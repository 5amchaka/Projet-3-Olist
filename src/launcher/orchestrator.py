"""Orchestrateur principal du launcher automatisé."""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

from src.config import CSV_FILES, DATABASE_PATH, PROJECT_ROOT, RAW_DIR
from src.launcher.browser_opener import open_browser
from src.launcher.config_manager import ConfigManager
from src.launcher.downloader import KaggleDownloader
from src.launcher.healthcheck import HealthChecker
from src.launcher.logger_adapter import restore_default_logging, setup_logging_bridge
from src.launcher.ui import UIManager, WebSocketUIAdapter


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
        use_splash: bool = True,
        splash_theme: str = "matrix",
        run_tests: bool = False,
        run_all_tests: bool = False,
        verify_csv: bool = False,
    ):
        self.ui = ui
        self.force = force
        self.skip_etl = skip_etl
        self.skip_download = skip_download
        self.port = port
        self.no_browser = no_browser
        self.use_splash = use_splash
        self.splash_theme = splash_theme
        self.run_tests = run_tests
        self.run_all_tests = run_all_tests
        self.verify_csv = verify_csv

        # Splash server (initialisé plus tard si nécessaire)
        self.splash_server = None

        # Initialiser les gestionnaires
        self.config_manager = ConfigManager(ui, PROJECT_ROOT)
        self.health_checker = HealthChecker(ui)
        self.downloader = KaggleDownloader(ui)

    def run_full_launch(self) -> None:
        """Exécuter le lancement complet du dashboard."""
        if self.use_splash:
            # Mode splash WebSocket (async)
            asyncio.run(self.run_full_launch_async())
        else:
            # Mode CLI classique (sync)
            self._run_full_launch_sync()

    async def run_full_launch_async(self) -> None:
        """Version async du lancement avec splash WebSocket."""
        try:
            # Démarrer le splash server
            from src.launcher.splash.server import SplashServer
            from src.launcher.splash.events import EventType

            self.splash_server = SplashServer(port=8079, theme=self.splash_theme)
            await self.splash_server.start()

            # Remplacer l'UI par le WebSocket adapter IMMÉDIATEMENT
            # (avant d'ouvrir le navigateur pour capturer toutes les phases)
            original_ui = self.ui
            loop = asyncio.get_event_loop()
            self.ui = WebSocketUIAdapter(
                self.splash_server,
                loop,
                original_ui.verbose,
                original_ui.quiet
            )

            # Réinitialiser les gestionnaires avec la nouvelle UI
            self.config_manager = ConfigManager(self.ui, PROJECT_ROOT)
            self.health_checker = HealthChecker(self.ui)
            self.downloader = KaggleDownloader(self.ui)

            # Calculer et envoyer le nombre total de phases
            total_phases = self._calculate_total_phases()
            await self.splash_server.broadcast_event(
                EventType.CONFIG,
                {"total_phases": total_phases}
            )

            # Afficher l'URL du splash (après avoir configuré l'UI)
            splash_url = "http://localhost:8079"
            print(f"\n🚀 Splash screen: {splash_url}")
            print("   Opening browser...")

            # Ouvrir le navigateur (avec support WSL)
            await asyncio.sleep(0.3)  # Petit délai pour que le serveur soit prêt

            success = await asyncio.to_thread(open_browser, splash_url, original_ui.verbose)

            if success:
                print("   ✓ Browser opened successfully!\n")
            else:
                # Fallback si échec
                print("   ⚠ Could not open browser automatically")
                print(f"   Please open manually: {splash_url}\n")

            # Attendre un peu que le client se connecte
            await asyncio.sleep(0.5)

            # Exécuter toutes les phases (mode sync dans le thread async)
            await asyncio.to_thread(self._run_phases_sync)

            # Lancer le dashboard de façon non-bloquante
            await self._phase_launch_dashboard_async()

            # Attendre un peu pour que le redirect se fasse
            await asyncio.sleep(3)

        except KeyboardInterrupt:
            self.ui.warning("\nLauncher interrupted by user")
            sys.exit(1)
        except Exception as e:
            self.ui.error(f"Launcher failed: {e}")
            # Broadcast error event
            if self.splash_server:
                from src.launcher.splash.events import EventType
                await self.splash_server.broadcast_event(
                    EventType.ERROR,
                    {"message": str(e), "fatal": True}
                )
                await asyncio.sleep(5)  # Laisser l'erreur visible
            raise LauncherError(str(e)) from e
        finally:
            # Fermer le splash server
            if self.splash_server:
                await self.splash_server.shutdown()

    def _run_full_launch_sync(self) -> None:
        """Version synchrone du lancement (mode CLI classique)."""
        try:
            # Animation Matrix
            self.ui.show_matrix_intro()
            self.ui.show_banner()

            # Exécuter les phases
            self._run_phases_sync()

            # Phase 6: Launch Dashboard (bloquant en mode CLI)
            self._phase_launch_dashboard()

        except KeyboardInterrupt:
            self.ui.warning("\nLauncher interrupted by user")
            sys.exit(1)
        except Exception as e:
            self.ui.error(f"Launcher failed: {e}")
            raise LauncherError(str(e)) from e

    def _run_phases_sync(self) -> None:
        """Exécute les phases 1-5 (communes aux deux modes)."""
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

        # Phases optionnelles de test/vérification
        if self.verify_csv:
            self._phase_verify_csv()

        if self.run_all_tests:
            self._phase_run_all_tests()
        elif self.run_tests:
            self._phase_run_tests()

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
            self.config_manager.load_env()
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
        """Phase 6: Lancement du dashboard (mode CLI bloquant)."""
        with self.ui.phase_context("Launching Dashboard"):
            # Configurer les variables d'environnement
            os.environ["DASHBOARD_PORT"] = str(self.port)
            if self.no_browser:
                os.environ["DASHBOARD_SHOW_BROWSER"] = "0"

            url = f"http://localhost:{self.port}/presentation"
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

    async def _phase_launch_dashboard_async(self) -> None:
        """Phase 6: Lancement du dashboard (mode splash non-bloquant)."""
        with self.ui.phase_context("Launching Dashboard"):
            # Configurer les variables d'environnement
            os.environ["DASHBOARD_PORT"] = str(self.port)
            os.environ["DASHBOARD_SHOW_BROWSER"] = "0"  # Pas de second browser

            # Lancer le dashboard en arrière-plan (non-bloquant)
            process = subprocess.Popen(
                [sys.executable, "-m", "src.dashboard"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            self.ui.info(f"Dashboard process started (PID: {process.pid})")

            # Attendre que le dashboard soit prêt
            from src.launcher.splash.health import wait_for_dashboard_ready
            ready = await wait_for_dashboard_ready(self.port, timeout=30)

            if ready:
                url = f"http://localhost:{self.port}/presentation"
                self.ui.info(f"Dashboard is ready at {url}")

                # Afficher la success box (qui déclenche le redirect)
                self.ui.show_success_box(url)
            else:
                raise LauncherError("Dashboard failed to start within 30 seconds")

    def _run_command_with_live_output(self, cmd: list, cwd=None) -> int:
        """
        Exécute une commande et stream la sortie vers le UI en temps réel.

        Returns:
            Le code de retour de la commande
        """
        import re

        # Regex pour supprimer les codes ANSI
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=cwd or PROJECT_ROOT,
        )

        # Lire et afficher ligne par ligne
        for line in process.stdout:
            line = line.rstrip()
            if line:
                # Supprimer les codes ANSI
                clean_line = ansi_escape.sub('', line)

                # Ignorer les lignes vides ou de séparation
                if not clean_line or clean_line.strip() in ['', '═'*60]:
                    continue

                # Déterminer le niveau
                if "FAILED" in clean_line or "ERROR" in clean_line or "error:" in clean_line:
                    self.ui.display_live_log("ERROR", clean_line)
                elif "PASSED" in clean_line or "passed" in clean_line.lower() or "[OK]" in clean_line:
                    self.ui.display_live_log("SUCCESS", clean_line)
                elif "WARNING" in clean_line or "warning:" in clean_line.lower():
                    self.ui.display_live_log("WARNING", clean_line)
                else:
                    self.ui.display_live_log("INFO", clean_line)

        return_code = process.wait()
        return return_code

    def _phase_verify_csv(self) -> None:
        """Phase optionnelle: Vérification CSV via csvkit."""
        with self.ui.phase_context("CSV Verification (csvkit)"):
            self.ui.info("Running CSV analysis with csvkit...")

            try:
                return_code = self._run_command_with_live_output(
                    ["bash", "scripts/verify_csv_analysis.sh"]
                )

                if return_code == 0:
                    self.ui.success("CSV verification completed successfully")
                else:
                    raise subprocess.CalledProcessError(return_code, "verify_csv_analysis.sh")

            except subprocess.CalledProcessError as e:
                self.ui.error(f"CSV verification failed (exit code {e.returncode})")
                raise LauncherError(f"CSV verification failed") from e
            except FileNotFoundError:
                self.ui.warning("verify_csv_analysis.sh not found, skipping")

    def _phase_run_tests(self) -> None:
        """Phase optionnelle: Tests unitaires (sans intégration)."""
        with self.ui.phase_context("Running Unit Tests"):
            self.ui.info("Running unit tests (excluding integration tests)...")

            try:
                return_code = self._run_command_with_live_output([
                    sys.executable, "-m", "pytest",
                    "tests/", "-v",
                    "-m", "not integration",
                    "--tb=short",  # Traceback court
                ])

                if return_code == 0:
                    self.ui.success("All unit tests passed")
                else:
                    raise subprocess.CalledProcessError(return_code, "pytest")

            except subprocess.CalledProcessError as e:
                self.ui.error(f"Some tests failed (exit code {e.returncode})")
                raise LauncherError("Unit tests failed") from e

    def _phase_run_all_tests(self) -> None:
        """Phase optionnelle: Tous les tests (unitaires + intégration)."""
        with self.ui.phase_context("Running All Tests"):
            self.ui.info("Running all tests (unit + integration)...")

            try:
                return_code = self._run_command_with_live_output([
                    sys.executable, "-m", "pytest",
                    "tests/", "-v",
                    "--tb=short",  # Traceback court
                ])

                if return_code == 0:
                    self.ui.success("All tests passed")
                else:
                    raise subprocess.CalledProcessError(return_code, "pytest")

            except subprocess.CalledProcessError as e:
                self.ui.error(f"Some tests failed (exit code {e.returncode})")
                raise LauncherError("Tests failed") from e

    def _calculate_total_phases(self) -> int:
        """Calcule le nombre total de phases qui seront exécutées."""
        # Phases de base : toujours 6
        # 1. Configuration
        # 2. Pre-flight check
        # 3. Download (ou skip)
        # 4. ETL (ou skip)
        # 5. Validation
        # 6. Dashboard launch
        total = 6

        # Phases optionnelles
        if self.verify_csv:
            total += 1

        if self.run_all_tests or self.run_tests:
            total += 1

        return total

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
