"""Composant bloc d'insight dynamique (bordure cyan)."""

from nicegui import ui


def insight_block(html_content: str) -> None:
    """Affiche un bloc d'insight data-driven avec icone ampoule."""
    with ui.element("div").classes("insight-block"):
        ui.html(f"\U0001f4a1 {html_content}")
