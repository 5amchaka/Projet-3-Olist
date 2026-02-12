"""
Types d'événements WebSocket et sanitization des messages.

Ce module garantit qu'aucune donnée sensible (clés API, secrets, chemins privés)
ne soit envoyée au client web.
"""

import re
from typing import Any, Dict, List, Tuple
from enum import Enum


class EventType(str, Enum):
    """Types d'événements envoyés via WebSocket."""

    CONFIG = "config"
    PHASE_START = "phase_start"
    PHASE_COMPLETE = "phase_complete"
    LOG = "log"
    DASHBOARD_READY = "dashboard_ready"
    ERROR = "error"
    CONNECTED = "connected"


# Patterns de redaction (pattern, replacement)
REDACT_PATTERNS: List[Tuple[str, str]] = [
    # Clés Kaggle
    (r'KAGGLE_KEY\s*=\s*\S+', 'KAGGLE_KEY=<redacted>'),
    (r'KAGGLE_USERNAME\s*=\s*\S+', 'KAGGLE_USERNAME=<redacted>'),

    # Clés API génériques
    (r'api[_-]?key[\s=:]+[\w\-]{10,}', 'api_key=<redacted>'),
    (r'secret[\s=:]+[\w\-]{10,}', 'secret=<redacted>'),
    (r'token[\s=:]+[\w\-]{10,}', 'token=<redacted>'),
    (r'password[\s=:]+\S+', 'password=<redacted>'),

    # Chemins home (remplacement par ~/)
    (r'/home/[^/\s]+/', '~/'),

    # Credentials dans URLs
    (r'://[^:]+:[^@]+@', '://<redacted>@'),
]


# Clés sensibles à supprimer des dictionnaires
SENSITIVE_KEYS = {
    'KAGGLE_KEY',
    'KAGGLE_USERNAME',
    'api_key',
    'apikey',
    'secret',
    'token',
    'password',
    'credentials',
    'auth',
}


def sanitize_message(event: Dict[str, Any]) -> Dict[str, Any]:
    """
    Nettoie un événement avant envoi WebSocket.

    Supprime/redacte :
    - Clés API et secrets
    - Chemins privés (/home/user/)
    - Variables d'environnement sensibles
    - Stack traces détaillées (garde seulement le message)

    Args:
        event: Événement brut (dict avec type, data, timestamp)

    Returns:
        Événement sanitizé (safe pour le client web)
    """
    # Deep copy pour ne pas modifier l'original
    sanitized = _deep_sanitize(event)

    return sanitized


def _deep_sanitize(obj: Any) -> Any:
    """Sanitize récursif pour structures imbriquées."""

    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            # Supprimer les clés sensibles
            if key.lower() in SENSITIVE_KEYS:
                result[key] = "<redacted>"
            else:
                result[key] = _deep_sanitize(value)
        return result

    elif isinstance(obj, (list, tuple)):
        return type(obj)(_deep_sanitize(item) for item in obj)

    elif isinstance(obj, str):
        return _redact_string(obj)

    else:
        return obj


def _redact_string(text: str) -> str:
    """Applique tous les patterns de redaction sur une chaîne."""

    result = text

    # Appliquer tous les patterns
    for pattern, replacement in REDACT_PATTERNS:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    # Tronquer les stack traces longues (garder 3 premières lignes)
    if '\n' in result and 'Traceback' in result:
        lines = result.split('\n')
        if len(lines) > 5:
            result = '\n'.join(lines[:3]) + '\n... (stack trace truncated)'

    return result


def create_event(
    event_type: EventType,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Crée un événement WebSocket structuré.

    Args:
        event_type: Type d'événement
        data: Données de l'événement

    Returns:
        Événement formaté pour envoi WebSocket
    """
    import time

    return {
        "type": event_type.value,
        "data": data,
        "timestamp": int(time.time()),
    }
