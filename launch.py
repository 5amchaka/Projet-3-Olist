#!/usr/bin/env python
"""Point d'entrée CLI pour le launcher automatisé du dashboard Olist."""

import click

from src.launcher.orchestrator import OlistOrchestrator
from src.launcher.ui import UIManager


@click.command()
@click.option(
    "--force",
    is_flag=True,
    help="Force re-download CSV and rebuild database",
)
@click.option(
    "--skip-etl",
    is_flag=True,
    help="Skip ETL pipeline if database exists",
)
@click.option(
    "--skip-download",
    is_flag=True,
    help="Skip CSV download if files exist",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
@click.option(
    "--quiet",
    "-q",
    is_flag=True,
    help="Minimal output (errors only)",
)
@click.option(
    "--port",
    type=int,
    default=8080,
    help="Dashboard port (default: 8080)",
)
@click.option(
    "--no-browser",
    is_flag=True,
    help="Do not open browser automatically",
)
@click.option(
    "--health-check-only",
    is_flag=True,
    help="Run system diagnostic only (no launch)",
)
def main(
    force: bool,
    skip_etl: bool,
    skip_download: bool,
    verbose: bool,
    quiet: bool,
    port: int,
    no_browser: bool,
    health_check_only: bool,
) -> None:
    """OLIST Dashboard Launcher - Automated setup and launch.

    This launcher automatically:
    - Validates configuration and Kaggle credentials
    - Downloads CSV files if needed
    - Runs ETL pipeline if needed
    - Launches the dashboard

    Examples:
        # Standard launch (smart detection)
        python launch.py

        # Force complete rebuild
        python launch.py --force

        # Quick launch (skip everything if possible)
        python launch.py --skip-download --skip-etl

        # Health check only
        python launch.py --health-check-only

        # Custom port
        python launch.py --port 8888
    """
    # Initialiser l'UI
    ui = UIManager(verbose=verbose, quiet=quiet)

    # Mode health check uniquement
    if health_check_only:
        orchestrator = OlistOrchestrator(
            ui=ui,
            force=force,
            skip_etl=skip_etl,
            skip_download=skip_download,
            port=port,
            no_browser=no_browser,
        )
        orchestrator.run_health_check_only()
        return

    # Lancement complet
    orchestrator = OlistOrchestrator(
        ui=ui,
        force=force,
        skip_etl=skip_etl,
        skip_download=skip_download,
        port=port,
        no_browser=no_browser,
    )

    orchestrator.run_full_launch()


if __name__ == "__main__":
    main()
