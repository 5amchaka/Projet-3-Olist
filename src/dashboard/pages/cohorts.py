"""Page Cohortes rétention — heatmap ECharts."""

import pandas as pd
from nicegui import ui

from src.dashboard.components.page_layout import layout
from src.dashboard.components.sql_viewer import sql_viewer
from src.dashboard.theme import PRIMARY
from src.dashboard.components.insight import insight_block


@ui.page("/cohorts")
def page() -> None:
    layout(current_path="/cohorts")
    content()


def content() -> None:
    """Construit le contenu de la page Cohortes retention."""
    with ui.element("div").classes("narrative-block"):
        ui.html(
            "<b>Cohortes de rétention</b> — "
            "Les clients sont regroupés par mois de premier achat (cohorte). "
            "Pour chaque cohorte on mesure combien reviennent acheter 1, 2, 3… mois "
            "après. La heatmap montre le <b>taux de rétention</b> : "
            "le mois 0 vaut 100 %, les mois suivants indiquent la part de clients "
            "qui ont effectué au moins un nouvel achat."
        )

    # ── SQL viewer + heatmap ─────────────────────────────────────────────
    sql_viewer(
        title="Rétention par cohorte mensuelle",
        description=(
            "<code>DATE / strftime</code>, "
            "<code>GROUP BY cohorte</code>, "
            "<code>COUNT DISTINCT</code>, "
            "<code>auto-jointure (self-join)</code>"
        ),
        sql_file="cohorts_retention.sql",
        chart_builder=_build_heatmap,
        show_table=True,
    )


def _build_heatmap(df: pd.DataFrame) -> None:
    """Construit la heatmap ECharts de rétention par cohorte."""
    if df.empty:
        ui.label("Aucune donnée de cohorte disponible.").classes("text-center mt-4")
        return

    # Pivot : lignes = cohorte, colonnes = mois depuis 1er achat
    pivot = df.pivot(
        index="cohort_month",
        columns="months_since_first",
        values="nb_customers",
    )

    # Filtrer les cohortes trop petites (< 50 clients au mois 0)
    if 0 in pivot.columns:
        pivot = pivot[pivot[0] >= 50]

    if pivot.empty:
        ui.label("Pas assez de données pour les cohortes.").classes("text-center mt-4")
        return

    # Taux de rétention (%) relatif au mois 0
    month_zero = pivot[0]
    retention = pivot.div(month_zero, axis=0) * 100

    # Préparer les axes
    cohorts = [str(c) for c in pivot.index]
    # Exclure mois 0 (toujours 100%) pour mieux voir la rétention réelle
    ret_cols = [c for c in pivot.columns if c > 0]
    months_labels = [str(m) for m in ret_cols]

    # Carte du mois 0 : affichée séparément comme texte
    cohort_sizes = {str(c): int(pivot.loc[c, 0]) for c in pivot.index}

    # Données heatmap : [x (mois), y (cohorte), valeur (%)] — sans mois 0
    data = []
    for i, cohort_key in enumerate(pivot.index):
        for j, month_col in enumerate(ret_cols):
            val = retention.loc[cohort_key, month_col] if month_col in retention.columns else None
            if pd.notna(val):
                data.append([j, i, round(val, 1)])

    # Calculer le max réel (hors mois 0) pour l'échelle de couleur
    vals = [d[2] for d in data if d[2] > 0]
    max_val = max(vals) if vals else 1.0
    # Arrondir vers le haut au prochain entier
    max_scale = min(max(round(max_val + 0.5), 1), 100)

    options = {
        "tooltip": {"position": "top"},
        "grid": {
            "top": 40,
            "bottom": 60,
            "left": 120,
            "right": 40,
        },
        "xAxis": {
            "type": "category",
            "data": months_labels,
            "name": "Mois depuis 1er achat",
            "nameLocation": "center",
            "nameGap": 35,
            "splitArea": {"show": True},
        },
        "yAxis": {
            "type": "category",
            "data": cohorts,
            "name": "Cohorte",
            "nameLocation": "center",
            "nameGap": 90,
            "splitArea": {"show": True},
        },
        "visualMap": {
            "min": 0,
            "max": max_scale,
            "calculable": True,
            "orient": "horizontal",
            "left": "center",
            "bottom": 0,
            "inRange": {
                "color": ["#1a1a2e", "#0d3320", "#1a6640", "#27996b", PRIMARY],
            },
            "textStyle": {"color": "#ccc"},
        },
        "series": [
            {
                "type": "heatmap",
                "data": data,
                "label": {
                    "show": True,
                    "fontSize": 10,
                    "formatter": "{@[2]} %",
                },
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowColor": "rgba(0, 0, 0, 0.5)",
                    }
                },
            }
        ],
    }

    ui.echart(options).classes("w-full").style("height: 450px")

    # Insight cohortes
    if ret_cols and len(retention) > 0:
        # Retention moyenne au mois 1
        if 1 in retention.columns:
            avg_ret_m1 = retention[1].mean()
            best_cohort_idx = retention[1].idxmax()
            best_cohort_val = retention.loc[best_cohort_idx, 1]
            insight_block(
                f"La retention moyenne au mois 1 est de <b>{avg_ret_m1:.1f}%</b>, "
                f"typique du e-commerce. La meilleure cohorte est "
                f"<b>{best_cohort_idx}</b> avec <b>{best_cohort_val:.1f}%</b> de retention. "
                f"Ameliorer la retention au mois 1 aurait un effet multiplicateur sur la LTV."
            )

    # Afficher la taille des cohortes en complément
    ui.label("Taille des cohortes (clients au mois 0)").classes("page-title mt-4")
    size_df = pd.DataFrame([
        {"Cohorte": k, "Clients": v} for k, v in cohort_sizes.items()
    ])
    ui.table.from_pandas(size_df).classes("w-full mt-2")
