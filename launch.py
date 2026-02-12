#!/usr/bin/env python
"""Point d'entrée CLI pour le launcher automatisé du dashboard Olist."""

import os
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
    "--no-splash",
    is_flag=True,
    help="Disable WebSocket splash screen (use CLI mode)",
)
@click.option(
    "--run-tests",
    is_flag=True,
    help="Run unit tests before launching dashboard",
)
@click.option(
    "--run-all-tests",
    is_flag=True,
    help="Run all tests (unit + integration) before launching",
)
@click.option(
    "--verify-csv",
    is_flag=True,
    help="Run CSV verification (csvkit analysis) before launching",
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
    no_splash: bool,
    run_tests: bool,
    run_all_tests: bool,
    verify_csv: bool,
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

        # CLI mode (no splash)
        python launch.py --no-splash

        # Run tests before launch
        python launch.py --run-tests

        # Run all tests (including integration)
        python launch.py --run-all-tests

        # Verify CSV files before launch
        python launch.py --verify-csv
    """
    # Initialiser l'UI
    ui = UIManager(verbose=verbose, quiet=quiet)

    # Auto-détection : désactiver splash si headless ou quiet
    use_splash = not no_splash
    if use_splash:
        # Vérifier si on a un display (Linux/WSL)
        if os.name != 'nt' and not os.environ.get('DISPLAY'):
            use_splash = False
        # Mode quiet → CLI seulement
        if quiet:
            use_splash = False

    # Mode health check uniquement
    if health_check_only:
        orchestrator = OlistOrchestrator(
            ui=ui,
            force=force,
            skip_etl=skip_etl,
            skip_download=skip_download,
            port=port,
            no_browser=no_browser,
            use_splash=False,  # Toujours CLI pour health check
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
        use_splash=use_splash,
        run_tests=run_tests,
        run_all_tests=run_all_tests,
        verify_csv=verify_csv,
    )

    orchestrator.run_full_launch()


if __name__ == "__main__":
    main()
