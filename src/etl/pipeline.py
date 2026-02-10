"""Orchestrateur : exécuter le pipeline ETL complet."""

import logging

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

logger = logging.getLogger(__name__)

_SEPARATOR = "=" * 60


def _log_phase(title: str) -> None:
    """Afficher un en-tete de phase dans les logs."""
    logger.info(_SEPARATOR)
    logger.info(title)
    logger.info(_SEPARATOR)


def run_full_pipeline():
    """Extraction -> Transformation -> Construction des dimensions -> Chargement dans SQLite."""

    # ── Extraction ────────────────────────────────────────────────────────
    _log_phase("PHASE 1: EXTRACT")
    dfs = load_all_raw()

    # ── Transformation ──────────────────────────────────────────────────
    _log_phase("PHASE 2: TRANSFORM")
    cleaned = clean_all(dfs)

    # ── Construction des dimensions ───────────────────────────────────────
    _log_phase("PHASE 3: BUILD DIMENSIONS")

    dim_dates = build_dim_dates(cleaned["orders"])
    logger.info("dim_dates: %s entries", f"{len(dim_dates):,}")

    dim_geo = build_dim_geolocation(cleaned["geolocation"])
    logger.info("dim_geolocation: %s locations", f"{len(dim_geo):,}")

    dim_customers = build_dim_customers(cleaned["customers"], dim_geo)
    logger.info("dim_customers: %s customers", f"{len(dim_customers):,}")

    dim_sellers = build_dim_sellers(cleaned["sellers"], dim_geo)
    logger.info("dim_sellers: %s sellers", f"{len(dim_sellers):,}")

    dim_products = build_dim_products(cleaned["products"])
    logger.info("dim_products: %s products", f"{len(dim_products):,}")

    fact = build_fact_orders(
        cleaned["order_items"],
        cleaned["orders"],
        cleaned["order_payments"],
        cleaned["order_reviews"],
        dim_customers,
        dim_sellers,
        dim_products,
    )
    logger.info("fact_orders: %s rows", f"{len(fact):,}")

    # ── Chargement ───────────────────────────────────────────────────────
    _log_phase("PHASE 4: LOAD INTO SQLITE")

    DATABASE_DIR.mkdir(parents=True, exist_ok=True)
    engine = get_engine()

    load_to_sqlite(engine, dim_dates, dim_geo, dim_customers, dim_sellers, dim_products, fact)

    _log_phase("PIPELINE COMPLETE")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
    run_full_pipeline()
