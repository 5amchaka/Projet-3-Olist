"""Mode Présentation — stepper séquentiel à travers les analyses."""

from nicegui import ui

from src.dashboard.theme import BG_DARK, CUSTOM_CSS, PRIMARY
from src.dashboard.pages import clients, cohorts, optimisation, rfm, ventes


@ui.page("/presentation")
def page() -> None:
    """Page présentation : un stepper parcourt les 6 étapes."""
    ui.add_head_html(CUSTOM_CSS)

    # ── Header simplifié ───────────────────────────────────────────────────
    with ui.header().classes("items-center justify-between px-4").style(
        f"background: {BG_DARK}; border-bottom: 1px solid #333"
    ):
        with ui.row().classes("items-center gap-2"):
            ui.icon("storefront").classes("text-2xl").style(f"color: {PRIMARY}")
            ui.label("Olist SQL Explorer").classes(
                "text-lg font-bold"
            ).style("color: white")
        ui.button(
            "Mode Explorer",
            icon="explore",
            on_click=lambda: ui.navigate.to("/"),
        ).props("flat color=white")

    # ── Stepper ────────────────────────────────────────────────────────────
    with ui.stepper().classes("w-full").props("vertical animated") as stepper:

        # -- Étape 1 : Introduction -------------------------------------------
        with ui.step("Introduction", icon="home"):
            with ui.element("div").style("max-width: 800px"):
                ui.label("Olist SQL Explorer").classes(
                    "text-2xl font-bold mb-2"
                ).style(f"color: {PRIMARY}")
                ui.markdown(
                    "Bienvenue dans l'exploration du **Data Warehouse Olist** "
                    "(e-commerce brésilien).\n\n"
                    "Ce dashboard est construit sur un **schéma en étoile** "
                    "SQLite comprenant :\n\n"
                    "- **`fact_orders`** : ~112 000 lignes (grain = article de commande)\n"
                    "- **`dim_customers`** / **`dim_sellers`** / **`dim_products`** / "
                    "**`dim_dates`** / **`dim_geolocation`**\n\n"
                    "Le parcours suit **3 axes d'analyse** demandés par l'exercice, "
                    "puis démontre les **techniques d'optimisation SQL** appliquées :\n\n"
                    "1. **Ventes** — CA, évolution YoY, Top 10 produits\n"
                    "2. **Clients** — Nouveaux vs récurrents, panier moyen, segmentation RFM\n"
                    "3. **Cohortes** — Rétention, LTV par cohorte\n"
                    "4. **Optimisation SQL** — Comparaisons avant/après avec EXPLAIN\n\n"
                    "Cliquez sur **Suivant** pour commencer."
                )
            with ui.stepper_navigation():
                ui.button("Suivant", on_click=stepper.next).props("color=green")

        # -- Étape 2 : Ventes -------------------------------------------------
        with ui.step("Ventes", icon="shopping_bag"):
            with ui.element("div").classes("narrative-block"):
                ui.html(
                    "<b>Axe 1 — Ventes :</b> quelles catégories de produits "
                    "génèrent le plus de CA ? Comment le chiffre d'affaires "
                    "évolue-t-il d'une année à l'autre ? Quel est le panier moyen ? "
                    "Les requêtes utilisent <b>CTEs</b>, <b>LAG() OVER</b>, "
                    "et <b>ROW_NUMBER()</b>."
                )
            ventes.content()
            with ui.stepper_navigation():
                ui.button("Précédent", on_click=stepper.previous).props("flat")
                ui.button("Suivant", on_click=stepper.next).props("color=green")

        # -- Étape 3 : Clients ------------------------------------------------
        with ui.step("Clients", icon="group"):
            with ui.element("div").classes("narrative-block"):
                ui.html(
                    "<b>Axe 2 — Clients :</b> combien de clients sont nouveaux "
                    "vs récurrents chaque mois ? Quelle est la <b>Lifetime Value</b> "
                    "par cohorte ? Et comment segmenter la base client avec la "
                    "méthode <b>RFM</b> (Récence, Fréquence, Montant) ? "
                    "Les requêtes combinent <b>NTILE</b>, <b>CASE WHEN</b>, "
                    "et des <b>CTEs multi-niveaux</b>."
                )
            clients.content()
            rfm.content()
            with ui.stepper_navigation():
                ui.button("Précédent", on_click=stepper.previous).props("flat")
                ui.button("Suivant", on_click=stepper.next).props("color=green")

        # -- Étape 4 : Cohortes -----------------------------------------------
        with ui.step("Cohortes", icon="grid_on"):
            with ui.element("div").classes("narrative-block"):
                ui.html(
                    "<b>Axe 3 — Cohortes :</b> mesurer la rétention client — "
                    "combien de clients reviennent 1, 2, 3 mois après leur premier "
                    "achat ? Les <b>CTEs</b> et le calcul de <b>delta mois</b> "
                    "à partir d'entiers AAAAMM structurent cette analyse. "
                    "La heatmap montre le taux de rétention par cohorte."
                )
            cohorts.content()
            with ui.stepper_navigation():
                ui.button("Précédent", on_click=stepper.previous).props("flat")
                ui.button("Suivant", on_click=stepper.next).props("color=green")

        # -- Étape 5 : Optimisation SQL ----------------------------------------
        with ui.step("Optimisation SQL", icon="speed"):
            with ui.element("div").classes("narrative-block"):
                ui.html(
                    "<b>Optimisation :</b> au-delà de l'analyse, il est essentiel "
                    "de démontrer que les requêtes sont <b>performantes</b>. "
                    "Cette section compare 3 paires de requêtes <b>avant/après</b> "
                    "optimisation, avec le plan d'exécution "
                    "(<code>EXPLAIN QUERY PLAN</code>) exécuté en direct."
                )
            optimisation.content()
            with ui.stepper_navigation():
                ui.button("Précédent", on_click=stepper.previous).props("flat")
                ui.button("Suivant", on_click=stepper.next).props("color=green")

        # -- Étape 6 : Conclusion ----------------------------------------------
        with ui.step("Conclusion", icon="emoji_events"):
            with ui.element("div").style("max-width: 800px"):
                ui.label("Récapitulatif").classes(
                    "text-2xl font-bold mb-2"
                ).style(f"color: {PRIMARY}")
                ui.markdown(
                    "Ce parcours a démontré les **techniques SQL avancées** "
                    "suivantes :\n\n"
                    "| Technique | Utilisée dans |\n"
                    "|-----------|---------------|\n"
                    "| **CTEs (WITH)** | Toutes les analyses |\n"
                    "| **Window functions** (LAG, ROW_NUMBER, NTILE) | Ventes, RFM |\n"
                    "| **Agrégations conditionnelles** (COUNT DISTINCT CASE WHEN) | Clients |\n"
                    "| **Self-join & delta mois** | Cohortes |\n"
                    "| **Index B-Tree** | Optimisation |\n"
                    "| **CTE MATERIALIZED** | Optimisation |\n"
                    "| **Projection minimale + LIMIT** | Optimisation |\n\n"
                    "Le schéma en étoile et les index permettent des requêtes "
                    "analytiques performantes, même sur un volume de ~112 000 lignes."
                )
            with ui.stepper_navigation():
                ui.button("Précédent", on_click=stepper.previous).props("flat")
                ui.button(
                    "Retour à l'accueil",
                    icon="home",
                    on_click=lambda: ui.navigate.to("/"),
                ).props("color=green")
