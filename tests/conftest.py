"""Fixtures partagées pour les tests."""

import pandas as pd
import pytest

from src.etl.load import (
    build_dim_customers,
    build_dim_dates,
    build_dim_geolocation,
    build_dim_products,
    build_dim_sellers,
    build_fact_orders,
)
from src.etl.transform import (
    clean_customers,
    clean_geolocation,
    clean_order_items,
    clean_orders,
    clean_products,
    clean_sellers,
)


@pytest.fixture
def sample_customers():
    return pd.DataFrame({
        "customer_id": ["c1", "c2", "c3"],
        "customer_unique_id": ["u1", "u2", "u3"],
        "customer_zip_code_prefix": [1234, 56789, 100],
        "customer_city": ["sao paulo", "RIO DE JANEIRO", "  brasilia  "],
        "customer_state": ["sp", "rj", "df"],
    })


@pytest.fixture
def sample_geolocation():
    return pd.DataFrame({
        "geolocation_zip_code_prefix": [1234, 1234, 5678, 5678, 5678],
        "geolocation_lat": [-23.5, -23.6, -22.9, -22.8, -22.7],
        "geolocation_lng": [-46.6, -46.7, -43.2, -43.1, -43.3],
        "geolocation_city": ["sao paulo", "sao paulo", "rio de janeiro", "rio de janeiro", "rio de janeiro"],
        "geolocation_state": ["sp", "sp", "rj", "rj", "rj"],
    })


@pytest.fixture
def sample_orders():
    return pd.DataFrame({
        "order_id": ["o1", "o2"],
        "customer_id": ["c1", "c2"],
        "order_status": ["delivered", "shipped"],
        "order_purchase_timestamp": ["2018-01-15 10:00:00", "2018-02-20 14:30:00"],
        "order_approved_at": ["2018-01-15 11:00:00", "2018-02-20 15:00:00"],
        "order_delivered_carrier_date": ["2018-01-16 08:00:00", None],
        "order_delivered_customer_date": ["2018-01-20 10:00:00", None],
        "order_estimated_delivery_date": ["2018-01-25 00:00:00", "2018-03-10 00:00:00"],
    })


@pytest.fixture
def sample_orders_parsed(sample_orders):
    """sample_orders avec les 5 colonnes timestamp converties en datetime."""
    df = sample_orders.copy()
    for col in [
        "order_purchase_timestamp", "order_approved_at",
        "order_delivered_carrier_date", "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]:
        df[col] = pd.to_datetime(df[col])
    return df


@pytest.fixture
def sample_products():
    return pd.DataFrame({
        "product_id": ["p1", "p2", "p3"],
        "product_category_name": ["informatica", None, "beleza_saude"],
        "product_name_lenght": [50.0, None, 30.0],
        "product_description_lenght": [500.0, 300.0, None],
        "product_photos_qty": [3.0, None, 2.0],
        "product_weight_g": [1000.0, 500.0, None],
        "product_length_cm": [30.0, None, 20.0],
        "product_height_cm": [10.0, 5.0, None],
        "product_width_cm": [20.0, None, 15.0],
    })


@pytest.fixture
def sample_category_translation():
    return pd.DataFrame({
        "product_category_name": ["informatica", "beleza_saude"],
        "product_category_name_english": ["computers", "health_beauty"],
    })


@pytest.fixture
def sample_sellers():
    return pd.DataFrame({
        "seller_id": ["s1", "s2"],
        "seller_zip_code_prefix": [1234, 5678],
        "seller_city": ["sao paulo", "rio de janeiro"],
        "seller_state": ["sp", "rj"],
    })


@pytest.fixture
def sample_order_items():
    return pd.DataFrame({
        "order_id": ["o1", "o1", "o2"],
        "order_item_id": [1, 2, 1],
        "product_id": ["p1", "p2", "p1"],
        "seller_id": ["s1", "s2", "s1"],
        "price": [100.0, 200.0, 150.0],
        "freight_value": [10.0, 20.0, 15.0],
        "shipping_limit_date": ["2018-02-01", "2018-02-01", "2018-03-01"],
    })


@pytest.fixture
def sample_order_payments():
    return pd.DataFrame({
        "order_id": ["o1", "o1", "o2"],
        "payment_sequential": [1, 2, 1],
        "payment_type": ["credit_card", "voucher", "boleto"],
        "payment_installments": [3, 1, 1],
        "payment_value": [250.0, 50.0, 150.0],
    })


@pytest.fixture
def sample_order_reviews():
    return pd.DataFrame({
        "review_id": ["r1", "r2", "r3"],
        "order_id": ["o1", "o1", "o2"],
        "review_score": [3, 5, 4],
        "review_comment_title": ["", "", ""],
        "review_comment_message": ["", "", ""],
        "review_creation_date": ["2018-02-01", "2018-02-10", "2018-03-05"],
        "review_answer_timestamp": ["2018-02-02", "2018-02-11", "2018-03-06"],
    })


@pytest.fixture
def sample_dim_geo(sample_geolocation):
    """Géolocalisation nettoyée + dimension construite."""
    geo = clean_geolocation(sample_geolocation)
    return build_dim_geolocation(geo)


@pytest.fixture
def fact_deps(
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
    """Construire toute la chaîne transform+build et retourner la fact table."""
    orders = clean_orders(sample_orders.copy())
    items = clean_order_items(sample_order_items.copy())

    geo = clean_geolocation(sample_geolocation)
    dim_geo = build_dim_geolocation(geo)
    dim_cust = build_dim_customers(clean_customers(sample_customers), dim_geo)
    dim_sell = build_dim_sellers(clean_sellers(sample_sellers), dim_geo)
    dim_prod = build_dim_products(
        clean_products(sample_products, sample_category_translation)
    )

    # Les reviews doivent être en datetime pour le tri dans build_fact_orders
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
    return fact
