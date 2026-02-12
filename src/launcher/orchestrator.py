"""Orchestrateur principal du launcher automatisé."""

import os
import subprocess
import sys
from pathlib import Path

from src.config import CSV_FILES, DATABASE_PATH, PROJECT_ROOT, RAW_DIR
from src.launcher.config_manager import ConfigManager
from src.launcher.downloader import KaggleDownloader
from src.launcher.healthcheck import HealthChecker
from src.launcher.logger_adapter import restore_default_logging, setup_logging_bridge
from src.launcher.ui import UIManager


class LauncherError(Exception):
    """Erreur générale du launcher."""


class OlistOrchestrator:
    """Orchestrateur pour le lancement automatisé du dashboard Olist."""

    def __init__(
        self,
        ui: UIManager,
        force: bool = False,
        skip_etl: bool = False,
        skip_download: bool = False,
        port: int = 8080,
        no_browser: bool = False,
    ):
        self.ui = ui
        self.force = force
        self.skip_etl = skip_etl
        self.skip_download = skip_download
        self.port = port
        self.no_browser = no_browser

        # Initialiser les gestionnaires
        self.config_manager = ConfigManager(ui, PROJECT_ROOT)
        self.health_checker = HealthChecker(ui)
        self.downloader = KaggleDownloader(ui)

    def run_full_launch(self) -> None:
        """Exécuter le lancement complet du dashboard."""
        try:
            # Animation Matrix
            self.ui.show_matrix_intro()
            self.ui.show_banner()

            # Phase 1: Configuration & Validation
            self._phase_configuration()

            # Phase 2: Pre-flight Health Check
            self._phase_preflight_check()

            # Phase 3: Download CSV (si nécessaire)
            download_executed = False
            if self._should_run_download():
                self._phase_download_csv()
                download_executed = True
            else:
                self.ui.skip("CSV download (files already present)")

            # Phase 4: ETL Pipeline (si nécessaire)
            etl_executed = False
            if self._should_run_etl():
                self._phase_etl_pipeline()
                etl_executed = True
            else:
                self.ui.skip("ETL pipeline (database already exists)")

            # Phase 5: Post-ETL Validation (seulement si ETL exécuté)
            if etl_executed:
                self._phase_post_etl_validation()
            else:
                # Validation légère si ETL skippé
                self._phase_basic_validation()

            # Phase 6: Launch Dashboard
            self._phase_launch_dashboard()

        except KeyboardInterrupt:
            self.ui.warning("\nLauncher interrupted by user")
            sys.exit(1)
        except Exception as e:
            self.ui.error(f"Launcher failed: {e}")
            raise LauncherError(str(e)) from e

    def run_health_check_only(self) -> None:
        """Exécuter uniquement le diagnostic de santé."""
        self.ui.show_banner()

        with self.ui.phase_context("System Diagnostic"):
            report = self.health_checker.run_full_diagnostic()

            # Afficher le rapport
            print("\n=== DIAGNOSTIC REPORT ===\n")
            print(f"Directory Structure: {'✓' if report['directory_structure'] else '✗'}")
            print(
                f"Python Dependencies: {'✓' if report['python_dependencies'] else '✗'}"
            )

            csv_present = sum(report["csv_files"].values())
            csv_total = len(report["csv_files"])
            print(f"CSV Files: {csv_present}/{csv_total}")

            db_info = report["database"]
            if db_info.get("exists"):
                print(f"Database: ✓ ({db_info.get('size_mb', 0):.1f} MB)")
                if db_info.get("valid_schema"):
                    print(f"  Schema: ✓ Valid")
                    print(f"  Row counts:")
                    for table, count in sorted(db_info.get("row_counts", {}).items()):
                        print(f"    - {table}: {count:,}")
            else:
                print("Database: ✗ Not found")

    def _phase_configuration(self) -> None:
        """Phase 1: Configuration et validation."""
        with self.ui.phase_context("Configuration & Validation"):
            self.config_manager.ensure_env_file()
            self.config_manager.validate_kaggle_credentials()
            self.config_manager.validate_permissions()

    def _phase_preflight_check(self) -> None:
        """Phase 2: Vérifications préliminaires."""
        with self.ui.phase_context("Pre-flight Health Check"):
            self.health_checker.check_directory_structure()
            self.health_checker.check_python_dependencies()

    def _phase_download_csv(self) -> None:
        """Phase 3: Téléchargement des CSV."""
        with self.ui.phase_context("Downloading CSV Files"):
            self.downloader.download_all()

    def _phase_etl_pipeline(self) -> None:
        """Phase 4: Exécution du pipeline ETL."""
        with self.ui.phase_context("ETL Pipeline"):
            # Configurer le bridge de logging
            setup_logging_bridge(self.ui)

            # Importer et exécuter le pipeline
            from src.etl.pipeline import run_full_pipeline

            run_full_pipeline()

            # Restaurer le logging par défaut
            restore_default_logging()

    def _phase_post_etl_validation(self) -> None:
        """Phase 5: Validation post-ETL (stricte)."""
        with self.ui.phase_context("Post-ETL Validation"):
            self.health_checker.validate_data_integrity()

    def _phase_basic_validation(self) -> None:
        """Phase 5: Validation basique (si ETL skippé)."""
        with self.ui.phase_context("Database Validation"):
            db_info = self.health_checker.check_database()
            if not db_info.get("exists"):
                raise LauncherError(
                    "Database does not exist. Run with --force to rebuild."
                )

    def _phase_launch_dashboard(self) -> None:
        """Phase 6: Lancement du dashboard."""
        with self.ui.phase_context("Launching Dashboard"):
            # Configurer les variables d'environnement
            os.environ["DASHBOARD_PORT"] = str(self.port)
            if self.no_browser:
                os.environ["DASHBOARD_SHOW_BROWSER"] = "0"

            url = f"http://localhost:{self.port}"
            self.ui.show_success_box(url)

            # Lancer le dashboard
            try:
                subprocess.run(
                    [sys.executable, "-m", "src.dashboard"],
                    check=True,
                )
            except subprocess.CalledProcessError as e:
                raise LauncherError(f"Dashboard launch failed: {e}") from e
            except KeyboardInterrupt:
                self.ui.info("\nDashboard stopped by user")

    def _should_run_download(self) -> bool:
        """Déterminer si le téléchargement CSV est nécessaire."""
        if self.skip_download:
            return False

        return self.downloader.should_download(force=self.force)

    def _should_run_etl(self) -> bool:
        """Déterminer si l'exécution de l'ETL est nécessaire."""
        if self.force:
            return True

        if self.skip_etl and DATABASE_PATH.exists():
            return False

        # Auto-détection : exécuter si DB absente
        if not DATABASE_PATH.exists():
            return True

        # Exécuter si les CSV sont plus récents que la DB
        if not RAW_DIR.exists():
            return False

        db_mtime = DATABASE_PATH.stat().st_mtime

        try:
            csv_mtimes = [
                (RAW_DIR / filename).stat().st_mtime
                for filename in CSV_FILES.values()
                if (RAW_DIR / filename).exists()
            ]

            if not csv_mtimes:
                return True

            latest_csv_mtime = max(csv_mtimes)
            return latest_csv_mtime > db_mtime

        except (FileNotFoundError, OSError):
            # En cas d'erreur, exécuter l'ETL par sécurité
            return True
