"""Page Pareto vendeurs — barres + courbe cumulative Plotly."""

import pandas as pd
import plotly.graph_objects as go
from nicegui import ui
from plotly.subplots import make_subplots

from src.dashboard.components.page_layout import layout
from src.dashboard.components.sql_viewer import sql_viewer
from src.dashboard.theme import CHART_COLORS, PLOTLY_TEMPLATE
from src.dashboard.components.insight import insight_block


@ui.page("/pareto")
def page() -> None:
    layout(current_path="/pareto")
    content()


def content() -> None:
    """Construit le contenu de la page Pareto vendeurs."""
    with ui.element("div").classes("narrative-block"):
        ui.html(
            "<b>Analyse Pareto des vendeurs</b> — "
            "Le principe de Pareto (loi 80/20) stipule qu'une minorite de vendeurs "
            "genere la majorite du chiffre d'affaires. Ce graphique identifie "
            "les vendeurs cles qui concentrent 80 % des revenus, "
            "permettant de prioriser les actions commerciales."
        )

    # -- SQL viewer + graphique Pareto --
    sql_viewer(
        title="Pareto des vendeurs",
        description=(
            "SUM() OVER (ROWS UNBOUNDED PRECEDING) cumul fenetre, "
            "ROW_NUMBER() OVER, sous-requete scalaire pour le total, "
            "CTE enchaine, CASE WHEN classification"
        ),
        sql_file="pareto_sellers.sql",
        chart_builder=_chart_builder,
    )


def _chart_builder(df: pd.DataFrame) -> None:
    """Construit un graphique Pareto combine : barres CA + ligne cumulative."""
    if df.empty:
        ui.label("Aucune donnee disponible.").classes("text-center mt-4")
        return

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Couleur conditionnelle selon le groupe Pareto
    bar_colors = [
        CHART_COLORS[0] if grp == "80%" else CHART_COLORS[3]
        for grp in df["pareto_group"]
    ]

    # Barres : chiffre d'affaires par vendeur (axe Y gauche)
    fig.add_trace(
        go.Bar(
            x=df["seller_rank"],
            y=df["total_revenue"],
            name="CA vendeur",
            marker_color=bar_colors,
            hovertemplate="Rang %{x}<br>CA: R$ %{y:,.2f}<extra></extra>",
        ),
        secondary_y=False,
    )

    # Ligne : pourcentage cumule (axe Y droit)
    fig.add_trace(
        go.Scatter(
            x=df["seller_rank"],
            y=df["cumulative_pct"],
            name="% cumule",
            mode="lines",
            line=dict(color=CHART_COLORS[1], width=2),
            hovertemplate="Rang %{x}<br>Cumul: %{y:.1f}%<extra></extra>",
        ),
        secondary_y=True,
    )

    # Ligne de reference a 80 %
    fig.add_hline(
        y=80,
        line_dash="dash",
        line_color=CHART_COLORS[2],
        annotation_text="80 %",
        annotation_position="top left",
        secondary_y=True,
    )

    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=500,
        xaxis_title="Rang du vendeur",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=60, r=60, t=40, b=60),
    )
    fig.update_yaxes(title_text="Chiffre d'affaires (R$)", secondary_y=False)
    fig.update_yaxes(
        title_text="% cumule",
        range=[0, 105],
        secondary_y=True,
    )

    ui.plotly(fig).classes("w-full mt-4")

    # Insight Pareto
    # Trouver le rang ou le cumul depasse 80%
    above_80 = df[df["cumulative_pct"] >= 80.0]
    if not above_80.empty:
        threshold_rank = int(above_80.iloc[0]["seller_rank"])
        nb_total = len(df)
        pct_sellers = threshold_rank * 100 / nb_total if nb_total > 0 else 0
        insight_block(
            f"Les <b>{threshold_rank}</b> premiers vendeurs ({pct_sellers:.0f}% du total) "
            f"concentrent 80% du CA — seuil atteint au rang <b>#{threshold_rank}</b>. "
            f"Cette concentration typique du Pareto invite a fideliser "
            f"ce noyau strategique tout en accompagnant la longue traine."
        )
    else:
        last_pct = df["cumulative_pct"].iloc[-1] if len(df) > 0 else 0
        insight_block(
            f"Les <b>{len(df)}</b> premiers vendeurs affiches representent "
            f"<b>{last_pct:.1f}%</b> du CA total. Le seuil des 80% n'est pas "
            f"encore atteint, signe d'une base vendeurs tres fragmentee."
        )
