# SQL Dashboard — Requetes analytiques

Requetes SQL utilisees par le dashboard **Olist SQL Explorer** (`src/dashboard/`).
Chaque fichier est autonome, commente en francais, et executable directement sur le DWH SQLite (`data/database/olist_dw.db`).

## Schema cible

Schema en etoile defini dans `sql/create_star_schema.sql` :

- **`fact_orders`** — table de faits (grain = article de commande, ~112k lignes)
- **`dim_dates`** — dimension temporelle (`date_key` au format AAAAMMJJ)
- **`dim_customers`** — clients (`customer_unique_id` pour deduplication)
- **`dim_sellers`** — vendeurs
- **`dim_products`** — produits et categories
- **`dim_geolocation`** — geolocalisation (zip, ville, etat)

## Fichiers

| Fichier | Page | Concepts SQL |
|---------|------|-------------|
| `overview_kpis.sql` | Vue d'ensemble | `COUNT(DISTINCT CASE WHEN)`, `SUM`, `AVG`, `ROUND`, `NULLIF` |
| `overview_monthly_mini.sql` | Vue d'ensemble | `JOIN`, `GROUP BY`, `PRINTF`, `ORDER BY` |
| `trends_monthly.sql` | Tendances | `LAG()`, `SUM() OVER` (running total), `NULLIF` |
| `rfm_segmentation.sql` | Segmentation RFM | CTEs multi-niveaux, `NTILE(5)`, `JULIANDAY()`, `CASE WHEN` classification |
| `pareto_sellers.sql` | Pareto vendeurs | `ROW_NUMBER()`, `PERCENT_RANK()`, `SUM() OVER (ROWS UNBOUNDED PRECEDING)` |
| `cohorts_retention.sql` | Cohortes | CTEs, calcul delta mois (AAAAMM), `COUNT(DISTINCT)`, self-join |
| `seller_scoring.sql` | Scoring vendeurs | `NTILE()`, `RANK()`, `DENSE_RANK()`, scoring multi-criteres |
| `top_products.sql` | Ventes | CTE, `ROW_NUMBER() OVER`, `COALESCE`, `LIMIT`, JOIN `dim_products` |
| `ca_yoy.sql` | Ventes | CTE, `LAG() OVER` (Year-over-Year), `NULLIF`, comparaison annuelle |
| `basket_avg.sql` | Ventes | reutilisation de `v_monthly_sales`, projection des colonnes utiles |
| `new_vs_recurring.sql` | Clients | CTEs multi-niveaux, `MIN()`, `CASE WHEN` classification nouveau/recurrent |
| `ltv_cohorts.sql` | Clients | 3 CTEs, `SUM() OVER (PARTITION BY)`, sous-requete correlee, LTV cumulative |

## Fichiers SQL complementaires (hors dashboard)

| Fichier | Description |
|---------|-------------|
| `sql/views.sql` | 3 vues SQL reutilisables : `v_monthly_sales`, `v_customer_cohorts`, `v_orders_enriched` |
| `sql/explain_analysis.sql` | Analyse `EXPLAIN QUERY PLAN` sur 4 requetes cles + synthese des index |
| `sql/dashboard/payment_gap_analysis.sql` | Investigation ponctuelle sur les ecarts paiements/facturation (non utilisee par l'UI du dashboard) |

## Utilisation standalone

```bash
# Executer une requete directement
sqlite3 -header -column data/database/olist_dw.db < sql/dashboard/overview_kpis.sql

# Ou via Python
python -c "
import sqlite3, pandas as pd
conn = sqlite3.connect('data/database/olist_dw.db')
df = pd.read_sql_query(open('sql/dashboard/rfm_segmentation.sql').read(), conn)
print(df)
"

# Creer les vues SQL
sqlite3 data/database/olist_dw.db < sql/views.sql

# Analyser les plans d'execution
sqlite3 data/database/olist_dw.db < sql/explain_analysis.sql
```

## Concepts SQL couverts

### Fonctions d'agregation
- `COUNT`, `SUM`, `AVG`, `ROUND`
- `COUNT(DISTINCT ...)` — comptage de valeurs uniques
- `COUNT(DISTINCT CASE WHEN ...)` — comptage conditionnel

### Fonctions de fenetrage (Window Functions)
- `LAG(col, n) OVER (ORDER BY ...)` — acces a la ligne precedente
- `SUM() OVER (ORDER BY ... ROWS UNBOUNDED PRECEDING)` — cumul glissant
- `SUM() OVER (PARTITION BY ... ORDER BY ...)` — cumul partitionne (LTV)
- `NTILE(n) OVER (ORDER BY ...)` — decoupage en quantiles
- `ROW_NUMBER() OVER (ORDER BY ...)` — rang unique
- `RANK() / DENSE_RANK() OVER (ORDER BY ...)` — rang avec/sans sauts

### CTEs (Common Table Expressions)
- CTE simple : `WITH cte AS (...) SELECT ...`
- CTEs enchainees : `WITH cte1 AS (...), cte2 AS (...) SELECT ...`
- Jusqu'a 3 CTEs dans `rfm_segmentation.sql`, `cohorts_retention.sql` et `ltv_cohorts.sql`

### Vues SQL (CREATE VIEW)
- `CREATE VIEW ... AS SELECT ...` — encapsulation de requetes reutilisables
- `DROP VIEW IF EXISTS` — idempotence
- 3 vues definies dans `sql/views.sql`

### Performance (EXPLAIN QUERY PLAN)
- `EXPLAIN QUERY PLAN` — analyse du plan d'execution SQLite
- Identification des `SCAN` (full table scan) vs `SEARCH USING INDEX`
- `AUTOMATIC COVERING INDEX` — index temporaires crees par SQLite
- `BLOOM FILTER` — filtre probabiliste pour jointures (SQLite 3.38+)
- Documentation dans `sql/explain_analysis.sql`

### Autres
- `CASE WHEN ... THEN ... ELSE ... END` — logique conditionnelle
- `COALESCE(a, b, c)` — premiere valeur non-NULL
- `NULLIF(val, 0)` — protection division par zero
- `JULIANDAY()` — calcul d'ecarts en jours (SQLite)
- Sous-requetes scalaires dans `SELECT` et `WHERE`
- Sous-requetes correlees (LTV par cohorte)
