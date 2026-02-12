"""
Annotations interactives sur le code SQL.

Fonctionnalités :
- Détecte keywords SQL dans le code (LAG, NTILE, WITH, JOIN, etc.)
- Tooltips hover : short_desc du concept (1 phrase)
- Click sur keyword → panel latéral détaillé : detailed_desc + exemple
- Highlight syntaxique avancé avec couleurs
"""

from nicegui import ui
import re
from src.dashboard.course.content import CONCEPTS_INDEX, SQLConcept


class SQLAnnotator:
    """Annotations interactives sur code SQL pour pédagogie."""

    def __init__(self, sql_code: str, concepts: list[SQLConcept]):
        """
        Initialise l'annotateur.

        Args:
            sql_code: Code SQL à annoter
            concepts: Liste des concepts à annoter dans ce code
        """
        self.sql_code = sql_code
        self.concepts = concepts
        self.concept_panel = None  # Panel détails (initialisé dans render())

    def render(self) -> ui.column:
        """Construit l'UI avec code annoté + panel détails."""
        with ui.column().classes('w-full gap-4') as container:
            ui.label("🔍 Démo SQL Annotée").classes('text-xl font-semibold mb-2')

            # Row : Code à gauche + Panel détails à droite (si concept cliqué)
            with ui.row().classes('w-full gap-4'):
                # Code annoté (70% largeur)
                with ui.card().classes('flex-grow sql-editor-container'):
                    self._render_annotated_code()

                # Panel détails concepts (30% largeur, initialement caché)
                self.concept_panel = ui.column().classes('w-96').style('display: none;')

        return container

    def _render_annotated_code(self):
        """Affiche le code SQL avec annotations cliquables."""
        # Split en lignes pour numérotation
        lines = self.sql_code.split('\n')

        # Container avec scrolling
        with ui.scroll_area().classes('w-full').style('max-height: 400px;'):
            # Code block avec font monospace
            with ui.column().classes('gap-0 p-4 bg-gray-900 rounded'):
                for i, line in enumerate(lines, 1):
                    self._render_line(i, line)

    def _render_line(self, line_num: int, line: str):
        """Rend une ligne de code avec annotations."""
        # Numéro de ligne
        with ui.row().classes('gap-2 items-start'):
            ui.label(str(line_num)).classes(
                'text-gray-600 text-sm font-mono w-8 text-right flex-shrink-0'
            )

            # Contenu ligne annoté
            line_html = self._annotate_line_html(line)
            ui.html(line_html).classes('font-mono text-sm')

    def _annotate_line_html(self, line: str) -> str:
        """
        Transforme une ligne SQL en HTML avec keywords cliquables.

        Args:
            line: Ligne SQL brute

        Returns:
            HTML avec spans cliquables
        """
        # Keywords à annoter (extraire de self.concepts)
        keywords = {concept.keyword for concept in self.concepts}

        # Pattern regex : mots entiers uniquement
        pattern = r'\b(' + '|'.join(re.escape(kw) for kw in keywords) + r')\b'

        def replace_keyword(match):
            keyword = match.group(1)
            concept = next((c for c in self.concepts if c.keyword == keyword), None)

            if not concept:
                return keyword

            # Tooltip (short_desc) + onclick
            return f'''<span
                class="sql-keyword-annotated"
                title="{concept.short_desc}"
                onclick="window.show_concept_panel('{keyword}')"
                style="color: #00C853; cursor: pointer; text-decoration: underline dotted;"
            >{keyword}</span>'''

        # Remplacer keywords
        annotated = re.sub(pattern, replace_keyword, line, flags=re.IGNORECASE)

        # Colorier autres éléments SQL basiques (comments, strings)
        # Comments SQL (-- ...)
        annotated = re.sub(
            r'(--.*)',
            r'<span style="color: #888; font-style: italic;">\1</span>',
            annotated
        )

        # Strings ('...')
        annotated = re.sub(
            r"'([^']*)'",
            r"<span style='color: #e67e22;'>'\1'</span>",
            annotated
        )

        return annotated

    def show_concept_panel(self, keyword: str):
        """Affiche le panel détails pour un concept cliqué."""
        concept = CONCEPTS_INDEX.get(keyword)
        if not concept:
            return

        # Rendre panel visible
        self.concept_panel.style('display: block;')

        # Remplir contenu
        self.concept_panel.clear()
        with self.concept_panel:
            with ui.card().classes('w-full concept-detail-panel'):
                # Header avec icône catégorie
                category_icons = {
                    'window': '📊',
                    'cte': '🌳',
                    'aggregate': '📈',
                    'join': '🔗',
                    'index': '⚡',
                    'function': '🔧',
                }
                icon = category_icons.get(concept.category, '📝')

                with ui.row().classes('w-full justify-between items-center mb-4'):
                    ui.label(f"{icon} {concept.name}").classes('text-xl font-bold')
                    ui.button(
                        icon='close',
                        on_click=lambda: self.concept_panel.style('display: none;')
                    ).props('flat round size=sm')

                # Description détaillée
                ui.markdown(concept.detailed_desc).classes('text-gray-300 mb-4')

                # Exemple SQL
                ui.label("💻 Exemple :").classes('text-lg font-semibold mb-2')
                with ui.card().classes('w-full bg-gray-900 p-4'):
                    ui.html(f'<pre class="font-mono text-sm" style="margin: 0; white-space: pre-wrap;">{concept.example_sql}</pre>')

    def render_with_js_bridge(self) -> ui.column:
        """
        Version avec bridge JavaScript pour gérer les clicks.

        Note: NiceGUI ne peut pas facilement capter les onclick dans ui.html.
        Cette méthode injecte un bridge global JavaScript.
        """
        container = self.render()

        # Injecter bridge JavaScript
        ui.run_javascript(f"""
        window.show_concept_panel = function(keyword) {{
            // Envoyer événement au backend via WebSocket
            emitEvent('concept_clicked', {{keyword: keyword}});
        }};
        """)

        # Écouter événement côté Python
        # Note: Nécessite ui.on() custom ou utiliser ui.button avec binding

        return container
