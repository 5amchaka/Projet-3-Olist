# Olist ETL Pipeline

Pipeline ETL pour le dataset Brazilian E-commerce (Olist) : ~100k commandes 2016-2018.

Telecharge les 9 CSV depuis Kaggle, nettoie les donnees, et les charge dans un data warehouse SQLite (star schema).

## Quickstart

> **Alternative interactive** : ouvrir [notebooks/quickstart.ipynb](notebooks/quickstart.ipynb) pour un demarrage guide cellule par cellule.

### 1. Installation

```bash
uv venv && uv sync
```

### 2. Configuration Kaggle

Copier `.env.example` en `.env` et renseigner les credentials :

```bash
cp .env.example .env
# Editer .env avec votre KAGGLE_USERNAME et KAGGLE_KEY
```

### 3. Telecharger les donnees

```bash
bash scripts/download_dataset.sh
```

### 4. Lancer le pipeline ETL

```bash
uv run python -m src.etl
```

La base SQLite sera creee dans `data/database/olist_dw.db`.

### 5. Tests

```bash
uv run python -m pytest tests/ -v
```

## Structure

```
data/raw/           # CSV bruts depuis Kaggle
data/processed/     # Donnees intermediaires
data/staging/       # Staging
data/database/      # Fichier SQLite (data warehouse)
src/etl/            # Pipeline ETL (extract, transform, load)
src/database/       # Connexion et modeles
sql/                # DDL + requetes SQL
scripts/            # Scripts utilitaires (download, etc.)
notebooks/          # Exploration, nettoyage, chargement, verification
tests/              # Tests unitaires et d'integration
docs/               # Documentation du schema
```

## Documentation

| Document | Contenu |
|----------|---------|
| [docs/csv_to_star_schema.md](docs/csv_to_star_schema.md) | Choix de modelisation : pourquoi et comment les 9 CSV deviennent 6 tables |
| [docs/exploration_analysis.md](docs/exploration_analysis.md) | Analyse empirique des donnees brutes : chiffres cles, constats, justifications |
| [notebooks/quickstart.ipynb](notebooks/quickstart.ipynb) | Demarrage rapide : telecharger, lancer le pipeline, verifier la base |
| [notebooks/exploration_csv.ipynb](notebooks/exploration_csv.ipynb) | Notebook d'exploration : profils, cardinalites, visualisations par dataset |
| [notebooks/comparaison_csv_bdd.ipynb](notebooks/comparaison_csv_bdd.ipynb) | Tracabilite CSV → BDD : volumetrie, distributions avant/apres, perdu/gagne |

## Star Schema

Le data warehouse utilise un schema en etoile :
- **5 dimensions** : dates, geolocation, customers, sellers, products
- **1 table de faits** : fact_orders (grain = article commande)

Voir [docs/csv_to_star_schema.md](docs/csv_to_star_schema.md) pour le detail et [docs/exploration_analysis.md](docs/exploration_analysis.md) pour les constats empiriques qui motivent ces choix.

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
| category_translation | 71 | Traduction des categories PT->EN |
