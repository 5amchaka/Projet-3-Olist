"""Page Ventes — Top produits, CA YoY, panier moyen."""

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from nicegui import ui

from src.dashboard.components.page_layout import layout
from src.dashboard.components.sql_viewer import sql_viewer
from src.dashboard.theme import CHART_COLORS, PLOTLY_TEMPLATE, PRIMARY, SECONDARY
from src.dashboard.components.insight import insight_block


@ui.page("/ventes")
def page() -> None:
    layout(current_path="/ventes")
    content()


def content() -> None:
    """Construit le contenu de la page Ventes."""
    with ui.element("div").classes("narrative-block"):
        ui.html(
            "<b>Analyse des ventes</b> — "
            "Cette page explore trois dimensions complementaires : "
            "les <b>categories de produits les plus rentables</b> (Top 10), "
            "l'<b>evolution annuelle du CA</b> (Year-over-Year), "
            "et le <b>panier moyen mensuel</b> qui mesure la valeur "
            "moyenne de chaque commande au fil du temps."
        )

    # ── Top 10 produits ────────────────────────────────────────────────
    sql_viewer(
        title="Top 10 categories par chiffre d'affaires",
        description=(
            "<code>CTE</code>, "
            "<code>ROW_NUMBER() OVER</code>, "
            "<code>COALESCE</code>, "
            "<code>JOIN dim_products</code>, "
            "<code>LIMIT</code>"
        ),
        sql_file="top_products.sql",
        chart_builder=_build_top_products,
        show_table=True,
    )

    # ── CA YoY ─────────────────────────────────────────────────────────
    sql_viewer(
        title="Evolution du CA annee sur annee",
        description=(
            "<code>CTE</code>, "
            "<code>LAG() OVER</code>, "
            "<code>NULLIF</code>, "
            "<code>Calcul YoY (%)</code>"
        ),
        sql_file="ca_yoy.sql",
        chart_builder=_build_ca_yoy,
        show_table=True,
    )

    # ── Panier moyen ───────────────────────────────────────────────────
    sql_viewer(
        title="Panier moyen mensuel",
        description=(
            "<code>Vue v_monthly_sales</code>, "
            "<code>ORDER BY</code>, "
            "<code>projection des metriques mensuelles</code>"
        ),
        sql_file="basket_avg.sql",
        chart_builder=_build_basket_avg,
    )


def _build_top_products(df: pd.DataFrame) -> None:
    """Bar chart horizontal — Top 10 produits par CA."""
    if df.empty:
        ui.label("Aucune donnee disponible.").classes("text-center mt-4")
        return

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["total_revenue"],
            y=df["category_name"],
            orientation="h",
            marker_color=CHART_COLORS[0],
            text=df["total_revenue"].apply(lambda v: f"R$ {v:,.0f}"),
            textposition="auto",
            hovertemplate=(
                "%{y}<br>"
                "CA: R$ %{x:,.2f}<br>"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=450,
        yaxis=dict(autorange="reversed"),
        xaxis_title="Chiffre d'affaires (R$)",
        margin=dict(l=180, r=40, t=30, b=50),
    )

    ui.plotly(fig).classes("w-full mt-4")

    # Insight top produits
    top1 = df.iloc[0]
    top3_rev = df.head(3)["total_revenue"].sum()
    top10_rev = df["total_revenue"].sum()
    pct_top3 = top3_rev * 100 / top10_rev if top10_rev > 0 else 0
    insight_block(
        f"La categorie <b>{top1['category_name']}</b> domine avec "
        f"<b>R$ {top1['total_revenue']:,.0f}</b> de CA. ".replace(",", " ")
        + f"Les 3 premieres categories concentrent <b>{pct_top3:.0f}%</b> du Top 10, "
        f"revelant une forte concentration sectorielle."
    )


def _build_ca_yoy(df: pd.DataFrame) -> None:
    """Grouped bar chart — CA annuel + taux de croissance YoY."""
    if df.empty:
        ui.label("Aucune donnee disponible.").classes("text-center mt-4")
        return

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=df["year"].astype(str),
            y=df["annual_revenue"],
            name="CA annuel (R$)",
            marker_color=CHART_COLORS[0],
            text=df["annual_revenue"].apply(lambda v: f"R$ {v / 1e6:.1f}M"),
            textposition="outside",
        ),
        secondary_y=False,
    )

    # Croissance YoY (ligne sur axe secondaire)
    yoy = df[df["yoy_growth_pct"].notna()]
    fig.add_trace(
        go.Scatter(
            x=yoy["year"].astype(str),
            y=yoy["yoy_growth_pct"],
            name="Croissance YoY (%)",
            mode="lines+markers+text",
            line=dict(color=SECONDARY, width=3),
            marker=dict(size=10),
            text=yoy["yoy_growth_pct"].apply(lambda v: f"+{v:.0f}%" if v > 0 else f"{v:.0f}%"),
            textposition="top center",
        ),
        secondary_y=True,
    )

    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=400,
        margin=dict(l=60, r=60, t=40, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )
    fig.update_yaxes(title_text="CA (R$)", secondary_y=False)
    fig.update_yaxes(title_text="Croissance (%)", secondary_y=True)
    fig.update_xaxes(title_text="Annee")

    ui.plotly(fig).classes("w-full mt-4")

    # Insight CA YoY
    if len(df) >= 2:
        best_year = df.loc[df["annual_revenue"].idxmax()]
        last_yoy = df[df["yoy_growth_pct"].notna()]
        if not last_yoy.empty:
            latest = last_yoy.iloc[-1]
            sign = "+" if latest["yoy_growth_pct"] > 0 else ""
            insight_block(
                f"L'annee <b>{int(best_year['year'])}</b> enregistre le CA le plus eleve "
                f"avec <b>R$ {best_year['annual_revenue'] / 1e6:.1f}M</b>. "
                f"La derniere croissance YoY est de <b>{sign}{latest['yoy_growth_pct']:.0f}%</b>."
            )


def _build_basket_avg(df: pd.DataFrame) -> None:
    """Line chart — evolution du panier moyen mensuel."""
    if df.empty:
        ui.label("Aucune donnee disponible.").classes("text-center mt-4")
        return

    # Filtrer les mois non representatifs (< 100 commandes)
    df = df[df["monthly_orders"] >= 100].reset_index(drop=True)
    if df.empty:
        ui.label("Aucune donnee disponible apres filtrage.").classes("text-center mt-4")
        return

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["month_label"],
            y=df["avg_basket"],
            mode="lines+markers",
            line=dict(color=PRIMARY, width=2),
            marker=dict(size=5),
            fill="tozeroy",
            fillcolor="rgba(0, 200, 83, 0.1)",
            name="Panier moyen",
            hovertemplate="Mois: %{x}<br>Panier: R$ %{y:.2f}<extra></extra>",
        )
    )

    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=350,
        margin=dict(l=50, r=30, t=30, b=50),
        xaxis_title="Mois",
        yaxis_title="Panier moyen (R$)",
        showlegend=False,
    )

    ui.plotly(fig).classes("w-full mt-4")

    # Insight panier moyen
    if len(df) >= 2:
        avg_basket_global = df["avg_basket"].mean()
        best_basket = df.loc[df["avg_basket"].idxmax()]
        insight_block(
            f"Le panier moyen global est de <b>R$ {avg_basket_global:.2f}</b>. "
            f"Le pic est atteint en <b>{best_basket['month_label']}</b> "
            f"avec <b>R$ {best_basket['avg_basket']:.2f}</b>. "
            f"Un panier stable traduit une maturite des habitudes d'achat."
        )
