"""Page Optimisation SQL — benchmarks mesures avec KPIs et graphiques."""

import asyncio

from nicegui import background_tasks, ui

from src.dashboard.components.benchmark import (
    BenchmarkResult,
    get_cache,
    clear_cache,
    run_all_benchmarks,
)
from src.dashboard.components.kpi_card import kpi_card
from src.dashboard.components.page_layout import layout
from src.dashboard.theme import ACCENT, BG_CARD, DANGER, PRIMARY, SECONDARY

# ── Comparaisons avant/apres ─────────────────────────────────────────────

COMPARISONS = [
    {
        "title": "Index B-Tree sur order_status",
        "technique": "Creation d'index",
        "icon": "search",
        "before_label": "Full table scan (NOT INDEXED)",
        "before_sql": (
            "SELECT COUNT(*)\n"
            "FROM fact_orders NOT INDEXED\n"
            "WHERE order_status = 'delivered'"
        ),
        "after_label": "Recherche via index idx_fact_order_status",
        "after_sql": (
            "SELECT COUNT(*)\n"
            "FROM fact_orders INDEXED BY idx_fact_order_status\n"
            "WHERE order_status = 'delivered'"
        ),
        "explanation": (
            "**Technique : Index B-Tree**\n\n"
            "Sans index, SQLite doit parcourir **toutes les lignes** de la table "
            "(`SCAN`) pour trouver celles qui correspondent au filtre — complexite O(n).\n\n"
            "Avec un index B-Tree sur `order_status`, le moteur effectue une "
            "**recherche binaire** dans l'arbre d'index (`SEARCH`) — complexite O(log n).\n\n"
            "Sur ~112 000 lignes, le gain est significatif pour les requetes filtrees "
            "frequemment sur le statut."
        ),
        "kpi_icon": "search",
        "kpi_color": PRIMARY,
    },
    {
        "title": "SELECT * vs colonnes ciblees",
        "technique": "Projection minimale",
        "icon": "compress",
        "before_label": "SELECT * + LIMIT 1000",
        "before_sql": (
            "SELECT *\n"
            "FROM fact_orders\n"
            "ORDER BY date_key DESC\n"
            "LIMIT 1000"
        ),
        "after_label": "Colonnes ciblees + LIMIT 1000",
        "after_sql": (
            "SELECT order_id, order_status, price\n"
            "FROM fact_orders\n"
            "ORDER BY date_key DESC\n"
            "LIMIT 1000"
        ),
        "explanation": (
            "**Technique : Projection minimale (comparaison a volume egal)**\n\n"
            "- `SELECT *` transfere **toutes les colonnes**, meme inutilisees — "
            "augmente le volume de donnees en memoire et empeche l'utilisation "
            "d'index couvrants (covering index).\n\n"
            "- Ici, les deux requetes lisent **le meme nombre de lignes** "
            "(LIMIT 1000) pour isoler l'effet de la projection.\n\n"
            "**Bonne pratique :** toujours nommer explicitement les colonnes "
            "necessaires, surtout sur les requetes interactives."
        ),
        "kpi_icon": "compress",
        "kpi_color": SECONDARY,
    },
    {
        "title": "Sous-requete correlee vs CTE materialisee",
        "technique": "Materialisation CTE",
        "icon": "account_tree",
        "before_label": "Sous-requete correlee (executee par ligne)",
        "before_sql": (
            "SELECT\n"
            "    o.order_id,\n"
            "    o.price,\n"
            "    (SELECT AVG(o2.price)\n"
            "     FROM fact_orders o2\n"
            "     WHERE o2.order_status = o.order_status\n"
            "    ) AS avg_status_value\n"
            "FROM fact_orders o\n"
            "LIMIT 100"
        ),
        "after_label": "CTE materialisee (calculee une seule fois)",
        "after_sql": (
            "WITH status_avg AS MATERIALIZED (\n"
            "    SELECT order_status,\n"
            "           AVG(price) AS avg_value\n"
            "    FROM fact_orders\n"
            "    GROUP BY order_status\n"
            ")\n"
            "SELECT\n"
            "    o.order_id,\n"
            "    o.price,\n"
            "    sa.avg_value AS avg_status_value\n"
            "FROM fact_orders o\n"
            "JOIN status_avg sa ON sa.order_status = o.order_status\n"
            "LIMIT 100"
        ),
        "explanation": (
            "**Technique : CTE materialisee (MATERIALIZED)**\n\n"
            "- La **sous-requete correlee** est re-executee pour **chaque ligne** "
            "de la requete principale — cout O(n x m).\n\n"
            "- La **CTE materialisee** calcule la moyenne **une seule fois** par "
            "statut, puis effectue un simple JOIN — cout O(n + m).\n\n"
            "Le plan d'execution montre la difference : `CORRELATED SCALAR SUBQUERY` "
            "vs `MATERIALIZE` suivi d'un `SCAN` unique sur le resultat pre-calcule."
        ),
        "kpi_icon": "account_tree",
        "kpi_color": ACCENT,
    },
]

ITERATIONS = 30
WARMUP = 5


@ui.page("/optimisation")
def page() -> None:
    layout(current_path="/optimisation")
    content()


def content() -> None:
    """Construit le contenu de la page Optimisation SQL."""
    with ui.element("div").classes("narrative-block"):
        ui.html(
            "<b>Optimisation SQL</b> — "
            "Cette page mesure en temps reel les performances de 3 techniques "
            "d'optimisation SQL. Chaque requete est executee "
            f"jusqu'a <b>{ITERATIONS} fois</b> (adapte automatiquement pour les "
            "requetes lentes) sur la base SQLite du projet (~112 000 commandes). "
            "Les temps affiches sont des <b>moyennes reelles</b>, pas des estimations."
        )

    async def _on_rerun():
        clear_cache()
        await benchmark_content.refresh()

    with ui.row().classes("items-center gap-2 mb-4"):
        ui.button(
            "Relancer le benchmark",
            icon="refresh",
            on_click=_on_rerun,
        ).props("outline").style(
            f"color: {PRIMARY}; border-color: {PRIMARY}"
        )
        ui.label("Mesures en direct via time.perf_counter()").style(
            "color: #9E9E9E; font-size: 0.8rem"
        )

    background_tasks.create(benchmark_content(), name="benchmark_init")


@ui.refreshable
async def benchmark_content() -> None:
    """Execute les benchmarks et affiche les resultats (avec cache)."""
    cached = get_cache()
    if cached:
        _render_results(cached)
        return

    # Pas de cache → spinner + lancement en arriere-plan
    with ui.column().classes("w-full items-center py-8"):
        ui.spinner("dots", size="xl").style(f"color: {PRIMARY}")
        ui.label("Execution des benchmarks...").style(
            "color: #9E9E9E; font-size: 0.9rem"
        )

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None,
        lambda: run_all_benchmarks(COMPARISONS, iterations=ITERATIONS, warmup=WARMUP),
    )
    benchmark_content.refresh()


def _render_results(results: list[BenchmarkResult]) -> None:
    """Affiche les resultats des benchmarks."""
    _render_summary_kpis(results)
    _render_summary_chart(results)
    for comp, result in zip(COMPARISONS, results):
        _render_comparison(comp, result)


# ── KPIs recapitulatifs ──────────────────────────────────────────────────


def _render_summary_kpis(results: list[BenchmarkResult]) -> None:
    """Affiche 3 KPI cards avec le speedup de chaque comparaison."""
    with ui.row().classes("w-full gap-4 mt-2 mb-4"):
        for comp, result in zip(COMPARISONS, results):
            kpi_card(
                title=comp["technique"],
                value=f"{result.speedup}x",
                subtitle=(
                    f"{result.time_before_ms}ms → {result.time_after_ms}ms"
                ),
                icon=comp.get("kpi_icon", "speed"),
                color=comp.get("kpi_color", PRIMARY),
            )


# ── Bar chart resume ─────────────────────────────────────────────────────


def _render_summary_chart(results: list[BenchmarkResult]) -> None:
    """Bar chart groupe horizontal — resume des 3 comparaisons."""
    labels = [r.label for r in results]
    before_vals = [r.time_before_ms for r in results]
    after_vals = [r.time_after_ms for r in results]

    chart = ui.echart(
        {
            "darkMode": True,
            "backgroundColor": "transparent",
            "tooltip": {
                "trigger": "axis",
                "axisPointer": {"type": "shadow"},
                "formatter": "{b}<br/>{a0}: {c0} ms<br/>{a1}: {c1} ms",
            },
            "legend": {
                "data": ["Avant", "Apres"],
                "textStyle": {"color": "#E0E0E0"},
            },
            "grid": {
                "left": "3%",
                "right": "6%",
                "bottom": "3%",
                "containLabel": True,
            },
            "xAxis": {
                "type": "value",
                "name": "Temps (ms)",
                "nameTextStyle": {"color": "#9E9E9E"},
                "axisLabel": {"color": "#9E9E9E"},
            },
            "yAxis": {
                "type": "category",
                "data": labels,
                "axisLabel": {"color": "#E0E0E0", "fontSize": 11},
            },
            "series": [
                {
                    "name": "Avant",
                    "type": "bar",
                    "data": before_vals,
                    "itemStyle": {"color": DANGER},
                    "label": {
                        "show": True,
                        "position": "right",
                        "formatter": "{c} ms",
                        "color": "#E0E0E0",
                        "fontSize": 11,
                    },
                },
                {
                    "name": "Apres",
                    "type": "bar",
                    "data": after_vals,
                    "itemStyle": {"color": PRIMARY},
                    "label": {
                        "show": True,
                        "position": "right",
                        "formatter": "{c} ms",
                        "color": "#E0E0E0",
                        "fontSize": 11,
                    },
                },
            ],
        }
    )
    chart.classes("w-full").style("height: 220px")


# ── Section detaillee par comparaison ────────────────────────────────────


def _render_comparison(comp: dict, result: BenchmarkResult) -> None:
    """Affiche une section detaillee pour une comparaison."""
    ui.separator().classes("my-4")

    # Titre + badge technique
    with ui.row().classes("items-center gap-2 mt-4"):
        ui.icon(comp["icon"]).classes("text-2xl").style(f"color: {PRIMARY}")
        ui.label(comp["title"]).classes("page-title")
        ui.badge(comp["technique"]).props("outline").style(
            f"color: {SECONDARY}; border-color: {SECONDARY}"
        )

    # 4 mini-metriques
    with ui.row().classes("w-full gap-3 mt-3 mb-3"):
        _mini_metric(
            "Avant",
            f"{result.time_before_ms} ms",
            f"± {result.std_before_ms} ms",
            DANGER,
        )
        _mini_metric(
            "Apres",
            f"{result.time_after_ms} ms",
            f"± {result.std_after_ms} ms",
            PRIMARY,
        )
        _mini_metric(
            "Acceleration",
            f"{result.speedup}x",
            "plus rapide",
            SECONDARY,
        )
        _mini_metric(
            "Iterations",
            str(result.iterations),
            "mesures",
            "#9E9E9E",
        )

    # Mini bar chart
    _render_mini_chart(result)

    # SQL collapsible
    with ui.expansion("Voir le code SQL", icon="code").classes(
        "w-full mt-2"
    ).style(f"background: {BG_CARD}; border-radius: 8px"):
        with ui.row().classes("w-full gap-4"):
            with ui.column().classes("flex-1"):
                ui.label(comp["before_label"]).classes("font-bold").style(
                    f"color: {DANGER}"
                )
                ui.code(comp["before_sql"], language="sql").classes("w-full")
            with ui.column().classes("flex-1"):
                ui.label(comp["after_label"]).classes("font-bold").style(
                    f"color: {PRIMARY}"
                )
                ui.code(comp["after_sql"], language="sql").classes("w-full")

    # EXPLAIN collapsible
    with ui.expansion("Voir le plan d'execution", icon="playlist_play").classes(
        "w-full mt-1"
    ).style(f"background: {BG_CARD}; border-radius: 8px"):
        with ui.row().classes("w-full gap-4"):
            with ui.column().classes("flex-1"):
                ui.label("AVANT").classes("text-xs font-bold").style(
                    f"color: {DANGER}"
                )
                _render_explain_block(result.explain_before, DANGER)
            with ui.column().classes("flex-1"):
                ui.label("APRES").classes("text-xs font-bold").style(
                    f"color: {PRIMARY}"
                )
                _render_explain_block(result.explain_after, PRIMARY)

    # Explication pedagogique
    with ui.card().classes("w-full mt-3").style(
        "background: rgba(0, 200, 83, 0.06); "
        "border-left: 3px solid #00C853; "
        "border-radius: 8px"
    ):
        ui.markdown(comp["explanation"])


# ── Helpers ──────────────────────────────────────────────────────────────


def _mini_metric(label: str, value: str, subtitle: str, color: str) -> None:
    """Affiche une mini-metrique inline."""
    with ui.card().classes("p-3").style(
        f"background: {BG_CARD}; border-radius: 8px; "
        f"border-top: 3px solid {color}; min-width: 130px; flex: 1 1 0%"
    ):
        ui.label(label).style("color: #9E9E9E; font-size: 0.75rem; text-transform: uppercase")
        ui.label(value).style(f"color: {color}; font-size: 1.4rem; font-weight: 700")
        ui.label(subtitle).style("color: #9E9E9E; font-size: 0.75rem")


def _render_mini_chart(result: BenchmarkResult) -> None:
    """Mini bar chart horizontal pour une comparaison."""
    chart = ui.echart(
        {
            "darkMode": True,
            "backgroundColor": "transparent",
            "grid": {
                "left": "2%",
                "right": "15%",
                "top": "5%",
                "bottom": "5%",
                "containLabel": True,
            },
            "xAxis": {
                "type": "value",
                "show": False,
            },
            "yAxis": {
                "type": "category",
                "data": ["Apres", "Avant"],
                "axisLabel": {"color": "#E0E0E0", "fontSize": 11},
                "axisLine": {"show": False},
                "axisTick": {"show": False},
            },
            "series": [
                {
                    "type": "bar",
                    "data": [
                        {"value": result.time_after_ms, "itemStyle": {"color": PRIMARY}},
                        {"value": result.time_before_ms, "itemStyle": {"color": DANGER}},
                    ],
                    "barWidth": "50%",
                    "label": {
                        "show": True,
                        "position": "right",
                        "formatter": "{c} ms",
                        "color": "#E0E0E0",
                        "fontSize": 11,
                    },
                }
            ],
        }
    )
    chart.classes("w-full").style("height: 120px")


def _render_explain_block(lines: list[str], color: str) -> None:
    """Affiche les lignes du plan d'execution dans un bloc monospace."""
    with ui.element("div").style(
        "background: #1a1a2e; "
        "border-radius: 6px; "
        "padding: 10px 14px; "
        f"border-left: 3px solid {color}; "
        "font-family: monospace; "
        "font-size: 0.82rem"
    ):
        for line in lines:
            ui.label(line).style("color: #E0E0E0; margin: 2px 0")
