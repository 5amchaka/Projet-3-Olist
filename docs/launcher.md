# Launcher Automatise - Documentation Technique

## Vue d'ensemble

Le launcher (`launch.py`) orchestre le cycle complet:

1. verification de l'environnement
2. telechargement des CSV si necessaire
3. execution ETL si necessaire
4. validation de la base
5. lancement du dashboard

Il expose deux modes d'interface:

- mode CLI (terminal)
- mode splash WebSocket (page web temporaire sur `http://localhost:8079`)

## Architecture

### Fichiers

```text
launch.py
src/launcher/
├── orchestrator.py        # orchestration des phases
├── ui.py                  # rendu CLI et adaptateur UI
├── config_manager.py      # chargement .env + permissions
├── healthcheck.py         # diagnostics systeme
├── downloader.py          # telechargement Kaggle + manifest
├── logger_adapter.py      # bridge logs ETL -> UI
├── browser_opener.py      # ouverture navigateur (Linux/WSL/Windows)
└── splash/                # serveur splash + events + health check
```

### Comportement reel de configuration

- `.env` est **optionnel**.
- si `KAGGLE_USERNAME` / `KAGGLE_KEY` sont absents, le downloader injecte des credentials par defaut (`anonymous`) pour le dataset public Olist.
- le launcher ne cree pas `.env` de facon interactive.

## Flux d'execution

Phases executees par `OlistOrchestrator`:

1. `Configuration & Validation`
2. `Pre-flight Health Check`
3. `Downloading CSV Files` (conditionnelle)
4. `ETL Pipeline` (conditionnelle)
5. `Post-ETL Validation` ou `Database Validation`
6. `Launching Dashboard`

Phases optionnelles selon flags:

- `CSV Verification (csvkit)` via `--verify-csv`
- `Running Unit Tests` via `--run-tests`
- `Running All Tests` via `--run-all-tests`

## Logique de skip

- Download:
  - force avec `--force`
  - sinon skip si les 9 CSV sont deja presents dans `data/raw/`
- ETL:
  - force avec `--force`
  - skip si `--skip-etl` et DB existante
  - sinon execution auto si DB absente ou si CSV plus recents que `olist_dw.db`

## Options CLI

Options disponibles (`uv run python launch.py --help`):

```bash
--force
--skip-etl
--skip-download
-v, --verbose
-q, --quiet
--port INTEGER
--no-browser
--no-splash
--theme [matrix|simplon]
--run-tests
--run-all-tests
--verify-csv
--health-check-only
```

### Exemples

```bash
# lancement standard
uv run python launch.py --theme simplon

# rebuild complet
uv run python launch.py --theme simplon --force

# mode rapide
uv run python launch.py --theme simplon --skip-download --skip-etl

# diagnostic uniquement
uv run python launch.py --health-check-only

# sans splash (mode CLI)
uv run python launch.py --no-splash

# avec verification + tests
uv run python launch.py --verify-csv --run-tests
```

## Cibles Makefile

```bash
make launch
make launch-force
make launch-quick
make launch-with-tests
make launch-with-all-tests
make launch-with-verify
make health
```

## Variables d'environnement

Variables utiles:

```bash
DASHBOARD_PORT=8080
DASHBOARD_SHOW_BROWSER=1
KAGGLE_USERNAME=...
KAGGLE_KEY=...
```

Notes:

- `DASHBOARD_SHOW_BROWSER` est `false` par defaut dans `src/dashboard/main.py`.
- `--port` force le port au moment du lancement.
- en mode splash, le launcher demarre toujours le splash sur `8079`.

## Verification rapide de la doc

Commandes utilisees pour valider cette documentation:

```bash
make help
uv run python launch.py --help
```

## Points d'attention

- `healthcheck.py` verifie la presence de: `pandas`, `sqlalchemy`, `nicegui`, `click`, `colorama`, `dotenv`, `kaggle`.
- pour un lancement fluide, installer les extras dashboard/dev selon besoin (`uv sync --all-extras` recommande pour le mode launcher complet).
