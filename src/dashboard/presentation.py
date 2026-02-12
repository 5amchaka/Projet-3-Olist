"""
Mode Cours SQL Avancé — Apprentissage interactif avec exercices.

Routes :
- /presentation : Introduction DWH (6 slides)
- /presentation/{module_id}/{lesson_index} : Leçon interactive
"""

from nicegui import ui

from src.dashboard.theme import BG_DARK, CUSTOM_CSS, PRIMARY
from src.dashboard.course.dwh_intro import render_intro_carousel
from src.dashboard.course.content import COURSE_MODULES
from src.dashboard.components.chapter_layout import ChapterLayout
from src.dashboard.components.sql_editor import SQLEditor
from src.dashboard.components.sql_annotator import SQLAnnotator
from src.db import Database


# Instance database globale
db = Database()


@ui.page("/presentation")
def presentation_home() -> None:
    """Page d'accueil du cours : Introduction DWH (6 slides)."""
    ui.add_head_html(CUSTOM_CSS)

    # Header
    with ui.header().classes("items-center justify-between px-4").style(
        f"background: {BG_DARK}; border-bottom: 1px solid #333"
    ):
        with ui.row().classes("items-center gap-2"):
            ui.icon("school").classes("text-2xl").style(f"color: {PRIMARY}")
            ui.label("Cours SQL Avancé — Olist").classes(
                "text-lg font-bold"
            ).style("color: white")
        ui.button(
            "Mode Explorer",
            icon="explore",
            on_click=lambda: ui.navigate.to("/"),
        ).props("flat color=white")

    # Contenu : Introduction DWH
    with ui.column().classes("w-full max-w-5xl mx-auto p-8"):
        render_intro_carousel()


@ui.page("/presentation/{module_id}/{lesson_index}")
def presentation_lesson(module_id: str, lesson_index: int) -> None:
    """
    Affiche une leçon interactive.

    Args:
        module_id: ID du module (ex: "module_1_fundamentals")
        lesson_index: Index de la leçon dans le module (0-based)
    """
    ui.add_head_html(CUSTOM_CSS)

    # Trouver module et leçon
    module = next((m for m in COURSE_MODULES if m.id == module_id), None)
    if not module:
        ui.label(f"❌ Module {module_id} introuvable").classes("text-red-500 text-xl")
        return

    if lesson_index < 0 or lesson_index >= len(module.lessons):
        ui.label(f"❌ Leçon {lesson_index} introuvable dans {module.title}").classes(
            "text-red-500 text-xl"
        )
        return

    lesson = module.lessons[lesson_index]

    # Header
    with ui.header().classes("items-center justify-between px-4").style(
        f"background: {BG_DARK}; border-bottom: 1px solid #333"
    ):
        with ui.row().classes("items-center gap-2"):
            ui.icon(module.icon).classes("text-2xl").style(f"color: {PRIMARY}")
            ui.label(f"{module.title} — {lesson.title}").classes(
                "text-lg font-bold"
            ).style("color: white")
        with ui.row().classes("gap-2"):
            ui.button(
                "Retour intro",
                icon="home",
                on_click=lambda: ui.navigate.to("/presentation"),
            ).props("flat color=white outline")
            ui.button(
                "Mode Explorer",
                icon="explore",
                on_click=lambda: ui.navigate.to("/"),
            ).props("flat color=white")

    # Layout avec sidebar
    layout = ChapterLayout(module_id, lesson_index)
    layout.render(lambda: render_lesson_content(lesson))


def render_lesson_content(lesson):
    """
    Construit le contenu d'une leçon.

    Structure :
    1. Théorie (markdown)
    2. Démo SQL annotée (requête existante)
    3. Exercice interactif (si présent)
    4. Lien vers exploration (si présent)

    Args:
        lesson: Instance Lesson
    """
    # 1. Théorie
    with ui.card().classes('w-full mb-6'):
        ui.label("📚 Théorie").classes('text-2xl font-bold mb-4').style(f"color: {PRIMARY}")
        ui.markdown(lesson.theory).classes('text-gray-300 leading-relaxed')

    # 2. Démo SQL annotée
    if lesson.demo_sql_file:
        with ui.card().classes('w-full mb-6'):
            ui.label("💻 Démo : Requête SQL annotée").classes('text-2xl font-bold mb-4').style(
                f"color: {PRIMARY}"
            )
            ui.label(f"Fichier : sql/dashboard/{lesson.demo_sql_file}").classes(
                'text-sm text-gray-500 mb-4'
            )

            # Charger SQL depuis fichier
            try:
                sql_code = db.load_sql(lesson.demo_sql_file)

                # Annotateur (version simplifiée sans JS bridge)
                # Pour l'instant, affichage code + liste concepts
                with ui.column().classes('w-full gap-4'):
                    # Code SQL brut avec syntax highlighting
                    with ui.card().classes('w-full bg-gray-900 p-4'):
                        ui.html(
                            f'<pre class="sql-demo-block font-mono text-sm" style="margin: 0; white-space: pre-wrap; color: #e0e0e0;">{sql_code}</pre>'
                        )

                    # Liste des concepts annotables
                    if lesson.concepts:
                        ui.label("🔑 Concepts SQL utilisés :").classes(
                            'text-lg font-semibold mt-4'
                        )
                        with ui.column().classes('gap-2'):
                            for concept in lesson.concepts:
                                with ui.expansion(
                                    concept.name, icon='info'
                                ).classes('w-full bg-blue-900/20'):
                                    ui.markdown(concept.short_desc).classes('text-gray-400 mb-2')
                                    ui.markdown(concept.detailed_desc).classes('text-gray-300')
                                    ui.label("💡 Exemple :").classes(
                                        'text-sm font-semibold mt-2'
                                    )
                                    with ui.card().classes('bg-gray-900 p-3'):
                                        ui.html(
                                            f'<pre class="font-mono text-xs" style="margin: 0; white-space: pre-wrap;">{concept.example_sql}</pre>'
                                        )

            except FileNotFoundError:
                ui.label(f"⚠️ Fichier {lesson.demo_sql_file} introuvable").classes(
                    'text-yellow-500'
                )

    # 3. Exercice interactif
    if lesson.exercise:
        with ui.card().classes('w-full mb-6'):
            ui.label("✏️ Exercice Pratique").classes('text-2xl font-bold mb-4').style(
                f"color: {PRIMARY}"
            )

            # SQLEditor avec exercice
            editor = SQLEditor(
                initial_sql=lesson.exercise.starter_sql,
                exercise=lesson.exercise,
                db=db,
            )
            editor.render()

    # 4. Lien exploration
    if lesson.exploration_link:
        with ui.card().classes('w-full mb-6 bg-green-900/20 border-l-4 border-green-500'):
            ui.label("🚀 Exploration Libre").classes('text-xl font-bold mb-2')
            ui.markdown(
                "Cette leçon est liée à une page d'exploration interactive du dashboard. "
                "Vous pouvez y accéder pour approfondir l'analyse."
            ).classes('text-gray-300 mb-4')
            ui.button(
                "Ouvrir le dashboard d'exploration",
                icon='open_in_new',
                on_click=lambda: ui.navigate.to(lesson.exploration_link),
            ).props('color=positive')
