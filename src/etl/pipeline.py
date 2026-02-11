"""Orchestrateur : exécuter le pipeline ETL complet."""

import logging
from collections.abc import Callable
from typing import TypeVar

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
_T = TypeVar("_T")


class PipelinePhaseError(RuntimeError):
    """Erreur du pipeline enrichie avec le nom de la phase en échec."""


def _log_phase(title: str) -> None:
    """Afficher un en-tete de phase dans les logs."""
    logger.info(_SEPARATOR)
    logger.info(title)
    logger.info(_SEPARATOR)


def _run_phase(title: str, action: Callable[[], _T]) -> _T:
    """Exécuter une phase avec logs et contextualisation des erreurs."""
    _log_phase(title)
    try:
        return action()
    except Exception as exc:
        logger.exception("%s FAILED", title)
        raise PipelinePhaseError(f"{title} failed: {exc}") from exc


def run_full_pipeline() -> None:
    """Extraction -> Transformation -> Construction des dimensions -> Chargement dans SQLite."""

    dfs = _run_phase("PHASE 1: EXTRACT", load_all_raw)

    cleaned = _run_phase("PHASE 2: TRANSFORM", lambda: clean_all(dfs))

    def _build_dimensions_and_fact():
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
        return dim_dates, dim_geo, dim_customers, dim_sellers, dim_products, fact

    dim_dates, dim_geo, dim_customers, dim_sellers, dim_products, fact = _run_phase(
        "PHASE 3: BUILD DIMENSIONS",
        _build_dimensions_and_fact,
    )

    def _load():
        DATABASE_DIR.mkdir(parents=True, exist_ok=True)
        engine = get_engine()
        load_to_sqlite(
            engine,
            dim_dates,
            dim_geo,
            dim_customers,
            dim_sellers,
            dim_products,
            fact,
        )

    _run_phase("PHASE 4: LOAD INTO SQLITE", _load)

    _log_phase("PIPELINE COMPLETE")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(name)s | %(message)s")
    run_full_pipeline()
