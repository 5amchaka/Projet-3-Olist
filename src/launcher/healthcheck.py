"""Diagnostics et vérifications de santé du système."""

import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

from src.config import CSV_FILES, DATABASE_PATH, RAW_DIR

if TYPE_CHECKING:
    from src.launcher.ui import UIManager


class HealthCheckError(Exception):
    """Erreur lors d'un health check."""


class HealthChecker:
    """Vérificateur de santé du système."""

    def __init__(self, ui: "UIManager"):
        self.ui = ui

    def check_directory_structure(self) -> None:
        """Vérifier que la structure des répertoires est correcte."""
        # Les répertoires seront créés automatiquement si nécessaire
        # On vérifie juste que RAW_DIR parent existe
        if not RAW_DIR.parent.exists():
            raise HealthCheckError(f"Data directory parent does not exist: {RAW_DIR.parent}")

        self.ui.success("Directory structure OK")

    def check_python_dependencies(self) -> None:
        """Vérifier que les dépendances Python sont installées."""
        required_modules = [
            "pandas",
            "sqlalchemy",
            "nicegui",
            "click",
            "colorama",
        ]

        # Modules avec imports spéciaux
        special_imports = {
            "python-dotenv": "dotenv",
        }

        missing = []

        # Vérifier les modules standards
        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing.append(module)

        # Vérifier les imports spéciaux
        for package, import_name in special_imports.items():
            try:
                __import__(import_name)
            except ImportError:
                missing.append(package)

        # Pour Kaggle, vérifier uniquement que le package est installé
        # sans déclencher la validation des credentials
        try:
            import importlib.util
            spec = importlib.util.find_spec("kaggle")
            if spec is None:
                missing.append("kaggle")
        except (ImportError, ValueError):
            missing.append("kaggle")

        if missing:
            raise HealthCheckError(f"Missing Python dependencies: {', '.join(missing)}")

        self.ui.success("Python dependencies installed")

    def check_csv_files(self) -> dict[str, bool]:
        """Vérifier la présence des fichiers CSV.

        Returns:
            Dict indiquant pour chaque fichier s'il est présent
        """
        if not RAW_DIR.exists():
            return {name: False for name in CSV_FILES}

        status = {}
        for name, filename in CSV_FILES.items():
            csv_path = RAW_DIR / filename
            status[name] = csv_path.exists()

        present = sum(status.values())
        total = len(status)

        if present == total:
            self.ui.success(f"All CSV files present ({total}/{total})")
        elif present > 0:
            self.ui.warning(f"Some CSV files present ({present}/{total})")
        else:
            self.ui.info(f"No CSV files present ({present}/{total})")

        return status

    def check_database(self) -> dict:
        """Vérifier l'existence et la validité de la base de données.

        Returns:
            Dict avec les informations sur la DB
        """
        if not DATABASE_PATH.exists():
            self.ui.info("Database does not exist")
            return {"exists": False}

        # Vérifier la taille
        size_mb = DATABASE_PATH.stat().st_size / (1024 * 1024)

        # Vérifier le schéma
        try:
            conn = sqlite3.connect(DATABASE_PATH)
            cursor = conn.cursor()

            # Lister les tables (exclure les tables système SQLite)
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
            tables = [row[0] for row in cursor.fetchall()]

            # Compter les lignes dans chaque table
            row_counts = {}
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                row_counts[table] = cursor.fetchone()[0]

            conn.close()

            expected_tables = {
                "dim_dates",
                "dim_geolocation",
                "dim_customers",
                "dim_sellers",
                "dim_products",
                "fact_orders",
            }

            valid_schema = set(tables) == expected_tables

            if valid_schema:
                self.ui.success(f"Database exists ({size_mb:.1f} MB)")
                self.ui.success(f"Database schema valid ({len(tables)} tables)")
            else:
                self.ui.warning(f"Database schema incomplete or invalid")

            return {
                "exists": True,
                "size_mb": size_mb,
                "tables": tables,
                "row_counts": row_counts,
                "valid_schema": valid_schema,
            }

        except sqlite3.Error as e:
            self.ui.error(f"Database error: {e}")
            return {"exists": True, "error": str(e)}

    def validate_data_integrity(self) -> None:
        """Valider l'intégrité des données dans la base."""
        db_info = self.check_database()

        if not db_info.get("exists"):
            raise HealthCheckError("Database does not exist")

        if not db_info.get("valid_schema"):
            raise HealthCheckError("Database schema is invalid")

        # Vérifier que les tables ont des données
        row_counts = db_info.get("row_counts", {})
        empty_tables = [table for table, count in row_counts.items() if count == 0]

        if empty_tables:
            raise HealthCheckError(f"Empty tables found: {', '.join(empty_tables)}")

        self.ui.success("Data integrity validated")

    def run_full_diagnostic(self) -> dict:
        """Exécuter un diagnostic complet et retourner un rapport.

        Returns:
            Dict avec le rapport de diagnostic
        """
        report = {
            "directory_structure": False,
            "python_dependencies": False,
            "csv_files": {},
            "database": {},
        }

        try:
            self.check_directory_structure()
            report["directory_structure"] = True
        except HealthCheckError as e:
            self.ui.error(f"Directory check failed: {e}")

        try:
            self.check_python_dependencies()
            report["python_dependencies"] = True
        except HealthCheckError as e:
            self.ui.error(f"Dependencies check failed: {e}")

        report["csv_files"] = self.check_csv_files()
        report["database"] = self.check_database()

        return report
