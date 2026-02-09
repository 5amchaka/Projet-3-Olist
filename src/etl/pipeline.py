"""Orchestrateur : exécuter le pipeline ETL complet."""

from src.config import DATABASE_DIR
from src.database.connection import get_engine
from src.etl.extract import load_all_raw
from src.etl.transform import clean_all
from src.etl.load import (
    build_dim_dates,
    build_dim_geolocation,
    build_dim_customers,
    build_dim_sellers,
    build_dim_products,
    build_fact_orders,
    load_to_sqlite,
)


def run_full_pipeline():
    """Extraction -> Transformation -> Construction des dimensions -> Chargement dans SQLite."""

    # ── Extraction ────────────────────────────────────────────────────────
    print("=" * 60)
    print("PHASE 1: EXTRACT")
    print("=" * 60)
    dfs = load_all_raw()

    # ── Transformation ──────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("PHASE 2: TRANSFORM")
    print("=" * 60)
    cleaned = clean_all(dfs)

    # ── Construction des dimensions ───────────────────────────────────────
    print("\n" + "=" * 60)
    print("PHASE 3: BUILD DIMENSIONS")
    print("=" * 60)

    print("Building dim_dates...")
    dim_dates = build_dim_dates(cleaned["orders"])
    print(f"  -> {len(dim_dates):,} date entries")

    print("Building dim_geolocation...")
    dim_geo = build_dim_geolocation(cleaned["geolocation"])
    print(f"  -> {len(dim_geo):,} locations")

    print("Building dim_customers...")
    dim_customers = build_dim_customers(cleaned["customers"], dim_geo)
    print(f"  -> {len(dim_customers):,} customers")

    print("Building dim_sellers...")
    dim_sellers = build_dim_sellers(cleaned["sellers"], dim_geo)
    print(f"  -> {len(dim_sellers):,} sellers")

    print("Building dim_products...")
    dim_products = build_dim_products(cleaned["products"])
    print(f"  -> {len(dim_products):,} products")

    print("Building fact_orders...")
    fact = build_fact_orders(
        cleaned["order_items"],
        cleaned["orders"],
        cleaned["order_payments"],
        cleaned["order_reviews"],
        dim_customers,
        dim_sellers,
        dim_products,
    )
    print(f"  -> {len(fact):,} fact rows")

    # ── Chargement ───────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("PHASE 4: LOAD INTO SQLITE")
    print("=" * 60)

    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    engine = get_engine()

    load_to_sqlite(engine, dim_dates, dim_geo, dim_customers, dim_sellers, dim_products, fact)

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    run_full_pipeline()
