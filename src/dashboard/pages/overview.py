"""Page Vue d'ensemble — KPIs globaux et sparkline mensuelle."""

import pandas as pd
import plotly.graph_objects as go
from nicegui import ui

from src.dashboard import db
from src.dashboard.theme import ACCENT, CHART_COLORS, PLOTLY_TEMPLATE, PRIMARY, SECONDARY
from src.dashboard.components.page_layout import layout
from src.dashboard.components.kpi_card import kpi_card
from src.dashboard.components.sql_viewer import sql_viewer
from src.dashboard.components.insight import insight_block


@ui.page("/")
def page() -> None:
    layout(current_path="/")
    content()


def content() -> None:
    """Construit le contenu de la page Vue d'ensemble."""

    # ── Titre + description narrative ─────────────────────────────────────
    ui.label("Vue d'ensemble").classes("page-title")
    with ui.element("div").classes("narrative-block"):
        ui.html(
            "Bienvenue sur le <b>SQL Explorer Olist</b>. "
            "Cette page donne une vision synthetique de l'activite : "
            "nombre de commandes livrees, chiffre d'affaires total, "
            "satisfaction client moyenne et delai de livraison. "
            "La sparkline en bas illustre l'evolution mensuelle du CA."
        )

    # ── KPI cards ─────────────────────────────────────────────────────────
    _, df_kpis = db.query_from_file("overview_kpis.sql")
    if df_kpis.empty:
        ui.label("Aucune donnee KPI disponible.").classes("text-center mt-4")
    else:
        row = df_kpis.iloc[0]

        total_orders_raw = row.get("total_orders", 0)
        total_revenue_raw = row.get("total_revenue", 0.0)
        avg_review_raw = row.get("avg_review", 0.0)
        avg_delivery_raw = row.get("avg_delivery_days", 0.0)

        total_orders_num = int(total_orders_raw) if pd.notna(total_orders_raw) else 0
        total_revenue_num = float(total_revenue_raw) if pd.notna(total_revenue_raw) else 0.0
        review_val = float(avg_review_raw) if pd.notna(avg_review_raw) else 0.0
        avg_delivery_num = float(avg_delivery_raw) if pd.notna(avg_delivery_raw) else 0.0

        total_orders = f"{total_orders_num:,}".replace(",", " ")
        total_revenue = f"R$ {total_revenue_num / 1_000_000:.1f}M"
        avg_review = f"{review_val:.1f} / 5"
        avg_delivery = f"{avg_delivery_num:.1f} jours"

        with ui.row().classes("w-full flex-wrap gap-4"):
            kpi_card(
                title="Commandes livrees",
                value=total_orders,
                icon="shopping_cart",
                color=PRIMARY,
            )
            kpi_card(
                title="Chiffre d'affaires",
                value=total_revenue,
                icon="attach_money",
                color=SECONDARY,
            )
            kpi_card(
                title="Note moyenne",
                value=avg_review,
                icon="star",
                color=ACCENT,
            )
            kpi_card(
                title="Delai moyen",
                value=avg_delivery,
                icon="local_shipping",
                color=CHART_COLORS[3],
            )

        # ── Insight KPI ─────────────────────────────────────────────────────
        satisfaction = (
            "excellente" if review_val >= 4.0
            else "correcte" if review_val >= 3.0
            else "a ameliorer"
        )
        insight_block(
            f"Avec <b>{total_orders}</b> commandes livrees pour un CA de <b>{total_revenue}</b>, "
            f"la note moyenne de <b>{review_val:.1f}/5</b> indique une satisfaction client "
            f"<b>{satisfaction}</b>. Le delai moyen de <b>{avg_delivery}</b> reste competitif "
            f"pour le e-commerce bresilien."
        )

    # ── Sparkline mensuelle ───────────────────────────────────────────────
    def _build_sparkline(df):
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=df["month_label"],
            y=df["monthly_revenue"],
            mode="lines",
            fill="tozeroy",
            line=dict(color=PRIMARY, width=2),
            fillcolor="rgba(0, 200, 83, 0.15)",
            name="Revenue mensuel",
        ))
        fig.update_layout(
            template=PLOTLY_TEMPLATE,
            height=300,
            margin=dict(l=40, r=20, t=30, b=40),
            xaxis_title="Mois",
            yaxis_title="Revenue (R$)",
            showlegend=False,
        )
        ui.plotly(fig).classes("w-full")

        # Insight sparkline
        if len(df) >= 2:
            best_month = df.loc[df["monthly_revenue"].idxmax()]
            best_label = best_month["month_label"]
            best_val = best_month["monthly_revenue"]
            last_val = df.iloc[-1]["monthly_revenue"]
            insight_block(
                f"Le mois le plus fort est <b>{best_label}</b> avec "
                f"<b>R$ {best_val:,.0f}</b>. ".replace(",", " ")
                + f"Le dernier mois enregistre <b>R$ {last_val:,.0f}</b>.".replace(",", " ")
            )

    sql_viewer(
        title="Evolution mensuelle du chiffre d'affaires",
        description="JOIN, GROUP BY, ORDER BY, fonctions d'agregation (SUM, ROUND)",
        sql_file="overview_monthly_mini.sql",
        chart_builder=_build_sparkline,
    )
