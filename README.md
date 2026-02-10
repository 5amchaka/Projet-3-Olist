# Olist ETL Pipeline

Pipeline ETL pour le dataset Brazilian E-commerce (Olist) : ~100k commandes 2016-2018.

Telecharge les 9 CSV depuis Kaggle, nettoie les donnees, et les charge dans un data warehouse SQLite (star schema).

## Quickstart

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
.venv/bin/python -m src.etl.pipeline
```

La base SQLite sera creee dans `data/database/olist_dw.db`.

### 5. Tests

```bash
.venv/bin/python -m pytest tests/ -v
```

## Structure

```
data/raw/           # CSV bruts depuis Kaggle
data/database/      # Fichier SQLite (data warehouse)
src/etl/            # Pipeline ETL (extract, transform, load)
src/database/       # Connexion et modeles
sql/                # DDL + requetes SQL
notebooks/          # Exploration, nettoyage, chargement, verification
tests/              # Tests unitaires
docs/               # Documentation du schema
```

## Star Schema

Le data warehouse utilise un schema en etoile :
- **5 dimensions** : dates, geolocation, customers, sellers, products
- **1 table de faits** : fact_orders (grain = article commande)

Voir [docs/csv_to_star_schema.md](docs/csv_to_star_schema.md) pour le detail.

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
