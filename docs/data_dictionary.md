# Data Dictionary (Olist DW)

Ce document reference les tables du data warehouse SQLite (`data/database/olist_dw.db`).

## dim_dates

Grain: 1 ligne par date (AAAAMMJJ).

| Colonne | Type SQLite | Description |
|---|---|---|
| date_key | INTEGER (PK) | Cle date au format `YYYYMMDD` |
| full_date | DATE | Date civile |
| year | INTEGER | Annee |
| quarter | INTEGER | Trimestre (1-4) |
| month | INTEGER | Mois (1-12) |
| day | INTEGER | Jour du mois |
| day_of_week | INTEGER | Jour de semaine (0=lundi) |
| day_name | TEXT | Nom du jour |
| is_weekend | INTEGER | 1 si samedi/dimanche, sinon 0 |

## dim_geolocation

Grain: 1 ligne par `zip_code_prefix` (5 chiffres CEP).

| Colonne | Type SQLite | Description |
|---|---|---|
| geo_key | INTEGER (PK) | Cle surrogate geographique |
| zip_code_prefix | TEXT (UNIQUE) | Prefixe code postal |
| lat | REAL | Latitude agregée (mediane) |
| lng | REAL | Longitude agregée (mediane) |
| city | TEXT | Ville dominante (mode) |
| state | TEXT | Etat dominant (mode) |

## dim_customers

Grain: 1 ligne par `customer_id`.

| Colonne | Type SQLite | Description |
|---|---|---|
| customer_key | INTEGER (PK) | Cle surrogate client |
| customer_id | TEXT (UNIQUE) | Identifiant client source |
| customer_unique_id | TEXT | Identifiant client "global" Olist |
| geo_key | INTEGER (FK) | Cle vers `dim_geolocation` |
| city | TEXT | Ville client normalisee |
| state | TEXT | Etat client normalise |

## dim_sellers

Grain: 1 ligne par `seller_id`.

| Colonne | Type SQLite | Description |
|---|---|---|
| seller_key | INTEGER (PK) | Cle surrogate vendeur |
| seller_id | TEXT (UNIQUE) | Identifiant vendeur source |
| geo_key | INTEGER (FK) | Cle vers `dim_geolocation` |
| city | TEXT | Ville vendeur normalisee |
| state | TEXT | Etat vendeur normalise |

## dim_products

Grain: 1 ligne par `product_id`.

| Colonne | Type SQLite | Description |
|---|---|---|
| product_key | INTEGER (PK) | Cle surrogate produit |
| product_id | TEXT (UNIQUE) | Identifiant produit source |
| category_name_pt | TEXT | Categorie en portugais |
| category_name_en | TEXT | Categorie en anglais |
| weight_g | REAL | Poids (g) |
| length_cm | REAL | Longueur (cm) |
| height_cm | REAL | Hauteur (cm) |
| width_cm | REAL | Largeur (cm) |
| photos_qty | INTEGER | Nombre de photos |

## fact_orders

Grain: 1 ligne par article de commande (`order_id`, `order_item_id`).

| Colonne | Type SQLite | Description |
|---|---|---|
| fact_key | INTEGER (PK) | Cle surrogate de la table de faits |
| order_id | TEXT | Identifiant commande source |
| order_item_id | INTEGER | Rang de l'article dans la commande |
| date_key | INTEGER (FK) | Cle vers `dim_dates` (date d'achat) |
| customer_key | INTEGER (FK) | Cle vers `dim_customers` |
| seller_key | INTEGER (FK) | Cle vers `dim_sellers` |
| product_key | INTEGER (FK) | Cle vers `dim_products` |
| customer_geo_key | INTEGER (FK) | Cle geo du client |
| seller_geo_key | INTEGER (FK) | Cle geo du vendeur |
| order_status | TEXT | Statut de commande |
| price | REAL | Prix de l'article |
| freight_value | REAL | Frais de livraison article |
| order_payment_total | REAL | Paiement total commande (semi-additif) |
| payment_type | TEXT | Type dominant de paiement commande |
| review_score | INTEGER | Score d'avis retenu (dernier review) |
| delivery_days | REAL | Delai achat -> livraison reelle |
| estimated_days | REAL | Delai achat -> livraison estimee |
| delivery_delta_days | REAL | `delivery_days - estimated_days` |

## Vues SQL

| Vue | Description |
|---|---|
| v_monthly_sales | CA, commandes et panier moyen par mois |
| v_customer_cohorts | Cohorte de 1er achat par client unique |
| v_orders_enriched | Fact denormalisee avec dimensions jointes |
