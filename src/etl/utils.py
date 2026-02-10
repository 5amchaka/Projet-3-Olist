"""Utilitaires partagés pour les modules ETL."""

import pandas as pd


def safe_mode(series: pd.Series, default: str = "unknown") -> str:
    """Retourner le mode d'une série, ou *default* si vide/tout NaN."""
    m = series.mode()
    return m.iloc[0] if len(m) > 0 else default
