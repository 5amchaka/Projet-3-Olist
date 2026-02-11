"""Layout — header, sidebar, navigation."""

from nicegui import ui

from src.dashboard.theme import BG_DARK, CUSTOM_CSS, PRIMARY

NAV_ITEMS = [
    {"label": "Vue d'ensemble", "icon": "dashboard", "path": "/"},
    {"label": "Tendances", "icon": "trending_up", "path": "/trends"},
    {"label": "Segmentation RFM", "icon": "people", "path": "/rfm"},
    {"label": "Pareto vendeurs", "icon": "leaderboard", "path": "/pareto"},
    {"label": "Cohortes", "icon": "grid_on", "path": "/cohorts"},
    {"label": "Scoring vendeurs", "icon": "star_rate", "path": "/scoring"},
    {"label": "Ventes", "icon": "shopping_bag", "path": "/ventes"},
    {"label": "Clients", "icon": "group", "path": "/clients"},
    {"label": "Optimisation", "icon": "speed", "path": "/optimisation"},
]


def layout(current_path: str = "/") -> ui.left_drawer:
    """Crée le header + sidebar et retourne le drawer."""
    ui.add_head_html(CUSTOM_CSS)

    with ui.header().classes("items-center justify-between px-4").style(
        f"background: {BG_DARK}; border-bottom: 1px solid #333"
    ):
        with ui.row().classes("items-center gap-2"):
            ui.icon("storefront").classes("text-2xl").style(f"color: {PRIMARY}")
            ui.label("Olist SQL Explorer").classes(
                "text-lg font-bold"
            ).style("color: white")
        with ui.row().classes("items-center gap-2"):
            ui.button(
                "Présentation",
                icon="slideshow",
                on_click=lambda: ui.navigate.to("/presentation"),
            ).props("flat color=white")

    # `value=True` evite la detection JS "auto" du drawer (value=None) qui peut
    # timeout dans certains environnements headless/SSH.
    drawer = ui.left_drawer(value=True, bordered=True).classes("p-2").style(
        f"background: {BG_DARK}; border-right: 1px solid #333"
    )
    with drawer:
        ui.label("Navigation").classes("text-sm font-bold mb-2").style(
            "color: #9E9E9E; text-transform: uppercase; letter-spacing: 1px"
        )
        for item in NAV_ITEMS:
            is_active = current_path == item["path"]
            btn = ui.button(
                item["label"],
                icon=item["icon"],
                on_click=lambda p=item["path"]: ui.navigate.to(p),
            ).classes("w-full justify-start").props("flat align=left")
            if is_active:
                btn.style(f"background: rgba(0,200,83,0.12); color: {PRIMARY}")
            else:
                btn.style("color: #9E9E9E")

    return drawer
