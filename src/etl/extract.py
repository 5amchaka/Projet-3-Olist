"""Extraction : charger les fichiers CSV bruts dans des DataFrames."""

import logging

import pandas as pd

from src.config import CSV_FILES, RAW_DIR

logger = logging.getLogger(__name__)


def load_raw_csv(name: str) -> pd.DataFrame:
    """Charger un seul fichier CSV brut par nom de dataset."""
    filename = CSV_FILES[name]
    path = RAW_DIR / filename
    return pd.read_csv(path)


def load_all_raw() -> dict[str, pd.DataFrame]:
    """Charger les 9 fichiers CSV bruts dans un dictionnaire de DataFrames."""
    dfs = {}
    for name in CSV_FILES:
        logger.info("Loading %s...", name)
        dfs[name] = load_raw_csv(name)
        logger.info("  -> %s rows, %s cols", f"{dfs[name].shape[0]:,}", dfs[name].shape[1])
    return dfs
