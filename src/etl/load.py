"""Chargement : construire les tables de dimension/faits et charger dans SQLite."""

import logging

import pandas as pd

from src.config import PROJECT_ROOT

logger = logging.getLogger(__name__)


# ── Utilitaires ──────────────────────────────────────────────────────────

def _add_surrogate_key(df: pd.DataFrame, key_name: str) -> pd.DataFrame:
    """Ajouter une clé surrogate 1-indexed nommée key_name au DataFrame."""
    df = df.reset_index(drop=True)
    df.index += 1
    df.index.name = key_name
    return df.reset_index()


def _safe_mode(x):
    """Retourner le mode d'une série, ou 'not_defined' si vide."""
    m = x.mode()
    return m.iloc[0] if len(m) > 0 else "not_defined"


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
    date_series = [orders[col].dropna() for col in ts_cols if col in orders.columns]
    all_dates = pd.concat(date_series) if date_series else pd.Series(dtype="datetime64[ns]")

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
    return _add_surrogate_key(dim, "geo_key")


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
    return _add_surrogate_key(dim, "customer_key")


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
    return _add_surrogate_key(dim, "seller_key")


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
    return _add_surrogate_key(dim, "product_key")


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
        order_payment_total=("payment_value", "sum"),
        payment_type=("payment_type", _safe_mode),
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
    cust_by_id = dim_customers.set_index("customer_id")
    seller_by_id = dim_sellers.set_index("seller_id")
    product_lookup = dim_products.set_index("product_id")["product_key"]

    fact["customer_key"] = fact["customer_id"].map(cust_by_id["customer_key"])
    fact["seller_key"] = fact["seller_id"].map(seller_by_id["seller_key"])
    fact["product_key"] = fact["product_id"].map(product_lookup)
    fact["customer_geo_key"] = fact["customer_id"].map(cust_by_id["geo_key"])
    fact["seller_geo_key"] = fact["seller_id"].map(seller_by_id["geo_key"])

    # ── Clé date à partir de l'horodatage d'achat ────────────────────────
    fact["date_key"] = (
        fact["order_purchase_timestamp"]
        .dt.strftime("%Y%m%d")
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
        "order_payment_total", "payment_type", "review_score",
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
    """Charger toutes les tables de dimension et de faits dans SQLite (transaction atomique)."""
    ddl_path = PROJECT_ROOT / "sql" / "create_star_schema.sql"
    ddl = ddl_path.read_text()

    tables = [
        ("dim_dates", dim_dates),
        ("dim_geolocation", dim_geo),
        ("dim_customers", dim_customers),
        ("dim_sellers", dim_sellers),
        ("dim_products", dim_products),
        ("fact_orders", fact),
    ]

    with engine.connect() as conn:
        # DDL + inserts dans une seule transaction
        conn.connection.executescript(ddl)
        for name, df in tables:
            logger.info("Loading %s (%s rows)...", name, f"{len(df):,}")
            df.to_sql(name, conn, if_exists="append", index=False, chunksize=5000)
        conn.commit()

    logger.info("All tables loaded successfully.")
