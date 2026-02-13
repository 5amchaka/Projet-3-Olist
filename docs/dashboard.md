# Dashboard Olist SQL Explorer

Ce guide couvre le module dashboard (`src/dashboard`) : architecture, lancement, pages et mode presentation.

## Prerequis

Le dashboard utilise des dependances optionnelles.

```bash
uv sync --extra dashboard
```

Le dashboard lit la base SQLite `data/database/olist_dw.db`.
Si la base n'existe pas encore :

```bash
uv run python -m src.etl
```

## Lancement

```bash
uv run --extra dashboard python -m src.dashboard
```

Raccourci Makefile :

```bash
make dashboard
```

Par defaut le serveur ecoute sur le port `8080`.
Pour changer le port :

```bash
DASHBOARD_PORT=8090 uv run --extra dashboard python -m src.dashboard
```

Par defaut, le dashboard n'ouvre pas automatiquement un navigateur (pratique en environnement headless).
Pour activer l'ouverture auto :

```bash
DASHBOARD_SHOW_BROWSER=1 uv run --extra dashboard python -m src.dashboard
```

## Architecture

Structure principale :

- `src/dashboard/main.py` : point d'entree NiceGUI, enregistrement des pages, startup.
- `src/dashboard/db.py` : connexion SQLite, chargement SQL, execution requetes.
- `src/dashboard/theme.py` : palette couleurs, CSS, templates graphiques.
- `src/dashboard/presentation.py` : parcours narratif en 5 etapes (`/presentation`).
- `src/dashboard/components/` : composants reutilisables (`sql_viewer`, `sql_editor`, `sql_annotator`, `explain_visualizer`, `kpi_card`, `insight`, `benchmark`, `chapter_layout`, `page_layout`).
- `src/dashboard/pages/` : pages analytiques.

## Pages disponibles

- `/` : vue d'ensemble (KPIs + sparkline CA mensuel)
- `/trends` : tendances mensuelles
- `/ventes` : top categories, CA YoY, panier moyen
- `/clients` : nouveaux vs recurrents, LTV cohortes
- `/rfm` : segmentation RFM
- `/cohorts` : retention cohortes
- `/pareto` : Pareto vendeurs
- `/scoring` : scoring vendeurs
- `/optimisation` : comparaisons SQL avant/apres
- `/presentation` : mode presentation guide

## SQL utilise par le dashboard

Les requetes sont dans `sql/dashboard/*.sql`.
Inventaire detaille :

- `sql/dashboard/README.md`

Les vues SQL reutilisees par plusieurs pages sont definies dans :

- `sql/views.sql`

## Tests dashboard

Tests cibles :

```bash
uv run --extra dev --extra dashboard python -m pytest -q tests/test_dashboard_db.py tests/test_dashboard_sql.py tests/dashboard/
```

Ces tests couvrent la couche DB dashboard, l'execution SQL, les validateurs d'exercices,
le contenu pedagogique et le visualiseur `EXPLAIN`.
