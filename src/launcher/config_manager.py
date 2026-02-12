"""Gestion de la configuration du launcher."""

import os
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv

if TYPE_CHECKING:
    from src.launcher.ui import UIManager


class ConfigurationError(Exception):
    """Erreur de configuration."""


class ConfigManager:
    """Gestionnaire de configuration pour le launcher."""

    def __init__(self, ui: "UIManager", project_root: Path):
        self.ui = ui
        self.project_root = project_root
        self.env_file = project_root / ".env"

    def load_env(self) -> None:
        """Charger le fichier .env s'il existe."""
        if self.env_file.exists():
            load_dotenv(self.env_file)
            self.ui.success(".env file loaded")
        else:
            self.ui.info("No .env file (optional)")

    def validate_permissions(self) -> None:
        """Vérifier les permissions d'écriture dans les répertoires nécessaires."""
        if not os.access(self.project_root, os.W_OK):
            raise ConfigurationError(f"No write permission in {self.project_root}")

        self.ui.success("Directory permissions OK")

    def get_dashboard_config(self) -> dict:
        """Récupérer la configuration du dashboard depuis .env."""
        return {
            "port": int(os.getenv("DASHBOARD_PORT", "8080")),
            "show_browser": os.getenv("DASHBOARD_SHOW_BROWSER", "1") == "1",
        }
