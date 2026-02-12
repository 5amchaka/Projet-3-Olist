# Olist Analytics Platform

Plateforme d'analyse du dataset Olist (Brazilian E-commerce, ~100k commandes 2016-2018) :
pipeline ETL Python, data warehouse SQLite en star schema, dashboard NiceGUI et cours SQL interactif.

Le point d'entree principal est le launcher (`launch.py`), qui orchestre setup, checks, download, ETL et lancement du dashboard.

## Lancement rapide (recommande)

### Parcours A: automatise (one-command)

```bash
uv venv && uv sync --all-extras
make launch
```

`make launch` appelle `uv run python launch.py --theme simplon` et gere automatiquement:
- validation de l'environnement
- health checks
- download CSV si necessaire
- ETL si necessaire (skip intelligent si la DB est deja a jour)
- lancement du dashboard

Par defaut, `make launch` ne lance pas les tests.

Options courantes:

```bash
make launch-force
make launch-quick
make launch-with-tests
make launch-with-all-tests
make launch-with-verify
make health
```

Exemples en CLI direct:

```bash
uv run python launch.py --theme simplon --force
uv run python launch.py --port 8888 --no-browser
uv run python launch.py --no-splash --run-tests
uv run python launch.py --health-check-only
```

### Parcours B: manuel (etape par etape)

1. Installation

```bash
uv venv && uv sync
```

Extras selon besoin:

```bash
uv sync --extra dashboard
uv sync --extra dev
uv sync --extra notebook
```

2. Configuration (`.env` optionnel)

```bash
cp .env.example .env
```

Variables utiles:
- `DASHBOARD_PORT` (defaut: `8080`)
- `DASHBOARD_SHOW_BROWSER` (si absent: navigateur non ouvert automatiquement)

Note Kaggle:
- `make download` / `scripts/download_dataset.sh` attendent `KAGGLE_USERNAME` et `KAGGLE_KEY`.
- le launcher (`make launch`) applique un fallback pour le dataset public si credentials absentes.

3. Telecharger les donnees

```bash
make download
# ou: bash scripts/download_dataset.sh
```

4. Lancer le pipeline ETL

```bash
make etl
```

La base SQLite est creee dans `data/database/olist_dw.db`.

5. Lancer le dashboard

```bash
make dashboard
```

Acces:
- `http://localhost:8080`
- `http://localhost:8080/presentation` (cours SQL)

Exemples:

```bash
DASHBOARD_PORT=8090 make dashboard
DASHBOARD_SHOW_BROWSER=1 make dashboard
```

## Commandes utiles (Makefile)

| Commande | Description |
|----------|-------------|
| `make install` | Creer le venv + installer les dependances de base |
| `make download` | Telecharger et valider les 9 CSV Olist |
| `make etl` | Executer le pipeline ETL complet |
| `make dashboard` | Lancer le dashboard NiceGUI |
| `make launch` | Launcher automatise (one-command) |
| `make launch-force` | Launcher avec rebuild complet |
| `make launch-quick` | Launcher en mode rapide (skip si possible) |
| `make launch-with-tests` | Launcher avec tests unitaires |
| `make launch-with-all-tests` | Launcher avec tous les tests |
| `make launch-with-verify` | Launcher avec verification CSV (csvkit) |
| `make health` | Diagnostic systeme |
| `make test` | Tests unitaires (hors integration) |
| `make test-integration` | Tests d'integrite CSV <-> DW |
| `make test-all` | Tous les tests |
| `make verify` | Verification CSV via csvkit |

## Tests et CI

- `make test`: execute les tests hors `@pytest.mark.integration`.
- `make test-integration`: execute les tests d'integrite pipeline (`tests/test_pipeline_integrity.py`).
- `make test-all`: execute tous les tests, y compris les tests dashboard marques `integration`.
- `make verify`: verification independente de l'analyse CSV via `csvkit`.

CI (`.github/workflows/ci.yml`):
- `uv sync --all-extras`
- `pytest -m "not integration" --cov=src --cov-report=term-missing`

## Cours SQL interactif

Le dashboard inclut un cours SQL avance:
- 5 modules
- 15 lecons
- 9 exercices progressifs
- environ 160 min

Acces:
- `http://localhost:8080/presentation`

Fonctionnalites:
- editeur SQL (read-only executeur securise)
- annotations de concepts SQL
- visualisation `EXPLAIN QUERY PLAN`

Details:
- [docs/dashboard.md](docs/dashboard.md)
- [sql/dashboard/README.md](sql/dashboard/README.md)

## Structure du projet

```text
launch.py             # Point d'entree CLI (launcher automatise)
src/etl/              # Pipeline ETL (extract, transform, load)
src/dashboard/        # Dashboard NiceGUI (analytics + cours SQL)
src/database/         # Connexion SQLAlchemy et modeles
src/launcher/         # Orchestration (download -> ETL -> tests -> dashboard)
src/config.py         # Configuration centralisee (chemins, CSV)
sql/                  # DDL star schema, vues, requetes dashboard, exercices
scripts/              # Scripts utilitaires (download, verification CSV)
notebooks/            # Exploration et tracabilite CSV <-> BDD
tests/                # Tests unitaires et integration
docs/                 # Documentation technique
data/raw/             # CSV bruts depuis Kaggle
data/database/        # SQLite data warehouse (olist_dw.db)
```

## Documentation

| Document | Contenu |
|----------|---------|
| [docs/csv_to_star_schema.md](docs/csv_to_star_schema.md) | Choix de modelisation: 9 CSV -> 6 tables |
| [docs/exploration_analysis.md](docs/exploration_analysis.md) | Analyse empirique des donnees brutes |
| [docs/data_dictionary.md](docs/data_dictionary.md) | Dictionnaire de donnees: colonnes, types, semantique |
| [docs/dashboard.md](docs/dashboard.md) | Architecture dashboard, pages, cours SQL |
| [docs/launcher.md](docs/launcher.md) | Launcher: architecture, options, workflows |
| [docs/Analyse_Transformations_Olist_DW.md](docs/Analyse_Transformations_Olist_DW.md) | Analyse des transformations ETL |
| [sql/dashboard/README.md](sql/dashboard/README.md) | Inventaire des requetes SQL du dashboard |
| [notebooks/exploration_csv.ipynb](notebooks/exploration_csv.ipynb) | Exploration: profils, cardinalites, visualisations |
| [notebooks/comparaison_csv_bdd.ipynb](notebooks/comparaison_csv_bdd.ipynb) | Tracabilite CSV -> BDD: volumetrie, distributions |

## Star Schema

Le data warehouse utilise un schema en etoile:
- 5 dimensions: `dim_dates`, `dim_geolocation`, `dim_customers`, `dim_sellers`, `dim_products`
- 1 table de faits: `fact_orders` (grain = article commande)

Voir:
- [docs/csv_to_star_schema.md](docs/csv_to_star_schema.md)
- [docs/exploration_analysis.md](docs/exploration_analysis.md)

## Datasets

| Dataset | ~Lignes | Description |
|---------|---------|-------------|
| customers | 99k | Clients et localisation |
| geolocation | 1M | Coordonnees par code postal |
| orders | 99k | Commandes et timestamps |
| order_items | 112k | Articles par commande |
| order_payments | 103k | Paiements par commande |
| order_reviews | 99k | Avis clients |
| products | 32k | Catalogue produits |
| sellers | 3k | Vendeurs |
| category_translation | 71 | Traduction des categories PT -> EN |

## Troubleshooting

- `KAGGLE_USERNAME and KAGGLE_KEY must be set`
  - Ce message vient de `make download` / `scripts/download_dataset.sh`.
  - Renseigner `.env` puis relancer `make download`, ou passer par `make launch` (fallback dataset public).
- `kaggle CLI not found`
  - Reinstaller les dependances: `make install` ou `uv sync --all-extras`.
- `Fichier introuvable: data/raw/...`
  - CSV absents: relancer `make download` ou `make launch-force`.
- Base SQLite absente pour les tests d'integration
  - Executer d'abord `make etl`, puis `make test-integration`.
- `Address already in use` / port occupe
  - Changer le port: `uv run python launch.py --port 8888` ou `DASHBOARD_PORT=8888 make dashboard`.
- Splash screen ne s'affiche pas
  - En headless/WSL sans `DISPLAY`, utiliser `--no-splash`.
- Le navigateur ne s'ouvre pas automatiquement
  - Ouvrir l'URL manuellement, ou forcer `DASHBOARD_SHOW_BROWSER=1`.
- `PHASE X: ... failed: ...`
  - Le pipeline remonte maintenant l'etape en echec (extract/transform/build/load). Lire les logs juste au-dessus.
