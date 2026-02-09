"""Extraction : charger les fichiers CSV bruts dans des DataFrames."""

import pandas as pd

from src.config import CSV_FILES, RAW_DIR


def load_raw_csv(name: str) -> pd.DataFrame:
    """Charger un seul fichier CSV brut par nom de dataset."""
    filename = CSV_FILES[name]
    path = RAW_DIR / filename
    return pd.read_csv(path)


def load_all_raw() -> dict[str, pd.DataFrame]:
    """Charger les 9 fichiers CSV bruts dans un dictionnaire de DataFrames."""
    dfs = {}
    for name in CSV_FILES:
        print(f"  Loading {name}...")
        dfs[name] = load_raw_csv(name)
        print(f"    -> {dfs[name].shape[0]:,} rows, {dfs[name].shape[1]} cols")
    return dfs
