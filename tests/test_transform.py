"""Tests pour le module transform."""

import pandas as pd
import pytest

from src.etl.transform import (
    clean_all,
    clean_category_translation,
    clean_customers,
    clean_geolocation,
    clean_orders,
    clean_order_items,
    clean_order_payments,
    clean_order_reviews,
    clean_products,
    clean_sellers,
    drop_full_duplicates,
    parse_dates,
    strip_strings,
)


class TestUtilities:
    def test_drop_full_duplicates(self):
        df = pd.DataFrame({"a": [1, 1, 2], "b": [3, 3, 4]})
        result = drop_full_duplicates(df)
        assert len(result) == 2

    def test_parse_dates(self):
        df = pd.DataFrame({"dt": ["2018-01-15 10:00:00", "invalid", None]})
        result = parse_dates(df, ["dt"])
        assert pd.api.types.is_datetime64_any_dtype(result["dt"])
        assert pd.isna(result["dt"].iloc[1])

    def test_strip_strings(self):
        df = pd.DataFrame({"name": ["  hello  ", "world  ", "  test"]})
        result = strip_strings(df)
        assert result["name"].tolist() == ["hello", "world", "test"]


class TestCleanCustomers:
    def test_city_title_case(self, sample_customers):
        result = clean_customers(sample_customers)
        assert result["customer_city"].tolist() == ["Sao Paulo", "Rio De Janeiro", "Brasilia"]

    def test_state_upper(self, sample_customers):
        result = clean_customers(sample_customers)
        assert result["customer_state"].tolist() == ["SP", "RJ", "DF"]

    def test_zip_zero_padded(self, sample_customers):
        result = clean_customers(sample_customers)
        assert result["customer_zip_code_prefix"].tolist() == ["01234", "56789", "00100"]


class TestCleanGeolocation:
    def test_deduplication(self, sample_geolocation):
        result = clean_geolocation(sample_geolocation)
        assert len(result) == 2  # 2 unique zip codes

    def test_median_coordinates(self, sample_geolocation):
        result = clean_geolocation(sample_geolocation)
        zip_1234 = result[result["geolocation_zip_code_prefix"] == "01234"]
        assert abs(zip_1234["geolocation_lat"].iloc[0] - (-23.55)) < 0.01

    def test_zip_zero_padded(self, sample_geolocation):
        result = clean_geolocation(sample_geolocation)
        assert all(len(z) == 5 for z in result["geolocation_zip_code_prefix"])


class TestCleanOrders:
    def test_timestamps_parsed(self, sample_orders):
        result = clean_orders(sample_orders)
        assert pd.api.types.is_datetime64_any_dtype(result["order_purchase_timestamp"])

    def test_valid_status_when_input_is_valid(self, sample_orders):
        result = clean_orders(sample_orders)
        valid = {"delivered", "shipped", "canceled", "unavailable",
                 "invoiced", "processing", "created", "approved"}
        assert result["order_status"].isin(valid).all()

    def test_invalid_status_warns_but_is_not_modified(self, sample_orders, capsys):
        df = sample_orders.copy()
        df.loc[1, "order_status"] = "unknown_status"

        result = clean_orders(df)
        captured = capsys.readouterr()

        assert "WARNING: 1 orders with invalid status" in captured.out
        assert result.loc[1, "order_status"] == "unknown_status"


class TestCleanOrderItems:
    def test_shipping_limit_date_parsed(self, sample_order_items):
        result = clean_order_items(sample_order_items)
        assert pd.api.types.is_datetime64_any_dtype(result["shipping_limit_date"])

    def test_negative_values_clipped(self, sample_order_items):
        df = sample_order_items.copy()
        df.loc[0, "price"] = -10
        df.loc[1, "freight_value"] = -5

        result = clean_order_items(df)

        assert result.loc[0, "price"] == 0
        assert result.loc[1, "freight_value"] == 0


class TestCleanOrderPayments:
    def test_negative_payment_value_clipped(self, sample_order_payments):
        df = sample_order_payments.copy()
        df.loc[0, "payment_value"] = -20

        result = clean_order_payments(df)

        assert result.loc[0, "payment_value"] == 0

    def test_unknown_payment_type_warns(self, sample_order_payments, capsys):
        df = sample_order_payments.copy()
        df.loc[2, "payment_type"] = "crypto"

        clean_order_payments(df)
        captured = capsys.readouterr()

        assert "WARNING: 1 payments with unknown type" in captured.out


class TestCleanOrderReviews:
    def test_review_score_clipped(self, sample_order_reviews):
        df = sample_order_reviews.copy()
        df.loc[0, "review_score"] = 0
        df.loc[1, "review_score"] = 7

        result = clean_order_reviews(df)

        assert result.loc[0, "review_score"] == 1
        assert result.loc[1, "review_score"] == 5

    def test_missing_comments_filled_with_empty_string(self, sample_order_reviews):
        df = sample_order_reviews.copy()
        df.loc[0, "review_comment_title"] = None
        df.loc[1, "review_comment_message"] = None

        result = clean_order_reviews(df)

        assert result.loc[0, "review_comment_title"] == ""
        assert result.loc[1, "review_comment_message"] == ""

    def test_review_dates_parsed(self, sample_order_reviews):
        df = sample_order_reviews.copy()
        df["review_creation_date"] = df["review_creation_date"].astype(str)
        df["review_answer_timestamp"] = df["review_answer_timestamp"].astype(str)

        result = clean_order_reviews(df)

        assert pd.api.types.is_datetime64_any_dtype(result["review_creation_date"])
        assert pd.api.types.is_datetime64_any_dtype(result["review_answer_timestamp"])


class TestCleanProducts:
    def test_translation_merged(self, sample_products, sample_category_translation):
        result = clean_products(sample_products, sample_category_translation)
        assert "product_category_name_english" in result.columns
        row = result[result["product_id"] == "p1"]
        assert row["product_category_name_english"].iloc[0] == "computers"

    def test_missing_category_filled(self, sample_products, sample_category_translation):
        result = clean_products(sample_products, sample_category_translation)
        row = result[result["product_id"] == "p2"]
        assert row["product_category_name"].iloc[0] == "unknown"
        assert row["product_category_name_english"].iloc[0] == "unknown"

    def test_numeric_nulls_filled(self, sample_products, sample_category_translation):
        result = clean_products(sample_products, sample_category_translation)
        assert result["product_weight_g"].isna().sum() == 0


class TestCleanSellers:
    def test_normalization(self, sample_sellers):
        result = clean_sellers(sample_sellers)
        assert result["seller_city"].tolist() == ["Sao Paulo", "Rio De Janeiro"]
        assert result["seller_state"].tolist() == ["SP", "RJ"]
        assert all(len(z) == 5 for z in result["seller_zip_code_prefix"])


class TestCleanCategoryTranslation:
    def test_strips_whitespace(self):
        df = pd.DataFrame({
            "product_category_name": ["  informatica  ", "beleza_saude"],
            "product_category_name_english": ["computers  ", "  health_beauty"],
        })
        result = clean_category_translation(df)
        assert result["product_category_name"].tolist() == ["informatica", "beleza_saude"]
        assert result["product_category_name_english"].tolist() == ["computers", "health_beauty"]

    def test_drops_duplicates(self):
        df = pd.DataFrame({
            "product_category_name": ["info", "info"],
            "product_category_name_english": ["computers", "computers"],
        })
        result = clean_category_translation(df)
        assert len(result) == 1


class TestCleanAll:
    def test_returns_all_9_datasets(
        self,
        sample_customers,
        sample_geolocation,
        sample_orders,
        sample_order_items,
        sample_order_payments,
        sample_order_reviews,
        sample_products,
        sample_sellers,
        sample_category_translation,
    ):
        dfs = {
            "customers": sample_customers,
            "geolocation": sample_geolocation,
            "orders": sample_orders,
            "order_items": sample_order_items,
            "order_payments": sample_order_payments,
            "order_reviews": sample_order_reviews,
            "products": sample_products,
            "sellers": sample_sellers,
            "category_translation": sample_category_translation,
        }
        result = clean_all(dfs)

        expected_keys = {
            "customers", "geolocation", "orders", "order_items",
            "order_payments", "order_reviews", "products", "sellers",
            "category_translation",
        }
        assert set(result.keys()) == expected_keys

    def test_products_has_english_translation(
        self,
        sample_customers,
        sample_geolocation,
        sample_orders,
        sample_order_items,
        sample_order_payments,
        sample_order_reviews,
        sample_products,
        sample_sellers,
        sample_category_translation,
    ):
        """category_translation nettoyée avant products → la colonne anglaise existe."""
        dfs = {
            "customers": sample_customers,
            "geolocation": sample_geolocation,
            "orders": sample_orders,
            "order_items": sample_order_items,
            "order_payments": sample_order_payments,
            "order_reviews": sample_order_reviews,
            "products": sample_products,
            "sellers": sample_sellers,
            "category_translation": sample_category_translation,
        }
        result = clean_all(dfs)
        assert "product_category_name_english" in result["products"].columns


class TestEdgeCases:
    """Tests de cas limites : DataFrames vides, valeurs entièrement NaN."""

    def test_clean_customers_empty(self):
        df = pd.DataFrame(columns=[
            "customer_id", "customer_unique_id",
            "customer_zip_code_prefix", "customer_city", "customer_state",
        ])
        result = clean_customers(df)
        assert len(result) == 0
        assert list(result.columns) == list(df.columns)

    def test_clean_geolocation_empty(self):
        df = pd.DataFrame(columns=[
            "geolocation_zip_code_prefix", "geolocation_lat",
            "geolocation_lng", "geolocation_city", "geolocation_state",
        ])
        result = clean_geolocation(df)
        assert len(result) == 0

    def test_clean_geolocation_all_nan_city_state(self):
        """Colonnes ville/état entièrement NaN : ne doit pas lever IndexError."""
        df = pd.DataFrame({
            "geolocation_zip_code_prefix": [1234, 1234],
            "geolocation_lat": [-23.5, -23.6],
            "geolocation_lng": [-46.6, -46.7],
            "geolocation_city": [None, None],
            "geolocation_state": [None, None],
        })
        result = clean_geolocation(df)
        assert len(result) == 1
        assert result["geolocation_city"].iloc[0] == "unknown"
        assert result["geolocation_state"].iloc[0] == "unknown"

    def test_clean_orders_empty(self):
        df = pd.DataFrame(columns=[
            "order_id", "customer_id", "order_status",
            "order_purchase_timestamp", "order_approved_at",
            "order_delivered_carrier_date", "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ])
        result = clean_orders(df)
        assert len(result) == 0

    def test_clean_sellers_empty(self):
        df = pd.DataFrame(columns=[
            "seller_id", "seller_zip_code_prefix",
            "seller_city", "seller_state",
        ])
        result = clean_sellers(df)
        assert len(result) == 0


class TestErrorCases:
    """Tests avec pytest.raises pour les cas d'erreur."""

    def test_clean_products_without_translation_raises(self):
        """clean_products sans translation_df lève TypeError."""
        df = pd.DataFrame({
            "product_id": ["p1"],
            "product_category_name": ["info"],
        })
        with pytest.raises(TypeError):
            clean_products(df)
