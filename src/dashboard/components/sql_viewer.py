"""Composant central : affiche SQL → exécute → chart."""

from typing import Callable

import pandas as pd
from nicegui import ui

from src.dashboard import db


def sql_viewer(
    title: str,
    description: str,
    sql_file: str,
    chart_builder: Callable[[pd.DataFrame], None],
    show_table: bool = False,
) -> None:
    """Composant qui affiche une analyse complète : titre, SQL, chart, table.

    Args:
        title: Titre de l'analyse
        description: Concepts SQL mis en valeur
        sql_file: Nom du fichier .sql dans sql/dashboard/
        chart_builder: Callback (df) → construit le graphique
        show_table: Si True, affiche aussi les données brutes
    """
    sql_text, df = db.query_from_file(sql_file)

    ui.label(title).classes("page-title mt-4")
    with ui.element("div").classes("sql-concepts mb-2"):
        ui.html(f"<b>Concepts SQL :</b> {description}")

    with ui.expansion("Voir la requête SQL", icon="code").classes(
        "w-full sql-block"
    ).props("dense"):
        ui.code(sql_text, language="sql").classes("w-full")

    if df.empty:
        ui.label("Aucune donnee retournee par cette requete.").classes("text-center mt-4")
        return

    chart_builder(df)

    if show_table and not df.empty:
        with ui.expansion("Données brutes", icon="table_chart").classes("w-full mt-2"):
            ui.table.from_pandas(df.head(50)).classes("w-full")
