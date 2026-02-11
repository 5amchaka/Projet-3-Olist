"""Tests pour la couche DB du dashboard."""

import sqlite3

from src.dashboard import db as dashboard_db


def test_get_connection_sets_temp_store_memory(tmp_path, monkeypatch):
    """La connexion dashboard force temp_store en mémoire."""
    db_path = tmp_path / "dashboard_test.db"

    # DB minimale: table utilisée par la requête de contrôle.
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE fact_orders (order_id TEXT, order_status TEXT)")
    conn.executemany(
        "INSERT INTO fact_orders (order_id, order_status) VALUES (?, ?)",
        [("o1", "delivered"), ("o1", "delivered"), ("o2", "canceled")],
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(dashboard_db, "_conn", None)
    monkeypatch.setattr(dashboard_db, "DATABASE_PATH", db_path)
    monkeypatch.setattr(dashboard_db, "_VIEWS_SQL", tmp_path / "missing_views.sql")

    ro_conn = dashboard_db.get_connection()
    temp_store = ro_conn.execute("PRAGMA temp_store").fetchone()[0]
    busy_timeout = ro_conn.execute("PRAGMA busy_timeout").fetchone()[0]
    distinct_orders = ro_conn.execute(
        "SELECT COUNT(DISTINCT order_id) FROM fact_orders"
    ).fetchone()[0]

    assert temp_store == 2  # 2 = MEMORY
    assert busy_timeout == 5000
    assert distinct_orders == 2

    ro_conn.close()
    monkeypatch.setattr(dashboard_db, "_conn", None)
