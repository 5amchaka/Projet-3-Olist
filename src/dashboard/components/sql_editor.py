"""
Éditeur SQL interactif avec validation automatique.

Fonctionnalités :
- Édition SQL avec syntax highlighting (CodeMirror)
- Exécution READ-ONLY sécurisée
- Affichage résultats : tableau + graphique automatique
- Validation exercices avec comparaison solution
- Messages d'erreur pédagogiques
"""

from nicegui import ui
import pandas as pd
import sqlite3
from typing import Callable
import re

from src.db import Database
from src.dashboard.course.content import Exercise


class SQLEditor:
    """Éditeur SQL interactif pour les exercices du cours."""

    def __init__(
        self,
        initial_sql: str = "",
        exercise: Exercise | None = None,
        db: Database | None = None,
    ):
        """
        Initialise l'éditeur SQL.

        Args:
            initial_sql: Code SQL initial (starter pour exercices)
            exercise: Exercice associé (avec validateur)
            db: Instance Database (si None, en crée une)
        """
        self.initial_sql = initial_sql
        self.exercise = exercise
        self.db = db or Database()

        # UI components (initialisés dans render())
        self.editor = None
        self.result_container = None
        self.status_label = None

    def render(self) -> ui.column:
        """Construit l'UI de l'éditeur."""
        with ui.column().classes('w-full gap-4') as container:
            # Titre exercice si présent
            if self.exercise:
                with ui.card().classes('w-full bg-blue-900/20 border-l-4 border-blue-500'):
                    ui.label(self.exercise.title).classes('text-xl font-bold')
                    ui.markdown(self.exercise.description).classes('text-gray-300')

            # Éditeur SQL
            with ui.card().classes('w-full sql-editor-container'):
                ui.label("Éditeur SQL").classes('text-lg font-semibold mb-2')

                # CodeMirror avec mode SQL
                self.editor = ui.codemirror(
                    value=self.initial_sql,
                    language='sql',
                    theme='monokai',  # Dark theme
                ).classes('w-full').props('outlined')
                self.editor.style('height: 250px')

                # Boutons d'action
                with ui.row().classes('gap-2 mt-2'):
                    ui.button("▶ Exécuter", on_click=self._execute).props('color=positive')

                    if self.exercise:
                        ui.button("✓ Valider", on_click=self._validate).props('color=primary')
                        if self.exercise.hint:
                            ui.button("💡 Indice", on_click=self._show_hint).props('color=warning outline')

            # Zone de résultats
            self.result_container = ui.column().classes('w-full gap-2')

        return container

    def _execute(self):
        """Exécute la requête SQL et affiche les résultats."""
        sql = self.editor.value.strip()

        # Vérification sécurité : READ-ONLY
        if not self._is_read_only(sql):
            self._show_error("❌ Seules les requêtes SELECT sont autorisées (READ-ONLY).")
            return

        # Exécution
        try:
            result_df = self.db.query(sql)

            # Affichage résultats
            self._show_results(result_df)

        except sqlite3.Error as e:
            self._show_pedagogical_error(e)
        except Exception as e:
            self._show_error(f"❌ Erreur inattendue: {str(e)}")

    def _validate(self):
        """Valide l'exercice en comparant avec la solution de référence."""
        if not self.exercise:
            return

        sql = self.editor.value.strip()

        # Vérification sécurité
        if not self._is_read_only(sql):
            self._show_error("❌ Seules les requêtes SELECT sont autorisées.")
            return

        try:
            # Exécuter requête utilisateur
            result_df = self.db.query(sql)

            # Appeler validateur
            success, feedback = self.exercise.validator(result_df)

            # Afficher feedback
            if success:
                self._show_success(feedback)
            else:
                self._show_warning(feedback)

        except sqlite3.Error as e:
            self._show_pedagogical_error(e)
        except Exception as e:
            self._show_error(f"❌ Erreur lors de la validation: {str(e)}")

    def _show_results(self, df: pd.DataFrame):
        """Affiche les résultats de la requête."""
        self.result_container.clear()

        with self.result_container:
            ui.label(f"✓ Requête exécutée avec succès : {len(df)} ligne(s)").classes(
                'text-green-400 font-semibold'
            )

            if len(df) == 0:
                ui.label("Aucun résultat.").classes('text-gray-400 italic')
                return

            # Tableau de résultats
            with ui.card().classes('w-full'):
                ui.label("Résultats :").classes('text-lg font-semibold mb-2')

                # Limiter à 50 lignes pour l'affichage
                display_df = df.head(50)
                if len(df) > 50:
                    ui.label(f"(Affichage des 50 premières lignes sur {len(df)})").classes(
                        'text-sm text-gray-400 mb-2'
                    )

                # Table NiceGUI
                columns = [{'name': col, 'label': col, 'field': col} for col in display_df.columns]
                rows = display_df.to_dict('records')

                ui.table(columns=columns, rows=rows, row_key='index').classes('w-full')

            # Graphique automatique si structure adaptée
            chart = self._auto_chart(display_df)
            if chart:
                with ui.card().classes('w-full'):
                    ui.label("Visualisation automatique :").classes('text-lg font-semibold mb-2')
                    chart

    def _auto_chart(self, df: pd.DataFrame):
        """
        Génère un graphique automatiquement si la structure est adaptée.

        Heuristique : 1 colonne texte + 1-3 colonnes numériques → bar chart.

        Returns:
            ui.chart ou None
        """
        if len(df.columns) < 2 or len(df.columns) > 4:
            return None

        # Identifier colonnes
        text_cols = [col for col in df.columns if df[col].dtype == 'object']
        numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]

        # Vérifier structure : 1 texte + 1-3 numériques
        if len(text_cols) != 1 or not (1 <= len(numeric_cols) <= 3):
            return None

        # Limiter à 20 premières lignes pour lisibilité
        chart_df = df.head(20)

        # Construire options ECharts
        x_col = text_cols[0]
        categories = chart_df[x_col].tolist()

        series = []
        for num_col in numeric_cols:
            series.append({
                'name': num_col,
                'type': 'bar',
                'data': chart_df[num_col].tolist(),
            })

        chart_options = {
            'tooltip': {'trigger': 'axis'},
            'legend': {'data': numeric_cols},
            'xAxis': {
                'type': 'category',
                'data': categories,
                'axisLabel': {'rotate': 45, 'fontSize': 10},
            },
            'yAxis': {'type': 'value'},
            'series': series,
            'grid': {'bottom': 80},
        }

        return ui.echart(chart_options).classes('w-full h-80')

    def _show_pedagogical_error(self, error: sqlite3.Error):
        """Transforme une erreur SQLite en message pédagogique."""
        error_msg = str(error).lower()

        self.result_container.clear()
        with self.result_container:
            with ui.card().classes('w-full bg-red-900/20 border-l-4 border-red-500'):
                ui.label("❌ Erreur SQL").classes('text-xl font-bold text-red-400 mb-2')

                # Messages pédagogiques selon le type d'erreur
                if 'no such table' in error_msg:
                    # Extraire nom de table
                    match = re.search(r"no such table: (\w+)", error_msg)
                    table_name = match.group(1) if match else "inconnue"

                    ui.markdown(f"""**Table `{table_name}` introuvable.**

**Tables disponibles dans le DWH Olist** :
- `fact_orders` (table de faits, 112k lignes)
- `dim_customers`, `dim_sellers`, `dim_products`, `dim_geolocation`, `dim_dates`
- `v_monthly_sales`, `v_customer_cohorts` (vues)

💡 Vérifiez l'orthographe et utilisez les tables listées ci-dessus.
""").classes('text-gray-300')

                elif 'no such column' in error_msg:
                    ui.markdown(f"""**Colonne introuvable.**

{error_msg}

💡 **Astuces** :
- Utilisez `SELECT * FROM table LIMIT 5` pour voir les colonnes disponibles
- Vérifiez l'orthographe (sensible à la casse)
- Préfixez avec l'alias de table si jointure : `o.price` au lieu de `price`
""").classes('text-gray-300')

                elif 'syntax error' in error_msg:
                    ui.markdown(f"""**Erreur de syntaxe SQL.**

{error_msg}

💡 **Points de contrôle** :
- Virgules entre colonnes SELECT (mais PAS avant FROM)
- Parenthèses équilibrées dans les fonctions
- Mots-clés corrects (GROUP BY, ORDER BY, etc.)
- Point-virgule uniquement à la fin
""").classes('text-gray-300')

                elif 'ambiguous column' in error_msg:
                    ui.markdown(f"""**Colonne ambiguë dans une jointure.**

{error_msg}

💡 **Solution** : Préfixez avec l'alias de table.
```sql
-- ❌ Ambiguë
SELECT customer_id FROM fact_orders o JOIN dim_customers c ...

-- ✅ Clair
SELECT o.customer_id FROM fact_orders o JOIN dim_customers c ...
```
""").classes('text-gray-300')

                else:
                    # Erreur générique
                    ui.markdown(f"""**Erreur** : {error_msg}

💡 Consultez la syntaxe SQL et réessayez.
""").classes('text-gray-300')

    def _show_error(self, message: str):
        """Affiche un message d'erreur."""
        self.result_container.clear()
        with self.result_container:
            with ui.card().classes('w-full bg-red-900/20 border-l-4 border-red-500'):
                ui.markdown(message).classes('text-red-400')

    def _show_warning(self, message: str):
        """Affiche un message d'avertissement (validation échouée)."""
        self.result_container.clear()
        with self.result_container:
            with ui.card().classes('w-full bg-yellow-900/20 border-l-4 border-yellow-500'):
                ui.markdown(message).classes('text-yellow-400')

    def _show_success(self, message: str):
        """Affiche un message de succès."""
        self.result_container.clear()
        with self.result_container:
            with ui.card().classes('w-full bg-green-900/20 border-l-4 border-green-500'):
                ui.markdown(message).classes('text-green-400 text-lg')

                # Confetti animation (optionnel, fun!)
                ui.run_javascript('confetti({particleCount: 100, spread: 70, origin: {y: 0.6}});')

    def _show_hint(self):
        """Affiche l'indice de l'exercice."""
        if not self.exercise or not self.exercise.hint:
            return

        self.result_container.clear()
        with self.result_container:
            with ui.card().classes('w-full bg-blue-900/20 border-l-4 border-blue-500'):
                ui.label("💡 Indice").classes('text-xl font-bold text-blue-400 mb-2')
                ui.markdown(self.exercise.hint).classes('text-gray-300')

    @staticmethod
    def _is_read_only(sql: str) -> bool:
        """
        Vérifie que la requête est READ-ONLY (SELECT uniquement).

        Args:
            sql: Requête SQL à vérifier

        Returns:
            True si READ-ONLY, False sinon
        """
        # Retirer commentaires
        sql_clean = re.sub(r'--.*', '', sql)
        sql_clean = re.sub(r'/\*.*?\*/', '', sql_clean, flags=re.DOTALL)

        # Normaliser (lowercase, espaces)
        sql_clean = sql_clean.lower().strip()

        # Vérifier mots-clés interdits
        forbidden = [
            'insert', 'update', 'delete', 'drop', 'create', 'alter',
            'truncate', 'replace', 'merge', 'grant', 'revoke'
        ]

        for keyword in forbidden:
            if re.search(rf'\b{keyword}\b', sql_clean):
                return False

        # Autoriser SELECT, WITH, EXPLAIN
        if re.search(r'\b(select|with|explain)\b', sql_clean):
            return True

        return False
