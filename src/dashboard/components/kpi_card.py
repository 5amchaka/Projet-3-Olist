"""Composant carte KPI stylisée."""

from nicegui import ui

from src.dashboard.theme import PRIMARY


def kpi_card(
    title: str,
    value: str,
    subtitle: str = "",
    icon: str = "analytics",
    color: str = PRIMARY,
) -> None:
    """Affiche une carte KPI avec icône, valeur et sous-titre."""
    with ui.card().classes("kpi-card p-4").style(
        f"border-left-color: {color}; min-width: 200px; flex: 1 1 0%"
    ):
        with ui.row().classes("items-center gap-3 no-wrap"):
            ui.icon(icon).classes("text-3xl").style(f"color: {color}")
            with ui.column().classes("gap-0"):
                ui.label(title).classes("kpi-label")
                ui.label(value).classes("kpi-value").style(f"color: {color}")
                if subtitle:
                    ui.label(subtitle).style("color: #9E9E9E; font-size: 0.8rem")
