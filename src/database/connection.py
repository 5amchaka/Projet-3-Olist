"""Utilitaires de connexion à la base de données."""

import sqlite3

from sqlalchemy import create_engine, event

from src.config import DATABASE_PATH, DATABASE_URL


def get_engine():
    """Créer un moteur SQLAlchemy avec mode WAL et activation des clés étrangères."""
    engine = create_engine(DATABASE_URL, echo=False)

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def get_sqlite_connection() -> sqlite3.Connection:
    """Obtenir une connexion sqlite3 brute avec activation des clés étrangères."""
    conn = sqlite3.connect(str(DATABASE_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn
