"""Tests d'intégrité pipeline : comparaison CSV bruts vs base de données."""

import sqlite3

import pandas as pd
import pytest

from src.config import RAW_DIR, DATABASE_PATH, CSV_FILES as CSV_FILENAMES

# ── Chemins complets des CSV ─────────────────────────────────────────────

CSV_FILES = {name: RAW_DIR / filename for name, filename in CSV_FILENAMES.items()}

# ── Skip si les fichiers nécessaires sont absents ────────────────────────

_missing_csv = not all(p.exists() for p in CSV_FILES.values())
_missing_db = not DATABASE_PATH.exists()

pytestmark = pytest.mark.integration


# ── Helpers ──────────────────────────────────────────────────────────────

def db_query(conn, sql, params=None):
    """Exécuter une requête SQL et retourner un DataFrame."""
    return pd.read_sql_query(sql, conn, params=params)


def sample_and_query(conn, ids, sql_template, n=100, random_state=42):
    """Échantillonner N ids, construire des placeholders SQL, exécuter la requête.

    ``sql_template`` doit contenir un unique ``{placeholders}`` qui sera
    remplacé par ``?,?,?,...`` et les *ids* échantillonnés seront passés
    en paramètres liés.
    """
    sample = ids.sample(n=min(n, len(ids)), random_state=random_state).tolist()
    placeholders = ",".join("?" * len(sample))
    sql = sql_template.format(placeholders=placeholders)
    return db_query(conn, sql, params=sample), sample


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def raw_csvs():
    """Charger les 9 CSV bruts."""
    if _missing_csv:
        pytest.skip("CSV bruts absents — lancez d'abord le téléchargement Kaggle")
    dfs = {}
    for name, path in CSV_FILES.items():
        parse_dates = None
        if name == "orders":
            parse_dates = [
                "order_purchase_timestamp",
                "order_approved_at",
                "order_delivered_carrier_date",
                "order_delivered_customer_date",
                "order_estimated_delivery_date",
            ]
        elif name == "order_reviews":
            parse_dates = ["review_creation_date", "review_answer_timestamp"]
        dfs[name] = pd.read_csv(path, parse_dates=parse_dates)
    return dfs


@pytest.fixture(scope="module")
def db_conn():
    """Connexion SQLite en lecture seule."""
    if _missing_db:
        pytest.skip("Base de données absente — lancez d'abord le pipeline ETL")
    uri = f"file:{DATABASE_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    yield conn
    conn.close()


# ═══════════════════════════════════════════════════════════════════════════
# 1. TestRowCounts — 5 tests
# ═══════════════════════════════════════════════════════════════════════════

class TestRowCounts:
    """Vérifier que le nombre de lignes dans les dimensions correspond aux
    clés uniques des CSV bruts."""

    def test_dim_customers_count(self, raw_csvs, db_conn):
        expected = raw_csvs["customers"]["customer_id"].nunique()
        actual = db_query(db_conn, "SELECT COUNT(*) AS n FROM dim_customers")["n"][0]
        assert actual == expected

    def test_dim_sellers_count(self, raw_csvs, db_conn):
        expected = raw_csvs["sellers"]["seller_id"].nunique()
        actual = db_query(db_conn, "SELECT COUNT(*) AS n FROM dim_sellers")["n"][0]
        assert actual == expected

    def test_dim_products_count(self, raw_csvs, db_conn):
        expected = raw_csvs["products"]["product_id"].nunique()
        actual = db_query(db_conn, "SELECT COUNT(*) AS n FROM dim_products")["n"][0]
        assert actual == expected

    def test_dim_geolocation_count(self, raw_csvs, db_conn):
        expected = raw_csvs["geolocation"]["geolocation_zip_code_prefix"].nunique()
        actual = db_query(db_conn, "SELECT COUNT(*) AS n FROM dim_geolocation")["n"][0]
        assert actual == expected

    def test_fact_orders_count(self, raw_csvs, db_conn):
        expected = raw_csvs["order_items"].drop_duplicates().shape[0]
        actual = db_query(db_conn, "SELECT COUNT(*) AS n FROM fact_orders")["n"][0]
        assert actual == expected


# ═══════════════════════════════════════════════════════════════════════════
# 2. TestRevenueIntegrity — 4 tests
# ═══════════════════════════════════════════════════════════════════════════

class TestRevenueIntegrity:
    """Vérifier les sommes de prix et freight entre CSV et DB."""

    def test_total_price(self, raw_csvs, db_conn):
        csv_total = raw_csvs["order_items"]["price"].clip(lower=0).sum()
        db_total = db_query(db_conn, "SELECT SUM(price) AS s FROM fact_orders")["s"][0]
        assert db_total == pytest.approx(csv_total, rel=1e-6)

    def test_total_freight(self, raw_csvs, db_conn):
        csv_total = raw_csvs["order_items"]["freight_value"].clip(lower=0).sum()
        db_total = db_query(
            db_conn, "SELECT SUM(freight_value) AS s FROM fact_orders"
        )["s"][0]
        assert db_total == pytest.approx(csv_total, rel=1e-6)

    def test_no_negative_price(self, db_conn):
        result = db_query(
            db_conn, "SELECT COUNT(*) AS n FROM fact_orders WHERE price < 0"
        )["n"][0]
        assert result == 0

    def test_no_negative_freight(self, db_conn):
        result = db_query(
            db_conn,
            "SELECT COUNT(*) AS n FROM fact_orders WHERE freight_value < 0",
        )["n"][0]
        assert result == 0


# ═══════════════════════════════════════════════════════════════════════════
# 3. TestPaymentAggregation — 2 tests
# ═══════════════════════════════════════════════════════════════════════════

class TestPaymentAggregation:
    """Vérifier l'agrégation des paiements par commande."""

    def test_payment_sample(self, raw_csvs, db_conn):
        """Sur 100 commandes échantillonnées, order_payment_total DB == SUM CSV."""
        csv_pay = raw_csvs["order_payments"].copy()
        csv_pay["payment_value"] = csv_pay["payment_value"].clip(lower=0)
        csv_agg = csv_pay.groupby("order_id")["payment_value"].sum()

        db_pay, _ = sample_and_query(
            db_conn, csv_agg.index.to_series(),
            "SELECT DISTINCT order_id, order_payment_total FROM fact_orders "
            "WHERE order_id IN ({placeholders})",
        )

        for _, row in db_pay.iterrows():
            oid = row["order_id"]
            assert row["order_payment_total"] == pytest.approx(csv_agg[oid], rel=1e-6), (
                f"Payment mismatch pour order_id={oid}"
            )

    def test_payment_global_total(self, raw_csvs, db_conn):
        """Total global : SUM des payments par commande (commandes communes) DB == CSV."""
        csv_pay = raw_csvs["order_payments"].copy()
        csv_pay["payment_value"] = csv_pay["payment_value"].clip(lower=0)
        csv_agg = csv_pay.groupby("order_id")["payment_value"].sum()

        db_agg = db_query(
            db_conn,
            "SELECT order_id, MAX(order_payment_total) AS pv "
            "FROM fact_orders WHERE order_payment_total IS NOT NULL "
            "GROUP BY order_id",
        ).set_index("order_id")["pv"]

        common = csv_agg.index.intersection(db_agg.index)
        csv_total = csv_agg.loc[common].sum()
        db_total = db_agg.loc[common].sum()

        assert db_total == pytest.approx(csv_total, rel=1e-6)


# ═══════════════════════════════════════════════════════════════════════════
# 4. TestReviewAggregation — 1 test
# ═══════════════════════════════════════════════════════════════════════════

class TestReviewAggregation:
    """Vérifier que review_score correspond au dernier avis du CSV."""

    def test_review_latest_score(self, raw_csvs, db_conn):
        reviews = raw_csvs["order_reviews"].copy()
        reviews["review_creation_date"] = pd.to_datetime(
            reviews["review_creation_date"], errors="coerce"
        )
        latest = (
            reviews.sort_values("review_creation_date", ascending=False, na_position="last")
            .drop_duplicates(subset="order_id", keep="first")
            .set_index("order_id")["review_score"]
        )

        db_reviews, sample = sample_and_query(
            db_conn, latest.index.to_series(),
            "SELECT DISTINCT order_id, review_score FROM fact_orders "
            "WHERE order_id IN ({placeholders}) AND review_score IS NOT NULL",
        )

        for _, row in db_reviews.iterrows():
            oid = row["order_id"]
            expected_score = int(latest[oid])
            assert row["review_score"] == expected_score, (
                f"Review score mismatch pour order_id={oid}"
            )


# ═══════════════════════════════════════════════════════════════════════════
# 5. TestDeliveryMetrics — 2 tests
# ═══════════════════════════════════════════════════════════════════════════

class TestDeliveryMetrics:
    """Vérifier les métriques de livraison."""

    def test_delivery_days_from_csv(self, raw_csvs, db_conn):
        """delivery_days DB == calcul depuis timestamps CSV."""
        orders = raw_csvs["orders"].copy()
        orders["order_delivered_customer_date"] = pd.to_datetime(
            orders["order_delivered_customer_date"], errors="coerce"
        )
        orders["order_purchase_timestamp"] = pd.to_datetime(
            orders["order_purchase_timestamp"], errors="coerce"
        )
        delivered = orders.dropna(
            subset=["order_delivered_customer_date", "order_purchase_timestamp"]
        )
        csv_days = (
            (delivered["order_delivered_customer_date"] - delivered["order_purchase_timestamp"])
            .dt.total_seconds() / 86400
        )
        csv_delivery = pd.DataFrame({
            "order_id": delivered["order_id"],
            "delivery_days": csv_days,
        }).set_index("order_id")

        db_del, _ = sample_and_query(
            db_conn, csv_delivery.index.to_series(),
            "SELECT DISTINCT order_id, delivery_days FROM fact_orders "
            "WHERE order_id IN ({placeholders}) AND delivery_days IS NOT NULL",
        )

        for _, row in db_del.iterrows():
            oid = row["order_id"]
            assert row["delivery_days"] == pytest.approx(
                csv_delivery.loc[oid, "delivery_days"], abs=1e-4
            ), f"Delivery days mismatch pour order_id={oid}"

    def test_delivery_delta_coherence(self, db_conn):
        """delivery_delta_days == delivery_days - estimated_days (auto-cohérence)."""
        df = db_query(
            db_conn,
            "SELECT delivery_days, estimated_days, delivery_delta_days "
            "FROM fact_orders "
            "WHERE delivery_days IS NOT NULL AND estimated_days IS NOT NULL",
        )
        expected = df["delivery_days"] - df["estimated_days"]
        for i, row in df.iterrows():
            assert row["delivery_delta_days"] == pytest.approx(
                expected.iloc[i] if isinstance(i, int) else expected[i], abs=1e-4
            )


# ═══════════════════════════════════════════════════════════════════════════
# 6. TestDateDimension — 4 tests
# ═══════════════════════════════════════════════════════════════════════════

class TestDateDimension:
    """Vérifier la dimension date."""

    def test_fk_coverage(self, db_conn):
        """Toutes les date_key de fact_orders existent dans dim_dates."""
        orphans = db_query(
            db_conn,
            "SELECT COUNT(*) AS n FROM fact_orders f "
            "LEFT JOIN dim_dates d ON f.date_key = d.date_key "
            "WHERE f.date_key IS NOT NULL AND d.date_key IS NULL",
        )["n"][0]
        assert orphans == 0

    def test_date_key_format(self, db_conn):
        """date_key au format YYYYMMDD (8 chiffres, entre 20000101 et 20991231)."""
        invalid = db_query(
            db_conn,
            "SELECT COUNT(*) AS n FROM dim_dates "
            "WHERE date_key < 20000101 OR date_key > 20991231",
        )["n"][0]
        assert invalid == 0

    def test_full_date_coherence(self, db_conn):
        """full_date cohérent avec year/month/day."""
        df = db_query(
            db_conn,
            "SELECT full_date, year, month, day FROM dim_dates",
        )
        df["full_date"] = pd.to_datetime(df["full_date"])
        assert (df["full_date"].dt.year == df["year"]).all()
        assert (df["full_date"].dt.month == df["month"]).all()
        assert (df["full_date"].dt.day == df["day"]).all()

    def test_date_key_unique(self, db_conn):
        """Chaque date_key est unique dans dim_dates."""
        df = db_query(db_conn, "SELECT date_key FROM dim_dates")
        assert df["date_key"].is_unique


# ═══════════════════════════════════════════════════════════════════════════
# 7. TestForeignKeyIntegrity — 5 tests (paramétrisés)
# ═══════════════════════════════════════════════════════════════════════════

_FK_PARAMS = [
    ("customer_key", "dim_customers", "customer_key"),
    ("seller_key", "dim_sellers", "seller_key"),
    ("product_key", "dim_products", "product_key"),
    ("customer_geo_key", "dim_geolocation", "geo_key"),
    ("seller_geo_key", "dim_geolocation", "geo_key"),
]


class TestForeignKeyIntegrity:
    """Vérifier que toutes les FK de fact_orders référencent des dimensions."""

    @pytest.mark.parametrize("fk_col,dim_table,pk_col", _FK_PARAMS,
                             ids=[p[0] for p in _FK_PARAMS])
    def test_fk_no_orphans(self, db_conn, fk_col, dim_table, pk_col):
        orphans = db_query(
            db_conn,
            f"SELECT COUNT(*) AS n FROM fact_orders f "
            f"LEFT JOIN {dim_table} d ON f.{fk_col} = d.{pk_col} "
            f"WHERE f.{fk_col} IS NOT NULL AND d.{pk_col} IS NULL",
        )["n"][0]
        assert orphans == 0, f"{orphans} {fk_col} orphelins"


# ═══════════════════════════════════════════════════════════════════════════
# 8. TestOrderStatusDistribution — 2 tests
# ═══════════════════════════════════════════════════════════════════════════

class TestOrderStatusDistribution:
    """Vérifier la distribution des statuts (grain = article)."""

    def test_status_values_match(self, raw_csvs, db_conn):
        """Les statuts présents dans DB sont un sous-ensemble de ceux du CSV."""
        csv_statuses = set(raw_csvs["orders"]["order_status"].dropna().unique())
        db_statuses = set(
            db_query(db_conn, "SELECT DISTINCT order_status FROM fact_orders")[
                "order_status"
            ]
        )
        assert db_statuses.issubset(csv_statuses)

    def test_status_counts(self, raw_csvs, db_conn):
        """Distribution des statuts (grain article) cohérente entre CSV et DB."""
        items = raw_csvs["order_items"].drop_duplicates()
        orders = raw_csvs["orders"][["order_id", "order_status"]]
        merged = items.merge(orders, on="order_id", how="left")
        csv_counts = merged["order_status"].value_counts().sort_index()

        db_counts = db_query(
            db_conn,
            "SELECT order_status, COUNT(*) AS n FROM fact_orders "
            "GROUP BY order_status ORDER BY order_status",
        ).set_index("order_status")["n"]

        for status in csv_counts.index:
            assert db_counts.get(status, 0) == csv_counts[status], (
                f"Count mismatch pour statut '{status}'"
            )


# ═══════════════════════════════════════════════════════════════════════════
# 9. TestCategoryTranslation — 3 tests
# ═══════════════════════════════════════════════════════════════════════════

class TestCategoryTranslation:
    """Vérifier la traduction des catégories produits."""

    def test_known_categories_translated(self, raw_csvs, db_conn):
        """Produits avec catégorie connue -> category_name_en != 'unknown'."""
        translation = raw_csvs["category_translation"]
        known_cats = set(translation["product_category_name"].dropna().str.strip())

        products = raw_csvs["products"].copy()
        products["product_category_name"] = products["product_category_name"].str.strip()
        known_product_ids = list(
            products.loc[
                products["product_category_name"].isin(known_cats), "product_id"
            ]
        )[:200]

        placeholders = ",".join("?" * len(known_product_ids))
        db_prods = db_query(
            db_conn,
            f"SELECT product_id, category_name_en FROM dim_products "
            f"WHERE product_id IN ({placeholders})",
            params=known_product_ids,
        )

        unknowns = db_prods[db_prods["category_name_en"] == "unknown"]
        assert len(unknowns) == 0, (
            f"{len(unknowns)} produits avec catégorie connue traduits en 'unknown'"
        )

    def test_null_categories_unknown(self, raw_csvs, db_conn):
        """Produits avec catégorie null dans CSV -> 'unknown' dans DB."""
        products = raw_csvs["products"].copy()
        null_cat_ids = list(
            products.loc[products["product_category_name"].isna(), "product_id"]
        )

        if not null_cat_ids:
            pytest.skip("Aucun produit avec catégorie null dans le CSV")

        placeholders = ",".join("?" * len(null_cat_ids))
        db_prods = db_query(
            db_conn,
            f"SELECT product_id, category_name_en FROM dim_products "
            f"WHERE product_id IN ({placeholders})",
            params=null_cat_ids,
        )

        not_unknown = db_prods[db_prods["category_name_en"] != "unknown"]
        assert len(not_unknown) == 0, (
            f"{len(not_unknown)} produits null non traduits en 'unknown'"
        )

    def test_unknown_count_coherent(self, raw_csvs, db_conn):
        """Le nombre de 'unknown' dans DB correspond aux catégories manquantes."""
        translation = raw_csvs["category_translation"]
        known_cats = set(translation["product_category_name"].dropna().str.strip())

        products = raw_csvs["products"].copy()
        products["product_category_name"] = products["product_category_name"].str.strip()
        csv_unknown_count = (
            products["product_category_name"].isna()
            | ~products["product_category_name"].isin(known_cats)
        ).sum()

        db_unknown_count = db_query(
            db_conn,
            "SELECT COUNT(*) AS n FROM dim_products WHERE category_name_en = 'unknown'",
        )["n"][0]

        assert db_unknown_count == csv_unknown_count


# ═══════════════════════════════════════════════════════════════════════════
# 10. TestGeolocationDeduplication — 2 tests
# ═══════════════════════════════════════════════════════════════════════════

class TestGeolocationDeduplication:
    """Vérifier la déduplication de la géolocalisation."""

    def test_zip_code_unique(self, db_conn):
        """Chaque zip_code_prefix apparaît une seule fois."""
        df = db_query(db_conn, "SELECT zip_code_prefix FROM dim_geolocation")
        assert df["zip_code_prefix"].is_unique

    def test_median_coordinates(self, raw_csvs, db_conn):
        """lat/lng dans DB == médiane calculée sur le CSV brut."""
        geo = raw_csvs["geolocation"].copy()
        geo["geolocation_zip_code_prefix"] = (
            geo["geolocation_zip_code_prefix"].astype(str).str.zfill(5)
        )
        csv_median = geo.groupby("geolocation_zip_code_prefix").agg(
            lat=("geolocation_lat", "median"),
            lng=("geolocation_lng", "median"),
        )

        db_geo = db_query(
            db_conn,
            "SELECT zip_code_prefix, lat, lng FROM dim_geolocation",
        ).set_index("zip_code_prefix")

        sample_zips = csv_median.sample(n=min(100, len(csv_median)), random_state=42)
        for zip_code in sample_zips.index:
            if zip_code in db_geo.index:
                assert db_geo.loc[zip_code, "lat"] == pytest.approx(
                    csv_median.loc[zip_code, "lat"], abs=1e-4
                ), f"Lat mismatch pour zip={zip_code}"
                assert db_geo.loc[zip_code, "lng"] == pytest.approx(
                    csv_median.loc[zip_code, "lng"], abs=1e-4
                ), f"Lng mismatch pour zip={zip_code}"


# ═══════════════════════════════════════════════════════════════════════════
# 11. TestSchemaConstraints — 4 tests (boucles converties en parametrize)
# ═══════════════════════════════════════════════════════════════════════════

_SURROGATE_KEYS = [
    ("dim_customers", "customer_key"),
    ("dim_sellers", "seller_key"),
    ("dim_products", "product_key"),
    ("dim_geolocation", "geo_key"),
]

_PRIMARY_FIELDS = ["order_id", "order_item_id", "price", "freight_value"]


class TestSchemaConstraints:
    """Vérifier les contraintes du schéma."""

    def test_order_item_unique(self, db_conn):
        """Unicité de la paire (order_id, order_item_id)."""
        df = db_query(
            db_conn, "SELECT order_id, order_item_id FROM fact_orders"
        )
        assert not df.duplicated().any()

    def test_review_score_range(self, db_conn):
        """review_score entre 1 et 5 (ou NULL)."""
        invalid = db_query(
            db_conn,
            "SELECT COUNT(*) AS n FROM fact_orders "
            "WHERE review_score IS NOT NULL AND (review_score < 1 OR review_score > 5)",
        )["n"][0]
        assert invalid == 0

    @pytest.mark.parametrize("table,key", _SURROGATE_KEYS,
                             ids=[f"{t}.{k}" for t, k in _SURROGATE_KEYS])
    def test_positive_keys(self, db_conn, table, key):
        """Les clés surrogate sont positives."""
        neg = db_query(
            db_conn,
            f"SELECT COUNT(*) AS n FROM {table} WHERE {key} <= 0",
        )["n"][0]
        assert neg == 0, f"{table}.{key} contient des valeurs <= 0"

    @pytest.mark.parametrize("col", _PRIMARY_FIELDS)
    def test_no_null_primary_fields(self, db_conn, col):
        """Pas de nulls dans les champs essentiels de fact_orders."""
        nulls = db_query(
            db_conn,
            f"SELECT COUNT(*) AS n FROM fact_orders WHERE {col} IS NULL",
        )["n"][0]
        assert nulls == 0, f"fact_orders.{col} contient {nulls} NULL(s)"
