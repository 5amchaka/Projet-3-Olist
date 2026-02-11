"""Point d'entrée NiceGUI — routage des pages."""

import asyncio
import os

from nicegui import app, background_tasks, ui


async def _precompute_benchmarks() -> None:
    """Lance les benchmarks en arriere-plan pour remplir le cache."""
    from src.dashboard.pages.optimisation import COMPARISONS, ITERATIONS, WARMUP
    from src.dashboard.components.benchmark import run_all_benchmarks

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, lambda: run_all_benchmarks(COMPARISONS, iterations=ITERATIONS, warmup=WARMUP)
    )


def _get_dashboard_port(default: int = 8080) -> int:
    """Retourne le port du dashboard depuis DASHBOARD_PORT ou une valeur par defaut."""
    raw_port = os.getenv("DASHBOARD_PORT")
    if raw_port is None:
        return default
    try:
        port = int(raw_port)
    except ValueError:
        return default
    return port if 1 <= port <= 65535 else default


def _get_show_browser(default: bool = False) -> bool:
    """Active l'ouverture auto du navigateur via DASHBOARD_SHOW_BROWSER."""
    raw = os.getenv("DASHBOARD_SHOW_BROWSER")
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _schedule_benchmark_warmup() -> None:
    """Declenche le pre-calcul des benchmarks sans bloquer le startup."""
    background_tasks.create(_precompute_benchmarks(), name="precompute_benchmarks")


def run() -> None:
    """Démarre le serveur NiceGUI."""
    # Import des pages (les décorateurs @ui.page enregistrent les routes)
    from src.dashboard.pages import (  # noqa: F401
        clients,
        cohorts,
        optimisation,
        overview,
        pareto,
        rfm,
        seller_scoring,
        trends,
        ventes,
    )
    from src.dashboard import presentation  # noqa: F401

    app.on_startup(_schedule_benchmark_warmup)

    ui.run(
        title="Olist SQL Explorer",
        dark=True,
        reload=False,
        port=_get_dashboard_port(),
        show=_get_show_browser(),
    )
