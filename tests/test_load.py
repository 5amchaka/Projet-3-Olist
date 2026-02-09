"""Tests pour le module load."""

import pandas as pd
import pytest

from src.etl.load import (
    build_dim_dates,
    build_dim_geolocation,
    build_dim_customers,
    build_dim_sellers,
    build_dim_products,
    build_fact_orders,
)
from src.etl.transform import clean_geolocation, clean_customers, clean_sellers


class TestBuildDimDates:
    def test_date_key_format(self, sample_orders):
        orders = sample_orders.copy()
        orders["order_purchase_timestamp"] = pd.to_datetime(orders["order_purchase_timestamp"])
        orders["order_approved_at"] = pd.to_datetime(orders["order_approved_at"])
        orders["order_delivered_carrier_date"] = pd.to_datetime(orders["order_delivered_carrier_date"])
        orders["order_delivered_customer_date"] = pd.to_datetime(orders["order_delivered_customer_date"])
        orders["order_estimated_delivery_date"] = pd.to_datetime(orders["order_estimated_delivery_date"])

        dim = build_dim_dates(orders)
        assert len(dim) > 0
        # Les clés date doivent être des entiers au format AAAAMMJJ
        assert all(dim["date_key"] > 20170000)
        assert all(dim["date_key"] < 20200000)

    def test_weekend_flag(self, sample_orders):
        orders = sample_orders.copy()
        for col in ["order_purchase_timestamp", "order_approved_at",
                     "order_delivered_carrier_date", "order_delivered_customer_date",
                     "order_estimated_delivery_date"]:
            orders[col] = pd.to_datetime(orders[col])

        dim = build_dim_dates(orders)
        assert dim["is_weekend"].isin([0, 1]).all()


class TestBuildDimGeolocation:
    def test_has_geo_key(self, sample_geolocation):
        geo = clean_geolocation(sample_geolocation)
        dim = build_dim_geolocation(geo)
        assert "geo_key" in dim.columns
        assert dim["geo_key"].is_unique


class TestBuildDimCustomers:
    def test_has_customer_key(self, sample_customers, sample_geolocation):
        geo = clean_geolocation(sample_geolocation)
        dim_geo = build_dim_geolocation(geo)
        cust = clean_customers(sample_customers)
        dim = build_dim_customers(cust, dim_geo)
        assert "customer_key" in dim.columns
        assert dim["customer_key"].is_unique

    def test_geo_key_lookup(self, sample_customers, sample_geolocation):
        geo = clean_geolocation(sample_geolocation)
        dim_geo = build_dim_geolocation(geo)
        cust = clean_customers(sample_customers)
        dim = build_dim_customers(cust, dim_geo)
        # Le client c1 a le code postal 01234 qui est dans la géolocalisation
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
    """Tests pour build_fact_orders."""

    @pytest.fixture
    def fact_deps(
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
    ):
        """Prepare toutes les dimensions et retourne la fact table."""
        from src.etl.transform import (
            clean_orders,
            clean_order_items,
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

        fact = build_fact_orders(
            order_items=items,
            orders=orders,
            payments=sample_order_payments,
            reviews=sample_order_reviews,
            dim_customers=dim_cust,
            dim_sellers=dim_sell,
            dim_products=dim_prod,
        )
        return fact

    def test_fact_row_count(self, fact_deps):
        """Le grain est l'article : 3 items → 3 lignes."""
        assert len(fact_deps) == 3

    def test_payment_value_per_order(self, fact_deps):
        """payment_value pour o1 = 250 + 50 = 300 (somme commande, pas item)."""
        o1_rows = fact_deps[fact_deps["order_id"] == "o1"]
        assert (o1_rows["payment_value"] == 300.0).all()

    def test_review_keeps_latest(self, fact_deps):
        """o1 a 2 reviews (score 3 le 02-01, score 5 le 02-10) → on garde 5."""
        o1_rows = fact_deps[fact_deps["order_id"] == "o1"]
        assert (o1_rows["review_score"] == 5).all()

    def test_surrogate_keys_present(self, fact_deps):
        """Les cles surrogate doivent etre non-null."""
        assert fact_deps["customer_key"].notna().all()
        assert fact_deps["seller_key"].notna().all()
        assert fact_deps["product_key"].notna().all()

    def test_delivery_metrics(self, fact_deps):
        """delivery_days pour o1 = 5 jours (15 jan → 20 jan)."""
        o1_row = fact_deps[fact_deps["order_id"] == "o1"].iloc[0]
        assert round(o1_row["delivery_days"]) == 5
