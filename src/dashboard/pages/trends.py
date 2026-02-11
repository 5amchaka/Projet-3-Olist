"""Page Tendances — evolution mensuelle du CA, commandes et cumul."""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from nicegui import ui

from src.dashboard.theme import CHART_COLORS, PLOTLY_TEMPLATE
from src.dashboard.components.page_layout import layout
from src.dashboard.components.sql_viewer import sql_viewer
from src.dashboard.components.insight import insight_block


@ui.page("/trends")
def page() -> None:
    layout(current_path="/trends")
    content()


def content() -> None:
    """Construit le contenu de la page Tendances."""

    # ── Titre + narrative ─────────────────────────────────────────────────
    ui.label("Tendances mensuelles").classes("page-title")
    with ui.element("div").classes("narrative-block"):
        ui.html(
            "Cette page analyse l'<b>evolution temporelle</b> de l'activite Olist. "
            "Le premier graphique superpose le chiffre d'affaires mensuel (barres) "
            "et le taux de croissance mois par mois (ligne, axe secondaire). "
            "Le second graphique montre le <b>cumul glissant</b> du CA, "
            "mettant en evidence la trajectoire globale de l'entreprise."
        )

    # ── Chart builder ─────────────────────────────────────────────────────
    def _build_trends_chart(df):
        # Filtrer les mois avec CA < 10k (débuts non représentatifs)
        df = df[df["monthly_revenue"] >= 10_000].reset_index(drop=True)

        # Plafonner la croissance à ±100% pour éviter les pics aberrants
        growth_capped = df["growth_pct"].clip(-100, 100)

        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.12,
            subplot_titles=(
                "Revenue mensuel & croissance (%)",
                "Cumul du chiffre d'affaires",
            ),
            specs=[[{"secondary_y": True}], [{"secondary_y": False}]],
        )

        # --- Subplot 1 : revenue (bar) + growth_pct (line, secondary y) ---
        fig.add_trace(
            go.Bar(
                x=df["month_label"],
                y=df["monthly_revenue"],
                name="Revenue (R$)",
                marker_color=CHART_COLORS[0],
                opacity=0.85,
            ),
            row=1, col=1, secondary_y=False,
        )

        fig.add_trace(
            go.Scatter(
                x=df["month_label"],
                y=growth_capped,
                name="Croissance (%)",
                mode="lines+markers",
                line=dict(color=CHART_COLORS[1], width=2),
                marker=dict(size=5),
            ),
            row=1, col=1, secondary_y=True,
        )

        # --- Subplot 2 : running total (area) ---
        fig.add_trace(
            go.Scatter(
                x=df["month_label"],
                y=df["running_total"],
                name="Cumul CA",
                mode="lines",
                fill="tozeroy",
                line=dict(color=CHART_COLORS[2], width=2),
                fillcolor="rgba(0, 229, 255, 0.15)",
            ),
            row=2, col=1,
        )

        fig.update_layout(
            template=PLOTLY_TEMPLATE,
            height=650,
            margin=dict(l=50, r=50, t=50, b=40),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.04,
                xanchor="center",
                x=0.5,
            ),
        )

        fig.update_yaxes(title_text="Revenue (R$)", row=1, col=1, secondary_y=False)
        fig.update_yaxes(
            title_text="Croissance (%)", range=[-100, 100],
            row=1, col=1, secondary_y=True,
        )
        fig.update_yaxes(title_text="Cumul (R$)", row=2, col=1)
        fig.update_xaxes(title_text="Mois", row=2, col=1)

        ui.plotly(fig).classes("w-full")

        # Insight tendances
        if len(df) >= 2:
            cumul = df["running_total"].iloc[-1]
            cumul_fmt = f"R$ {cumul / 1_000_000:.1f}M"
            valid_growth = growth_capped.dropna()
            avg_growth = valid_growth.mean() if len(valid_growth) > 0 else 0
            sign = "+" if avg_growth > 0 else ""
            insight_block(
                f"Le CA cumule atteint <b>{cumul_fmt}</b>. "
                f"La croissance mensuelle moyenne est de <b>{sign}{avg_growth:.1f}%</b>. "
                + (
                    "La tendance est haussiere, signe d'une adoption croissante."
                    if avg_growth > 5
                    else "La croissance se stabilise, typique d'un marche en maturation."
                )
            )

    sql_viewer(
        title="Analyse des tendances mensuelles",
        description=(
            "CTE (WITH ... AS), fonctions de fenetre (LAG, SUM OVER), "
            "GROUP BY, COUNT(DISTINCT), NULLIF, ROUND"
        ),
        sql_file="trends_monthly.sql",
        chart_builder=_build_trends_chart,
    )
