"""
Visualisation animée des plans d'exécution SQLite.

Fonctionnalités :
- Parse EXPLAIN QUERY PLAN (format texte avec |---)
- Visualise steps avec color coding : SCAN rouge / SEARCH vert
- Navigation step-by-step : prev/next + auto-play
- Explications pédagogiques inline
"""

from nicegui import ui
import asyncio
import re


class ExplainVisualizer:
    """Visualisation animée de plans EXPLAIN QUERY PLAN."""

    def __init__(self, explain_output: str):
        """
        Initialise le visualizer.

        Args:
            explain_output: Sortie brute de EXPLAIN QUERY PLAN (multi-lignes)
        """
        self.explain_output = explain_output
        self.steps = self._parse_explain(explain_output)
        self.current_step_index = 0
        self.is_playing = False

        # UI components
        self.steps_container = None
        self.controls_row = None

    def render(self) -> ui.column:
        """Construit l'UI du visualizer."""
        with ui.column().classes('w-full gap-4') as container:
            ui.label("🔍 Plan d'exécution SQLite").classes('text-xl font-semibold mb-2')

            # Container steps
            self.steps_container = ui.column().classes('w-full gap-2')

            # Controls
            with ui.row().classes('gap-2 mt-4') as controls:
                self.controls_row = controls
                ui.button('⏮ Début', on_click=self._reset).props('outline')
                ui.button('◀ Précédent', on_click=self._previous).props('outline')
                ui.button('▶ Suivant', on_click=self._next).props('color=primary')
                ui.button('⏯ Auto-play', on_click=self._toggle_autoplay).props('color=positive')

            # Render initial state
            self._render_steps()

        return container

    def _parse_explain(self, output: str) -> list[dict]:
        """
        Parse la sortie EXPLAIN QUERY PLAN.

        Format SQLite :
        ```
        QUERY PLAN
        |--SCAN TABLE fact_orders
        |--SEARCH TABLE fact_orders USING INDEX idx_orders_date (order_date>?)
        `--USE TEMP B-TREE FOR ORDER BY
        ```

        Returns:
            Liste de dicts avec {text, type, optimized, explanation}
        """
        steps = []
        lines = output.strip().split('\n')

        for line in lines:
            # Skip header
            if 'QUERY PLAN' in line or line.strip() == '':
                continue

            # Retirer préfixes tree (|--, `--)
            clean_line = re.sub(r'^[|\s`-]+', '', line).strip()

            # Identifier type d'opération
            step_type = 'unknown'
            optimized = False
            explanation = ""

            if 'SCAN TABLE' in clean_line.upper():
                step_type = 'scan'
                explanation = "⚠️ Parcours complet de la table (lent sur grandes tables)"

            elif 'SEARCH TABLE' in clean_line.upper():
                if 'USING INDEX' in clean_line.upper():
                    step_type = 'search_indexed'
                    optimized = True
                    explanation = "✅ Recherche optimisée avec index (rapide)"
                else:
                    step_type = 'search'
                    explanation = "🟡 Recherche sans index (moyen)"

            elif 'USE TEMP B-TREE' in clean_line.upper():
                step_type = 'temp_btree'
                explanation = "🔵 Tri temporaire en mémoire (OK si peu de lignes)"

            elif 'MATERIALIZE' in clean_line.upper():
                step_type = 'materialize'
                optimized = True
                explanation = "✅ Matérialisation de CTE (évite recalculs)"

            else:
                step_type = 'other'
                explanation = "📝 Opération auxiliaire"

            steps.append({
                'text': clean_line,
                'type': step_type,
                'optimized': optimized,
                'explanation': explanation,
            })

        return steps

    def _render_steps(self):
        """Affiche tous les steps avec highlight du step courant."""
        self.steps_container.clear()

        with self.steps_container:
            for i, step in enumerate(self.steps):
                is_current = (i == self.current_step_index)
                self._render_step(step, is_current, i + 1)

    def _render_step(self, step: dict, is_current: bool, step_num: int):
        """Rend un step avec color coding."""
        # Color selon type
        color_map = {
            'scan': 'red-900/30 border-red-500',  # Lent
            'search_indexed': 'green-900/30 border-green-500',  # Rapide
            'search': 'yellow-900/30 border-yellow-500',  # Moyen
            'temp_btree': 'blue-900/30 border-blue-500',  # OK
            'materialize': 'green-900/30 border-green-500',  # Optimisé
            'other': 'gray-900/30 border-gray-500',
        }

        icon_map = {
            'scan': '🔴',
            'search_indexed': '🟢',
            'search': '🟡',
            'temp_btree': '🔵',
            'materialize': '✅',
            'other': '📝',
        }

        bg_color = color_map.get(step['type'], 'gray-900/30 border-gray-500')
        icon = icon_map.get(step['type'], '📝')

        # Highlight si step courant
        if is_current:
            bg_color += ' ring-2 ring-white'

        with ui.card().classes(f'w-full bg-{bg_color} border-l-4'):
            with ui.row().classes('w-full items-start gap-3'):
                # Numéro step
                ui.label(f"{step_num}").classes('text-2xl font-bold text-gray-500 w-8')

                # Contenu
                with ui.column().classes('flex-1'):
                    # Texte opération
                    with ui.row().classes('items-center gap-2'):
                        ui.label(icon).classes('text-xl')
                        ui.label(step['text']).classes('font-mono text-sm')

                    # Explication si step courant
                    if is_current:
                        ui.markdown(f"**{step['explanation']}**").classes(
                            'mt-2 p-2 bg-black/30 rounded text-sm'
                        )

    def _reset(self):
        """Retour au début."""
        self.current_step_index = 0
        self._render_steps()

    def _previous(self):
        """Step précédent."""
        if self.current_step_index > 0:
            self.current_step_index -= 1
            self._render_steps()

    def _next(self):
        """Step suivant."""
        if self.current_step_index < len(self.steps) - 1:
            self.current_step_index += 1
            self._render_steps()

    async def _autoplay(self):
        """Animation auto (1.5s par step)."""
        self.is_playing = True
        self.current_step_index = 0

        while self.is_playing and self.current_step_index < len(self.steps):
            self._render_steps()
            await asyncio.sleep(1.5)
            self.current_step_index += 1

        self.is_playing = False

    def _toggle_autoplay(self):
        """Toggle auto-play."""
        if self.is_playing:
            self.is_playing = False
        else:
            # Lancer auto-play en background
            ui.timer(0, lambda: asyncio.create_task(self._autoplay()), once=True)
