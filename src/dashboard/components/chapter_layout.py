"""
Layout uniforme pour chaque leçon du cours.

Fonctionnalités :
- Sidebar fixe (256px) avec accordéons des 5 modules
- Highlight leçon courante (fond vert)
- Progress bar (% complétion globale)
- Navigation footer : Précédent / Suivant avec edge cases
- Main content scrollable pour le contenu de la leçon
"""

from nicegui import ui
from typing import Callable
from src.dashboard.course.content import COURSE_MODULES, Module


class ChapterLayout:
    """Layout uniforme pour les leçons du cours."""

    def __init__(
        self,
        module_id: str,
        lesson_index: int,
        on_navigate: Callable[[str, int], None] | None = None,
    ):
        """
        Initialise le layout.

        Args:
            module_id: ID du module courant
            lesson_index: Index de la leçon courante (0-based)
            on_navigate: Callback (module_id, lesson_index) pour navigation
        """
        self.module_id = module_id
        self.lesson_index = lesson_index
        self.on_navigate = on_navigate or self._default_navigate

        # Trouver module courant
        self.module = next((m for m in COURSE_MODULES if m.id == module_id), None)
        if not self.module:
            raise ValueError(f"Module {module_id} introuvable")

        self.total_lessons = len(self.module.lessons)

    def render(self, content_builder: Callable[[], None]) -> ui.row:
        """
        Construit le layout complet.

        Args:
            content_builder: Fonction qui construit le contenu de la leçon

        Returns:
            ui.row container
        """
        with ui.row().classes('w-full h-screen gap-0') as layout:
            # Sidebar fixe
            with ui.column().classes('w-64 bg-gray-900 border-r border-gray-700 course-sidebar').style(
                'height: 100vh; overflow-y: auto;'
            ):
                self._render_sidebar()

            # Main content
            with ui.column().classes('flex-1 overflow-y-auto p-8').style('height: 100vh;'):
                # Progress bar en haut
                self._render_progress()

                # Contenu de la leçon (injecté par le caller)
                with ui.column().classes('w-full max-w-4xl mx-auto gap-6'):
                    content_builder()

                # Footer navigation
                self._render_footer()

        return layout

    def _render_sidebar(self):
        """Affiche la sidebar avec accordéons des modules."""
        # Header
        with ui.row().classes('w-full p-4 border-b border-gray-700'):
            ui.icon('school').classes('text-green-400 text-2xl')
            ui.label('Cours SQL Avancé').classes('text-lg font-bold ml-2')

        # Accordéons des modules
        for i, module in enumerate(COURSE_MODULES, 1):
            is_current_module = (module.id == self.module_id)

            with ui.expansion(
                f"{i}. {module.title}",
                icon=module.icon,
                value=is_current_module  # Ouvert si module courant
            ).classes('w-full'):
                # Leçons du module
                for j, lesson in enumerate(module.lessons):
                    is_current = (module.id == self.module_id and j == self.lesson_index)

                    # Bouton leçon
                    btn_classes = 'w-full text-left px-4 py-2 lesson-item'
                    if is_current:
                        btn_classes += ' active bg-green-600 text-black font-semibold'

                    ui.button(
                        f"  {j + 1}. {lesson.title}",
                        on_click=lambda m=module.id, idx=j: self._navigate_to(m, idx)
                    ).classes(btn_classes).props('flat dense')

    def _render_progress(self):
        """Affiche la progress bar."""
        # Calculer progression globale
        total_lessons_global = sum(len(m.lessons) for m in COURSE_MODULES)
        completed_lessons = 0

        # Compter leçons complétées (modules avant + leçons avant dans module courant)
        for module in COURSE_MODULES:
            if module.id == self.module_id:
                completed_lessons += self.lesson_index
                break
            else:
                completed_lessons += len(module.lessons)

        progress_pct = (completed_lessons / total_lessons_global) * 100

        # Affichage
        with ui.card().classes('w-full bg-gray-800 mb-4'):
            with ui.row().classes('w-full justify-between items-center mb-2'):
                ui.label('Progression globale').classes('text-sm text-gray-400')
                ui.label(f'{completed_lessons}/{total_lessons_global} leçons').classes(
                    'text-sm font-semibold text-green-400'
                )

            # Barre de progression
            ui.linear_progress(
                value=progress_pct / 100,
                show_value=False
            ).classes('course-progress').props('color=positive')

    def _render_footer(self):
        """Affiche la navigation footer."""
        with ui.row().classes('w-full justify-between mt-8 p-4 border-t border-gray-700'):
            # Bouton Précédent
            if self._has_previous():
                prev_module_id, prev_index = self._get_previous()
                ui.button(
                    '← Leçon précédente',
                    on_click=lambda: self._navigate_to(prev_module_id, prev_index)
                ).props('outline')
            else:
                ui.button(
                    '← Retour intro',
                    on_click=lambda: ui.navigate.to('/presentation')
                ).props('outline')

            # Bouton Suivant
            if self._has_next():
                next_module_id, next_index = self._get_next()
                ui.button(
                    'Leçon suivante →',
                    on_click=lambda: self._navigate_to(next_module_id, next_index)
                ).props('color=primary')
            else:
                ui.button(
                    '✓ Terminer le cours',
                    on_click=lambda: ui.navigate.to('/presentation')
                ).props('color=positive')

    def _has_previous(self) -> bool:
        """Vérifie s'il existe une leçon précédente."""
        if self.lesson_index > 0:
            return True

        # Vérifier module précédent
        module_index = next((i for i, m in enumerate(COURSE_MODULES) if m.id == self.module_id), -1)
        return module_index > 0

    def _has_next(self) -> bool:
        """Vérifie s'il existe une leçon suivante."""
        if self.lesson_index < self.total_lessons - 1:
            return True

        # Vérifier module suivant
        module_index = next((i for i, m in enumerate(COURSE_MODULES) if m.id == self.module_id), -1)
        return module_index < len(COURSE_MODULES) - 1

    def _get_previous(self) -> tuple[str, int]:
        """Retourne (module_id, lesson_index) de la leçon précédente."""
        if self.lesson_index > 0:
            return self.module_id, self.lesson_index - 1

        # Module précédent, dernière leçon
        module_index = next(i for i, m in enumerate(COURSE_MODULES) if m.id == self.module_id)
        prev_module = COURSE_MODULES[module_index - 1]
        return prev_module.id, len(prev_module.lessons) - 1

    def _get_next(self) -> tuple[str, int]:
        """Retourne (module_id, lesson_index) de la leçon suivante."""
        if self.lesson_index < self.total_lessons - 1:
            return self.module_id, self.lesson_index + 1

        # Module suivant, première leçon
        module_index = next(i for i, m in enumerate(COURSE_MODULES) if m.id == self.module_id)
        next_module = COURSE_MODULES[module_index + 1]
        return next_module.id, 0

    def _navigate_to(self, module_id: str, lesson_index: int):
        """Navigue vers une leçon."""
        self.on_navigate(module_id, lesson_index)

    @staticmethod
    def _default_navigate(module_id: str, lesson_index: int):
        """Navigation par défaut (reload page)."""
        ui.navigate.to(f'/presentation/{module_id}/{lesson_index}')
