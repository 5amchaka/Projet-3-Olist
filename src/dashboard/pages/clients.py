"""Page Clients — Nouveaux vs recurrents, LTV par cohorte."""

import pandas as pd
import plotly.graph_objects as go
from nicegui import ui

from src.dashboard.components.page_layout import layout
from src.dashboard.components.sql_viewer import sql_viewer
from src.dashboard.theme import CHART_COLORS, PLOTLY_TEMPLATE, PRIMARY, SECONDARY
from src.dashboard.components.insight import insight_block


@ui.page("/clients")
def page() -> None:
    layout(current_path="/clients")
    content()


def content() -> None:
    """Construit le contenu de la page Clients."""
    with ui.element("div").classes("narrative-block"):
        ui.html(
            "<b>Analyse clients</b> — "
            "Cette page distingue les <b>nouveaux clients</b> (premier achat) "
            "des <b>clients recurrents</b> (deja achete auparavant) mois par mois. "
            "La seconde analyse calcule la <b>Lifetime Value (LTV)</b> par cohorte : "
            "combien de revenu chaque groupe de clients genere au fil du temps."
        )

    # ── Nouveaux vs recurrents ─────────────────────────────────────────
    sql_viewer(
        title="Nouveaux clients vs recurrents par mois",
        description=(
            "<code>CTEs multi-niveaux</code>, "
            "<code>MIN() premiere commande</code>, "
            "<code>CASE WHEN classification</code>, "
            "<code>COUNT(DISTINCT CASE WHEN)</code>"
        ),
        sql_file="new_vs_recurring.sql",
        chart_builder=_build_new_vs_recurring,
    )

    # ── LTV par cohorte ────────────────────────────────────────────────
    sql_viewer(
        title="Lifetime Value (LTV) par cohorte",
        description=(
            "<code>CTEs multi-niveaux (3)</code>, "
            "<code>SUM() OVER (PARTITION BY ... ORDER BY ...)</code>, "
            "<code>Sous-requete correlee</code>, "
            "<code>Calcul delta mois AAAAMM</code>"
        ),
        sql_file="ltv_cohorts.sql",
        chart_builder=_build_ltv_cohorts,
        show_table=True,
    )


def _build_new_vs_recurring(df: pd.DataFrame) -> None:
    """Stacked bar chart — nouveaux vs recurrents par mois."""
    if df.empty:
        ui.label("Aucune donnee disponible.").classes("text-center mt-4")
        return

    # Filtrer les mois non representatifs
    df = df[df["total"] >= 50].reset_index(drop=True)
    if df.empty:
        ui.label("Aucune donnee disponible apres filtrage.").classes("text-center mt-4")
        return

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=df["month_label"],
            y=df["new_customers"],
            name="Nouveaux",
            marker_color=CHART_COLORS[0],
            hovertemplate="Mois: %{x}<br>Nouveaux: %{y}<extra></extra>",
        )
    )

    fig.add_trace(
        go.Bar(
            x=df["month_label"],
            y=df["recurring"],
            name="Recurrents",
            marker_color=CHART_COLORS[1],
            hovertemplate="Mois: %{x}<br>Recurrents: %{y}<extra></extra>",
        )
    )

    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        barmode="stack",
        height=450,
        margin=dict(l=50, r=30, t=30, b=50),
        xaxis_title="Mois",
        yaxis_title="Nombre de clients",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    )

    ui.plotly(fig).classes("w-full mt-4")

    # KPI complementaire : taux de clients recurrents
    total_new = df["new_customers"].sum()
    total_rec = df["recurring"].sum()
    pct_rec = total_rec * 100.0 / (total_new + total_rec) if (total_new + total_rec) > 0 else 0

    with ui.row().classes("w-full justify-center gap-8 mt-4"):
        with ui.column().classes("items-center"):
            ui.label(f"{total_new:,}".replace(",", " ")).classes("kpi-value").style(
                f"color: {CHART_COLORS[0]}; font-size: 1.5rem"
            )
            ui.label("Nouveaux clients (total)").classes("kpi-label")
        with ui.column().classes("items-center"):
            ui.label(f"{total_rec:,}".replace(",", " ")).classes("kpi-value").style(
                f"color: {CHART_COLORS[1]}; font-size: 1.5rem"
            )
            ui.label("Clients recurrents (total)").classes("kpi-label")
        with ui.column().classes("items-center"):
            ui.label(f"{pct_rec:.1f} %").classes("kpi-value").style(
                f"color: {SECONDARY}; font-size: 1.5rem"
            )
            ui.label("Taux de recurrence").classes("kpi-label")

    # Insight nouveaux vs recurrents
    best_month = df.loc[df["new_customers"].idxmax()]
    insight_block(
        f"Avec seulement <b>{pct_rec:.1f}%</b> de clients recurrents, "
        f"la plateforme depend fortement de l'acquisition. "
        f"Le pic d'acquisition est en <b>{best_month['month_label']}</b> "
        f"avec <b>{int(best_month['new_customers'])}</b> nouveaux clients. "
        f"Augmenter la recurrence serait le levier de croissance le plus rentable."
    )


def _build_ltv_cohorts(df: pd.DataFrame) -> None:
    """Line chart — LTV cumulative par cohorte."""
    if df.empty:
        ui.label("Aucune donnee disponible.").classes("text-center mt-4")
        return

    # Convertir cohort_month en label lisible
    df = df.copy()
    df["cohort_label"] = (
        (df["cohort_month"] // 100).astype(str)
        + "-"
        + (df["cohort_month"] % 100).apply(lambda m: f"{m:02d}")
    )

    # Selectionner les cohortes avec assez de clients (>= 500 au mois 0)
    month0 = df[df["months_since_first"] == 0]
    large_cohorts = month0[month0["nb_customers"] >= 500]["cohort_label"].tolist()

    if not large_cohorts:
        # Fallback : prendre les 6 plus grandes cohortes
        large_cohorts = month0.nlargest(6, "nb_customers")["cohort_label"].tolist()

    fig = go.Figure()

    for i, cohort in enumerate(large_cohorts):
        cohort_data = df[df["cohort_label"] == cohort]
        fig.add_trace(
            go.Scatter(
                x=cohort_data["months_since_first"],
                y=cohort_data["ltv_per_customer"],
                mode="lines+markers",
                name=cohort,
                line=dict(color=CHART_COLORS[i % len(CHART_COLORS)], width=2),
                marker=dict(size=4),
                hovertemplate=(
                    f"Cohorte {cohort}<br>"
                    "Mois +%{x}<br>"
                    "LTV: R$ %{y:.2f}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        height=500,
        margin=dict(l=60, r=40, t=40, b=60),
        xaxis_title="Mois depuis le premier achat",
        yaxis_title="LTV par client (R$)",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
        ),
    )

    ui.plotly(fig).classes("w-full mt-4")

    # Insight LTV cohortes
    if large_cohorts:
        best_ltv_cohort = None
        best_ltv_val = 0
        for cohort in large_cohorts:
            cdata = df[df["cohort_label"] == cohort]
            if not cdata.empty:
                last_ltv = cdata["ltv_per_customer"].iloc[-1]
                if last_ltv > best_ltv_val:
                    best_ltv_val = last_ltv
                    best_ltv_cohort = cohort
        if best_ltv_cohort:
            insight_block(
                f"La cohorte la plus rentable est <b>{best_ltv_cohort}</b> "
                f"avec une LTV de <b>R$ {best_ltv_val:.2f}</b> par client. "
                f"Les cohortes plus recentes n'ont pas encore eu le temps de "
                f"developper leur plein potentiel de valeur."
            )
