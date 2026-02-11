"""Page Scoring vendeurs — radar Plotly + tableau interactif."""

import pandas as pd
import plotly.graph_objects as go
from nicegui import ui

from src.dashboard.components.page_layout import layout
from src.dashboard.components.sql_viewer import sql_viewer
from src.dashboard.theme import CHART_COLORS, PLOTLY_TEMPLATE
from src.dashboard.components.insight import insight_block


@ui.page("/scoring")
def page() -> None:
    layout(current_path="/scoring")
    content()


def content() -> None:
    """Construit le contenu de la page Scoring vendeurs."""
    with ui.element("div").classes("narrative-block"):
        ui.html(
            "<b>Scoring vendeurs</b> — "
            "Chaque vendeur est évalué sur 5 dimensions normalisées (NTILE) : "
            "revenu, volume de commandes, avis clients, délai de livraison et "
            "ponctualité. Le <b>score total</b> agrège ces notes pour établir "
            "un classement global. Le radar compare visuellement les profils "
            "des meilleurs vendeurs."
        )

    # ── SQL viewer + radar + tableau ─────────────────────────────────────
    sql_viewer(
        title="Classement et profil des vendeurs",
        description=(
            "<code>NTILE()</code>, "
            "<code>RANK / DENSE_RANK</code>, "
            "<code>Fonctions de fenêtrage</code>, "
            "<code>Agrégation multi-critères</code>"
        ),
        sql_file="seller_scoring.sql",
        chart_builder=_build_radar_and_table,
        show_table=False,
    )


def _build_radar_and_table(df: pd.DataFrame) -> None:
    """Radar chart Plotly (top 5) + tableau interactif (top 20)."""
    if df.empty:
        ui.label("Aucune donnée de scoring disponible.").classes("text-center mt-4")
        return

    top5 = df.head(5)

    # ── Radar chart Plotly ────────────────────────────────────────────────
    categories = ["Revenue", "Volume", "Avis", "Livraison", "Ponctualite"]
    score_cols = [
        "revenue_score",
        "volume_score",
        "review_score_ntile",
        "delivery_score",
        "ontime_score",
    ]

    fig = go.Figure()

    for i, (_, row) in enumerate(top5.iterrows()):
        values = [row[col] for col in score_cols]
        # Fermer le polygone en répétant la première valeur
        values_closed = values + [values[0]]
        cats_closed = categories + [categories[0]]

        seller_label = f"#{int(row['seller_rank'])} — {row['seller_city']}"

        fig.add_trace(
            go.Scatterpolar(
                r=values_closed,
                theta=cats_closed,
                fill="toself",
                name=seller_label,
                line=dict(color=CHART_COLORS[i % len(CHART_COLORS)]),
                opacity=0.7,
            )
        )

    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 5],
                tickvals=[1, 2, 3, 4, 5],
            ),
            bgcolor="rgba(0,0,0,0)",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5,
        ),
        margin=dict(t=40, b=80, l=60, r=60),
        height=500,
        title=dict(
            text="Profil radar — Top 5 vendeurs",
            font=dict(size=14),
        ),
    )

    ui.plotly(fig).classes("w-full")

    # Insight scoring
    best = top5.iloc[0]
    score_cols = [
        "revenue_score", "volume_score", "review_score_ntile",
        "delivery_score", "ontime_score",
    ]
    dim_labels = ["Revenue", "Volume", "Avis", "Livraison", "Ponctualite"]
    scores = [best[c] for c in score_cols]
    best_dim = dim_labels[scores.index(max(scores))]
    worst_dim = dim_labels[scores.index(min(scores))]
    insight_block(
        f"Le meilleur vendeur obtient <b>{int(best['total_score'])}/25</b>. "
        f"Son point fort est <b>{best_dim}</b>, "
        f"son axe d'amelioration est <b>{worst_dim}</b>. "
        f"Ce profil radar permet d'identifier les forces et faiblesses "
        f"de chaque vendeur pour un accompagnement cible."
    )

    # ── Tableau interactif top 20 ─────────────────────────────────────────
    ui.label("Top 20 vendeurs").classes("page-title mt-4")
    display_cols = [
        "seller_rank",
        "seller_city",
        "seller_state",
        "total_revenue",
        "nb_orders",
        "avg_review",
        "avg_delivery_days",
        "on_time_pct",
        "total_score",
    ]
    # Ne garder que les colonnes présentes dans le DataFrame
    display_cols = [c for c in display_cols if c in df.columns]
    top20 = df.head(20)[display_cols]

    ui.table.from_pandas(top20).classes("w-full")
