"""Couche données — connexion SQLite read-only et helpers."""

import sqlite3
from pathlib import Path

import pandas as pd

from src.config import DATABASE_PATH

_SQL_DIR = Path(__file__).resolve().parent.parent.parent / "sql" / "dashboard"
_VIEWS_SQL = Path(__file__).resolve().parent.parent.parent / "sql" / "views.sql"
_conn: sqlite3.Connection | None = None


def _ensure_views() -> None:
    """Crée les vues SQL si elles sont absentes (connexion read-write temporaire)."""
    if not _VIEWS_SQL.exists():
        return
    # Vérifier si les vues existent déjà
    ro = sqlite3.connect(f"file:{DATABASE_PATH}?mode=ro", uri=True)
    existing = {
        row[0]
        for row in ro.execute(
            "SELECT name FROM sqlite_master WHERE type='view'"
        ).fetchall()
    }
    ro.close()
    expected = {"v_monthly_sales", "v_customer_cohorts", "v_orders_enriched"}
    if expected <= existing:
        return
    # Créer les vues manquantes
    rw = sqlite3.connect(str(DATABASE_PATH))
    rw.executescript(_VIEWS_SQL.read_text())
    rw.close()


def get_connection() -> sqlite3.Connection:
    """Retourne une connexion SQLite read-only singleton."""
    global _conn
    if _conn is None:
        _ensure_views()
        uri = f"file:{DATABASE_PATH}?mode=ro"
        _conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
        # Evite les erreurs "unable to open database file" sur les requêtes
        # analytiques qui nécessitent des structures temporaires (DISTINCT,
        # GROUP BY, ORDER BY, window functions) en mode read-only.
        _conn.execute("PRAGMA temp_store=MEMORY")
        _conn.row_factory = sqlite3.Row
    return _conn


def load_sql(filename: str) -> str:
    """Charge un fichier .sql depuis sql/dashboard/."""
    return (_SQL_DIR / filename).read_text(encoding="utf-8")


def query(sql: str, params: tuple = ()) -> pd.DataFrame:
    """Exécute une requête SQL et retourne un DataFrame."""
    return pd.read_sql_query(sql, get_connection(), params=params)


def query_from_file(filename: str) -> tuple[str, pd.DataFrame]:
    """Charge un .sql, l'exécute, et retourne (sql_text, DataFrame)."""
    sql = load_sql(filename)
    return sql, query(sql)
