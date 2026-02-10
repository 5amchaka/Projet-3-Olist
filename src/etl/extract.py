"""Extraction : charger les fichiers CSV bruts dans des DataFrames."""

import logging

import pandas as pd

from src.config import CSV_FILES, RAW_DIR

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Erreur levée lors de l'extraction des données brutes."""


def load_raw_csv(name: str) -> pd.DataFrame:
    """Charger un seul fichier CSV brut par nom de dataset."""
    try:
        filename = CSV_FILES[name]
    except KeyError:
        raise ExtractionError(
            f"Dataset inconnu : '{name}'. "
            f"Datasets disponibles : {sorted(CSV_FILES)}"
        )

    path = RAW_DIR / filename
    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        raise ExtractionError(f"Fichier introuvable : {path}")


def load_all_raw() -> dict[str, pd.DataFrame]:
    """Charger les 9 fichiers CSV bruts dans un dictionnaire de DataFrames."""
    dfs = {}
    for name in CSV_FILES:
        logger.info("Loading %s...", name)
        dfs[name] = load_raw_csv(name)
        logger.info("  -> %s rows, %s cols", f"{dfs[name].shape[0]:,}", dfs[name].shape[1])
    return dfs
