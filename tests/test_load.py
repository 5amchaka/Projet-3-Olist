"""Tests pour le module load."""

import pandas as pd
import pytest
from sqlalchemy import create_engine, text

from src.etl.load import (
    build_dim_dates,
    build_dim_geolocation,
    build_dim_customers,
    build_dim_sellers,
    build_dim_products,
    build_fact_orders,
    load_to_sqlite,
)
from src.etl.transform import clean_customers, clean_sellers


class TestBuildDimDates:
    def test_date_key_format(self, sample_orders_parsed):
        dim = build_dim_dates(sample_orders_parsed)
        assert len(dim) > 0
        assert all(dim["date_key"] > 20170000)
        assert all(dim["date_key"] < 20200000)

    def test_weekend_flag(self, sample_orders_parsed):
        dim = build_dim_dates(sample_orders_parsed)
        assert dim["is_weekend"].isin([0, 1]).all()


class TestBuildDimGeolocation:
    def test_has_geo_key(self, sample_dim_geo):
        assert "geo_key" in sample_dim_geo.columns
        assert sample_dim_geo["geo_key"].is_unique


class TestBuildDimCustomers:
    def test_has_customer_key(self, sample_customers, sample_dim_geo):
        cust = clean_customers(sample_customers)
        dim = build_dim_customers(cust, sample_dim_geo)
        assert "customer_key" in dim.columns
        assert dim["customer_key"].is_unique

    def test_geo_key_lookup(self, sample_customers, sample_dim_geo):
        cust = clean_customers(sample_customers)
        dim = build_dim_customers(cust, sample_dim_geo)
        row = dim[dim["customer_id"] == "c1"]
        assert pd.notna(row["geo_key"].iloc[0])


class TestBuildDimProducts:
    def test_has_product_key(self, sample_products, sample_category_translation):
        from src.etl.transform import clean_products
        products = clean_products(sample_products, sample_category_translation)
        dim = build_dim_products(products)
        assert "product_key" in dim.columns
        assert len(dim) == 3


class TestBuildFactOrders:
    """Tests pour build_fact_orders (utilise la fixture fact_deps du conftest)."""

    def test_fact_row_count(self, fact_deps):
        """Le grain est l'article : 3 items -> 3 lignes."""
        assert len(fact_deps) == 3

    def test_order_payment_total_per_order(self, fact_deps):
        """order_payment_total pour o1 = 250 + 50 = 300 (somme commande, dupliquée par item)."""
        o1_rows = fact_deps[fact_deps["order_id"] == "o1"]
        assert (o1_rows["order_payment_total"] == 300.0).all()

    def test_review_keeps_latest(self, fact_deps):
        """o1 a 2 reviews (score 3 le 02-01, score 5 le 02-10) -> on garde 5."""
        o1_rows = fact_deps[fact_deps["order_id"] == "o1"]
        assert (o1_rows["review_score"] == 5).all()

    def test_surrogate_keys_present(self, fact_deps):
        """Les cles surrogate doivent etre non-null."""
        assert fact_deps["customer_key"].notna().all()
        assert fact_deps["seller_key"].notna().all()
        assert fact_deps["product_key"].notna().all()

    def test_delivery_metrics(self, fact_deps):
        """delivery_days pour o1 = 5 jours (15 jan -> 20 jan)."""
        o1_row = fact_deps[fact_deps["order_id"] == "o1"].iloc[0]
        assert round(o1_row["delivery_days"]) == 5

    def test_logs_unresolved_customer_fk(
        self,
        sample_order_items,
        sample_orders,
        sample_order_payments,
        sample_order_reviews,
        sample_customers,
        sample_geolocation,
        sample_sellers,
        sample_products,
        sample_category_translation,
        caplog,
    ):
        """Si une FK client n'est pas résolue, build_fact_orders loggue un warning explicite."""
        from src.etl.transform import (
            clean_geolocation,
            clean_order_items,
            clean_orders,
            clean_products,
        )

        orders = clean_orders(sample_orders.copy())
        items = clean_order_items(sample_order_items.copy())
        geo = clean_geolocation(sample_geolocation)

        dim_geo = build_dim_geolocation(geo)
        dim_cust = build_dim_customers(clean_customers(sample_customers), dim_geo)
        dim_sell = build_dim_sellers(clean_sellers(sample_sellers), dim_geo)
        dim_prod = build_dim_products(
            clean_products(sample_products, sample_category_translation)
        )

        # Supprimer volontairement le client c1 : les 2 items de o1 perdent leur FK client.
        dim_cust = dim_cust[dim_cust["customer_id"] != "c1"]

        reviews = sample_order_reviews.copy()
        reviews["review_creation_date"] = pd.to_datetime(reviews["review_creation_date"])
        reviews["review_answer_timestamp"] = pd.to_datetime(reviews["review_answer_timestamp"])

        with caplog.at_level("WARNING", logger="src.etl.load"):
            fact = build_fact_orders(
                order_items=items,
                orders=orders,
                payments=sample_order_payments,
                reviews=reviews,
                dim_customers=dim_cust,
                dim_sellers=dim_sell,
                dim_products=dim_prod,
            )

        assert "customer_key NULL" in caplog.text
        assert fact["customer_key"].isna().sum() == 2


class TestBuildDimSellers:
    def test_has_seller_key(self, sample_sellers, sample_dim_geo):
        sellers = clean_sellers(sample_sellers)
        dim = build_dim_sellers(sellers, sample_dim_geo)
        assert "seller_key" in dim.columns
        assert dim["seller_key"].is_unique

    def test_geo_key_lookup(self, sample_sellers, sample_dim_geo):
        sellers = clean_sellers(sample_sellers)
        dim = build_dim_sellers(sellers, sample_dim_geo)
        row = dim[dim["seller_id"] == "s1"]
        assert pd.notna(row["geo_key"].iloc[0])


class TestLoadToSqlite:
    @pytest.fixture
    def full_star_schema(
        self,
        sample_orders_parsed,
        sample_order_items,
        sample_order_payments,
        sample_order_reviews,
        sample_customers,
        sample_dim_geo,
        sample_sellers,
        sample_products,
        sample_category_translation,
    ):
        """Construire toutes les tables du schema en etoile."""
        from src.etl.transform import (
            clean_orders,
            clean_order_items,
            clean_products,
        )

        orders = clean_orders(sample_orders_parsed.copy())
        items = clean_order_items(sample_order_items.copy())

        dim_cust = build_dim_customers(clean_customers(sample_customers), sample_dim_geo)
        dim_sell = build_dim_sellers(clean_sellers(sample_sellers), sample_dim_geo)
        dim_prod = build_dim_products(
            clean_products(sample_products, sample_category_translation)
        )
        dim_dates = build_dim_dates(orders)

        reviews = sample_order_reviews.copy()
        reviews["review_creation_date"] = pd.to_datetime(reviews["review_creation_date"])
        reviews["review_answer_timestamp"] = pd.to_datetime(reviews["review_answer_timestamp"])

        fact = build_fact_orders(
            order_items=items,
            orders=orders,
            payments=sample_order_payments,
            reviews=reviews,
            dim_customers=dim_cust,
            dim_sellers=dim_sell,
            dim_products=dim_prod,
        )
        return dim_dates, sample_dim_geo, dim_cust, dim_sell, dim_prod, fact

    def test_tables_created(self, tmp_path, full_star_schema):
        """Les 6 tables sont creees dans la DB."""
        db_path = tmp_path / "test.db"
        engine = create_engine(f"sqlite:///{db_path}")
        dim_dates, dim_geo, dim_cust, dim_sell, dim_prod, fact = full_star_schema

        load_to_sqlite(engine, dim_dates, dim_geo, dim_cust, dim_sell, dim_prod, fact)

        with engine.connect() as conn:
            tables = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            ).fetchall()
        table_names = {row[0] for row in tables}

        expected = {"dim_dates", "dim_geolocation", "dim_customers",
                    "dim_sellers", "dim_products", "fact_orders"}
        assert expected.issubset(table_names)

    def test_row_counts(self, tmp_path, full_star_schema):
        """Le nombre de lignes chargees correspond aux DataFrames."""
        db_path = tmp_path / "test.db"
        engine = create_engine(f"sqlite:///{db_path}")
        dim_dates, dim_geo, dim_cust, dim_sell, dim_prod, fact = full_star_schema

        load_to_sqlite(engine, dim_dates, dim_geo, dim_cust, dim_sell, dim_prod, fact)

        with engine.connect() as conn:
            for table, df in [
                ("dim_dates", dim_dates),
                ("dim_geolocation", dim_geo),
                ("dim_customers", dim_cust),
                ("dim_sellers", dim_sell),
                ("dim_products", dim_prod),
                ("fact_orders", fact),
            ]:
                count = conn.execute(
                    text(f"SELECT COUNT(*) FROM {table}")
                ).scalar()
                assert count == len(df), f"{table}: attendu {len(df)}, obtenu {count}"

    def test_no_duplicates_on_reload(self, tmp_path, full_star_schema):
        """Re-executer load_to_sqlite ne cree pas de doublons (DDL fait DROP IF EXISTS)."""
        db_path = tmp_path / "test.db"
        engine = create_engine(f"sqlite:///{db_path}")
        dim_dates, dim_geo, dim_cust, dim_sell, dim_prod, fact = full_star_schema

        load_to_sqlite(engine, dim_dates, dim_geo, dim_cust, dim_sell, dim_prod, fact)
        load_to_sqlite(engine, dim_dates, dim_geo, dim_cust, dim_sell, dim_prod, fact)

        with engine.connect() as conn:
            count = conn.execute(text("SELECT COUNT(*) FROM fact_orders")).scalar()
        assert count == len(fact)

    def test_atomic_rollback_on_load_error(self, tmp_path, full_star_schema):
        """En cas d'erreur pendant le chargement, la DB doit rester dans son état précédent."""
        db_path = tmp_path / "test.db"
        engine = create_engine(f"sqlite:///{db_path}")
        dim_dates, dim_geo, dim_cust, dim_sell, dim_prod, fact = full_star_schema

        # Premier chargement valide = état de référence.
        load_to_sqlite(engine, dim_dates, dim_geo, dim_cust, dim_sell, dim_prod, fact)

        with engine.connect() as conn:
            baseline_city = conn.execute(
                text("SELECT city FROM dim_customers WHERE customer_id = 'c1'")
            ).scalar()
            baseline_fact_count = conn.execute(
                text("SELECT COUNT(*) FROM fact_orders")
            ).scalar()

        # Deuxième chargement volontairement invalide (CHECK review_score 1..5).
        dim_cust_changed = dim_cust.copy()
        dim_cust_changed.loc[
            dim_cust_changed["customer_id"] == "c1", "city"
        ] = "ShouldNotPersist"

        invalid_fact = fact.copy()
        invalid_fact.loc[invalid_fact.index[0], "review_score"] = 6

        with pytest.raises(Exception):
            load_to_sqlite(
                engine,
                dim_dates,
                dim_geo,
                dim_cust_changed,
                dim_sell,
                dim_prod,
                invalid_fact,
            )

        with engine.connect() as conn:
            city_after_error = conn.execute(
                text("SELECT city FROM dim_customers WHERE customer_id = 'c1'")
            ).scalar()
            fact_count_after_error = conn.execute(
                text("SELECT COUNT(*) FROM fact_orders")
            ).scalar()

        assert city_after_error == baseline_city
        assert fact_count_after_error == baseline_fact_count
