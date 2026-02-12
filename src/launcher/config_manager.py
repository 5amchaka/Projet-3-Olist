"""Gestion de la configuration et validation des credentials Kaggle."""

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
        self.env_example = project_root / ".env.example"

    def ensure_env_file(self) -> None:
        """S'assurer que le fichier .env existe et est valide."""
        if self.env_file.exists():
            self.ui.success(".env file found")
            load_dotenv(self.env_file)
            return

        # Fichier .env absent
        self.ui.warning(".env file not found")

        # Demander confirmation interactive
        response = input("Create .env file now? [Y/n]: ").strip().lower()
        if response in ["n", "no"]:
            raise ConfigurationError(".env file is required to proceed")

        self._create_env_interactively()
        self.ui.success(".env created")

    def _create_env_interactively(self) -> None:
        """Créer le fichier .env de manière interactive."""
        print("\nKaggle API Credentials:")
        print("Get them from: https://www.kaggle.com/settings/account\n")

        username = input("KAGGLE_USERNAME: ").strip()
        api_key = input("KAGGLE_KEY: ").strip()

        if not username or not api_key:
            raise ConfigurationError("Kaggle credentials cannot be empty")

        # Créer le fichier .env
        env_content = f"""# Kaggle API credentials (required)
KAGGLE_USERNAME={username}
KAGGLE_KEY={api_key}

# Dashboard configuration (optional)
DASHBOARD_PORT=8080
DASHBOARD_SHOW_BROWSER=1
"""
        self.env_file.write_text(env_content)

        # Charger immédiatement
        load_dotenv(self.env_file)

    def validate_kaggle_credentials(self) -> None:
        """Valider que les credentials Kaggle sont présents et valides."""
        username = os.getenv("KAGGLE_USERNAME")
        api_key = os.getenv("KAGGLE_KEY")

        if not username or not api_key:
            raise ConfigurationError(
                "KAGGLE_USERNAME and KAGGLE_KEY must be set in .env file"
            )

        self.ui.success(f"Kaggle credentials valid (user: {username})")

    def validate_permissions(self) -> None:
        """Vérifier les permissions d'écriture dans les répertoires nécessaires."""
        # Vérifier que PROJECT_ROOT est accessible en écriture
        if not os.access(self.project_root, os.W_OK):
            raise ConfigurationError(f"No write permission in {self.project_root}")

        self.ui.success("Directory permissions OK")

    def get_dashboard_config(self) -> dict:
        """Récupérer la configuration du dashboard depuis .env."""
        return {
            "port": int(os.getenv("DASHBOARD_PORT", "8080")),
            "show_browser": os.getenv("DASHBOARD_SHOW_BROWSER", "1") == "1",
        }
