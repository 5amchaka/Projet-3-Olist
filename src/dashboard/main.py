"""Point d'entrée NiceGUI — routage des pages."""

import asyncio

from nicegui import app, ui


async def _precompute_benchmarks() -> None:
    """Lance les benchmarks en arriere-plan pour remplir le cache."""
    from src.dashboard.pages.optimisation import COMPARISONS, ITERATIONS, WARMUP
    from src.dashboard.components.benchmark import run_all_benchmarks

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(
        None, lambda: run_all_benchmarks(COMPARISONS, iterations=ITERATIONS, warmup=WARMUP)
    )


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

    app.on_startup(_precompute_benchmarks)

    ui.run(
        title="Olist SQL Explorer",
        dark=True,
        reload=False,
        port=8080,
    )
