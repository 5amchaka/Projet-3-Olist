"""
Module splash screen WebSocket pour le launcher Olist.

Fournit une interface web interactive affichant les phases du pipeline ETL
en temps réel via WebSocket, avec une animation Matrix en arrière-plan.
"""

from .server import SplashServer
from .events import sanitize_message, EventType

__all__ = [
    "SplashServer",
    "sanitize_message",
    "EventType",
]
