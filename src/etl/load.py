"""Chargement : construire les tables de dimension/faits et charger dans SQLite."""

import pandas as pd
import numpy as np


# ── Constructeurs de dimensions ──────────────────────────────────────────

def build_dim_dates(orders: pd.DataFrame) -> pd.DataFrame:
    """Générer une dimension date à partir des horodatages des commandes."""
    ts_cols = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    all_dates = pd.Series(dtype="datetime64[ns]")
    for col in ts_cols:
        if col in orders.columns:
            all_dates = pd.concat([all_dates, orders[col].dropna()])

    unique_dates = all_dates.dt.date.unique()
    unique_dates = pd.to_datetime(sorted(unique_dates))

    dim = pd.DataFrame({
        "date_key": unique_dates.strftime("%Y%m%d").astype(int),
        "full_date": unique_dates.date,
        "year": unique_dates.year,
        "quarter": unique_dates.quarter,
        "month": unique_dates.month,
        "day": unique_dates.day,
        "day_of_week": unique_dates.dayofweek,
        "day_name": unique_dates.day_name(),
        "is_weekend": (unique_dates.dayofweek >= 5).astype(int),
    })
    return dim


def build_dim_geolocation(geo: pd.DataFrame) -> pd.DataFrame:
    """Construire la dimension géolocalisation (déjà dédupliquée par transform)."""
    dim = pd.DataFrame({
        "zip_code_prefix": geo["geolocation_zip_code_prefix"],
        "lat": geo["geolocation_lat"],
        "lng": geo["geolocation_lng"],
        "city": geo["geolocation_city"],
        "state": geo["geolocation_state"],
    })
    dim = dim.reset_index(drop=True)
    dim.index += 1
    dim.index.name = "geo_key"
    return dim.reset_index()


def build_dim_customers(
    customers: pd.DataFrame, dim_geo: pd.DataFrame
) -> pd.DataFrame:
    """Construire la dimension client avec recherche de geo_key."""
    geo_lookup = dim_geo.set_index("zip_code_prefix")["geo_key"]

    dim = pd.DataFrame({
        "customer_id": customers["customer_id"],
        "customer_unique_id": customers["customer_unique_id"],
        "geo_key": customers["customer_zip_code_prefix"].map(geo_lookup),
        "city": customers["customer_city"],
        "state": customers["customer_state"],
    })
    dim = dim.reset_index(drop=True)
    dim.index += 1
    dim.index.name = "customer_key"
    return dim.reset_index()


def build_dim_sellers(
    sellers: pd.DataFrame, dim_geo: pd.DataFrame
) -> pd.DataFrame:
    """Construire la dimension vendeur avec recherche de geo_key."""
    geo_lookup = dim_geo.set_index("zip_code_prefix")["geo_key"]

    dim = pd.DataFrame({
        "seller_id": sellers["seller_id"],
        "geo_key": sellers["seller_zip_code_prefix"].map(geo_lookup),
        "city": sellers["seller_city"],
        "state": sellers["seller_state"],
    })
    dim = dim.reset_index(drop=True)
    dim.index += 1
    dim.index.name = "seller_key"
    return dim.reset_index()


def build_dim_products(products: pd.DataFrame) -> pd.DataFrame:
    """Construire la dimension produit."""
    dim = pd.DataFrame({
        "product_id": products["product_id"],
        "category_name_pt": products["product_category_name"],
        "category_name_en": products["product_category_name_english"],
        "weight_g": products["product_weight_g"],
        "length_cm": products["product_length_cm"],
        "height_cm": products["product_height_cm"],
        "width_cm": products["product_width_cm"],
        "photos_qty": products["product_photos_qty"],
    })
    dim = dim.reset_index(drop=True)
    dim.index += 1
    dim.index.name = "product_key"
    return dim.reset_index()


def build_fact_orders(
    order_items: pd.DataFrame,
    orders: pd.DataFrame,
    payments: pd.DataFrame,
    reviews: pd.DataFrame,
    dim_customers: pd.DataFrame,
    dim_sellers: pd.DataFrame,
    dim_products: pd.DataFrame,
) -> pd.DataFrame:
    """Construire la table de faits au grain article de commande."""

    # ── Agrégation des paiements par commande : valeur totale + type dominant (mode) ──
    pay_agg = payments.groupby("order_id").agg(
        payment_value=("payment_value", "sum"),
        payment_type=("payment_type", lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else "not_defined"),
    ).reset_index()

    # ── Avis : garder le plus récent par commande ────────────────────────
    review_agg = (
        reviews.sort_values("review_creation_date", ascending=False, na_position="last")
        .drop_duplicates(subset="order_id", keep="first")
        [["order_id", "review_score"]]
    )

    # ── Fusion des informations de commande ───────────────────────────────
    fact = order_items.merge(orders, on="order_id", how="left")
    fact = fact.merge(pay_agg, on="order_id", how="left")
    fact = fact.merge(review_agg, on="order_id", how="left")

    # ── Recherche des clés de substitution ────────────────────────────────
    cust_lookup = dim_customers.set_index("customer_id")["customer_key"]
    seller_lookup = dim_sellers.set_index("seller_id")["seller_key"]
    product_lookup = dim_products.set_index("product_id")["product_key"]

    cust_geo_lookup = dim_customers.set_index("customer_id")["geo_key"]
    seller_geo_lookup = dim_sellers.set_index("seller_id")["geo_key"]

    fact["customer_key"] = fact["customer_id"].map(cust_lookup)
    fact["seller_key"] = fact["seller_id"].map(seller_lookup)
    fact["product_key"] = fact["product_id"].map(product_lookup)
    fact["customer_geo_key"] = fact["customer_id"].map(cust_geo_lookup)
    fact["seller_geo_key"] = fact["seller_id"].map(seller_geo_lookup)

    # ── Clé date à partir de l'horodatage d'achat ────────────────────────
    fact["date_key"] = (
        fact["order_purchase_timestamp"]
        .dt.strftime("%Y%m%d")
        .astype(float)
        .astype("Int64")
    )

    # ── Métriques de livraison ────────────────────────────────────────────
    fact["delivery_days"] = (
        fact["order_delivered_customer_date"] - fact["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400

    fact["estimated_days"] = (
        fact["order_estimated_delivery_date"] - fact["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400

    fact["delivery_delta_days"] = fact["delivery_days"] - fact["estimated_days"]

    # ── Sélection des colonnes finales ────────────────────────────────────
    result = fact[[
        "order_id", "order_item_id", "date_key",
        "customer_key", "seller_key", "product_key",
        "customer_geo_key", "seller_geo_key",
        "order_status", "price", "freight_value",
        "payment_value", "payment_type", "review_score",
        "delivery_days", "estimated_days", "delivery_delta_days",
    ]].copy()

    return result


# ── Chargeur SQLite ──────────────────────────────────────────────────────

def load_to_sqlite(
    engine,
    dim_dates: pd.DataFrame,
    dim_geo: pd.DataFrame,
    dim_customers: pd.DataFrame,
    dim_sellers: pd.DataFrame,
    dim_products: pd.DataFrame,
    fact: pd.DataFrame,
):
    """Charger toutes les tables de dimension et de faits dans SQLite."""
    # Lire et exécuter le DDL
    from src.config import PROJECT_ROOT
    ddl_path = PROJECT_ROOT / "sql" / "create_star_schema.sql"
    ddl = ddl_path.read_text()

    with engine.connect() as conn:
        conn.connection.executescript(ddl)

    tables = [
        ("dim_dates", dim_dates),
        ("dim_geolocation", dim_geo),
        ("dim_customers", dim_customers),
        ("dim_sellers", dim_sellers),
        ("dim_products", dim_products),
        ("fact_orders", fact),
    ]

    for name, df in tables:
        print(f"  Loading {name} ({len(df):,} rows)...")
        df.to_sql(name, engine, if_exists="append", index=False, chunksize=5000)

    print("  All tables loaded successfully.")
