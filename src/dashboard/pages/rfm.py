"""Page Segmentation RFM — treemap ECharts des segments clients."""

import pandas as pd
from nicegui import ui

from src.dashboard.components.page_layout import layout
from src.dashboard.components.sql_viewer import sql_viewer
from src.dashboard.theme import CHART_COLORS
from src.dashboard.components.insight import insight_block


@ui.page("/rfm")
def page() -> None:
    layout(current_path="/rfm")
    content()


def content() -> None:
    """Construit le contenu de la page Segmentation RFM."""
    with ui.element("div").classes("narrative-block"):
        ui.html(
            "<b>Segmentation RFM</b> — "
            "La methode RFM (Recence, Frequence, Monetaire) classe chaque client "
            "selon trois axes : quand a-t-il achete pour la derniere fois, "
            "combien de fois a-t-il commande, et combien a-t-il depense. "
            "Les clients sont repartis en segments actionnables pour orienter "
            "les campagnes marketing."
        )

    # -- SQL viewer + treemap --
    sql_viewer(
        title="Segments RFM",
        description=(
            "CTE (WITH), NTILE() fenetre de quartiles, "
            "julianday() pour la recence, CASE WHEN combine, "
            "GROUP BY + agregations"
        ),
        sql_file="rfm_segmentation.sql",
        chart_builder=_chart_builder,
    )


def _chart_builder(df: pd.DataFrame) -> None:
    """Construit un treemap ECharts des segments + tableau recapitulatif."""
    if df.empty:
        ui.label("Aucune donnee disponible.").classes("text-center mt-4")
        return

    # Associer une couleur a chaque segment
    color_map = {
        row.segment: CHART_COLORS[i % len(CHART_COLORS)]
        for i, row in enumerate(df.itertuples())
    }

    # Donnees du treemap
    tree_data = [
        {
            "name": row.segment,
            "value": int(row.nb_customers),
            "itemStyle": {"color": color_map[row.segment]},
        }
        for row in df.itertuples()
    ]

    options = {
        "tooltip": {"formatter": "{b}: {c} clients"},
        "series": [
            {
                "type": "treemap",
                "data": tree_data,
                "label": {
                    "show": True,
                    "formatter": "{b}\n{c}",
                },
                "breadcrumb": {"show": False},
            }
        ],
    }

    ui.echart(options).style("height: 400px").classes("w-full mt-4")

    # Insight RFM
    dominant = df.loc[df["nb_customers"].idxmax()]
    total_customers = df["nb_customers"].sum()
    pct_dominant = dominant["nb_customers"] * 100 / total_customers if total_customers > 0 else 0
    at_risk = df[df["segment"].str.contains("At Risk|Lost|Hibernating", case=False, na=False)]
    nb_at_risk = int(at_risk["nb_customers"].sum()) if not at_risk.empty else 0
    insight_block(
        f"Le segment dominant est <b>{dominant['segment']}</b> "
        f"(<b>{int(dominant['nb_customers'])}</b> clients, <b>{pct_dominant:.0f}%</b>). "
        + (
            f"Les segments a risque representent <b>{nb_at_risk}</b> clients "
            f"qui meritent une campagne de reactivation."
            if nb_at_risk > 0
            else "Aucun segment a risque identifie — bonne sante de la base client."
        )
    )

    # Tableau recapitulatif
    ui.label("Detail par segment").classes("page-title mt-4")
    ui.table.from_pandas(df).classes("w-full mt-2")
