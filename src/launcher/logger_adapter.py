"""Bridge entre le système de logging Python et l'UI du launcher."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.launcher.ui import UIManager


class UILogHandler(logging.Handler):
    """Handler de logging qui redirige vers l'UIManager."""

    def __init__(self, ui: "UIManager"):
        super().__init__()
        self.ui = ui

    def emit(self, record: logging.LogRecord) -> None:
        """Émettre un log vers l'UI."""
        try:
            msg = self.format(record)
            self.ui.display_live_log(record.levelname, msg)
        except Exception:
            self.handleError(record)


def setup_logging_bridge(ui: "UIManager") -> None:
    """Configurer le bridge logging → UI pour capturer les logs du pipeline ETL.

    Args:
        ui: Instance de UIManager pour afficher les logs
    """
    # Obtenir le root logger
    root_logger = logging.getLogger()

    # Nettoyer les handlers existants
    root_logger.handlers.clear()

    # Ajouter le handler UI
    ui_handler = UILogHandler(ui)
    ui_handler.setLevel(logging.INFO)

    # Format simple sans timestamps (l'UI gère déjà l'affichage)
    formatter = logging.Formatter("%(name)s | %(message)s")
    ui_handler.setFormatter(formatter)

    root_logger.addHandler(ui_handler)
    root_logger.setLevel(logging.INFO)


def restore_default_logging() -> None:
    """Restaurer la configuration de logging par défaut."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s | %(name)s | %(message)s",
        force=True,
    )
