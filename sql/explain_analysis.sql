-- =============================================================================
-- explain_analysis.sql
-- Analyse des plans d'execution des requetes principales
-- =============================================================================
-- Ce fichier documente les plans d'execution (EXPLAIN QUERY PLAN) des requetes
-- cles du dashboard et analyse l'utilisation des index.
--
-- EXPLAIN QUERY PLAN est la commande SQLite equivalente de EXPLAIN dans
-- PostgreSQL/MySQL. Elle montre comment le moteur SQL prevoit d'executer
-- une requete : quels index sont utilises, quels scans sont effectues,
-- et comment les donnees sont triees ou groupees.
--
-- Terminologie :
--   SCAN table       = parcours complet (full table scan) — O(n)
--   SEARCH ... USING INDEX idx (col=?) = recherche indexee — O(log n)
--   AUTOMATIC COVERING INDEX = index temporaire cree par SQLite pour la requete
--   USE TEMP B-TREE  = tri temporaire en memoire (GROUP BY, ORDER BY, DISTINCT)
-- =============================================================================


-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║ 1. overview_kpis.sql — Agregation globale                              ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝
-- Requete : agregation sur toute la table fact_orders sans filtre WHERE
-- specifique (ou filtre sur order_status='delivered' via CASE WHEN).
--
-- Plan d'execution :
--   |--USE TEMP B-TREE FOR count(DISTINCT)
--   `--SCAN fact_orders
--
-- Analyse :
--   - SCAN fact_orders : parcours complet de la table (~112k lignes).
--     C'est NORMAL pour une requete KPI globale sans clause WHERE.
--     Aucun index ne peut optimiser une agregation sans filtre.
--   - TEMP B-TREE : arbre temporaire pour COUNT(DISTINCT order_id).
--
-- Verdict : ✅ Optimal — un full scan est inevitable pour des KPIs globaux.

EXPLAIN QUERY PLAN
SELECT
    COUNT(DISTINCT CASE WHEN order_status = 'delivered' THEN order_id ELSE NULL END),
    ROUND(SUM(CASE WHEN order_status = 'delivered' THEN price ELSE NULL END), 2),
    ROUND(AVG(review_score), 2),
    ROUND(AVG(CASE WHEN order_status = 'delivered' THEN delivery_days ELSE NULL END), 1)
FROM fact_orders;


-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║ 2. rfm_segmentation.sql — CTE multi-niveaux + NTILE                   ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝
-- Requete : 3 CTEs enchainees avec jointures fact_orders ↔ dim_customers
-- ↔ dim_dates, GROUP BY customer_unique_id, NTILE(5).
--
-- Plan d'execution :
--   |--CO-ROUTINE rfm_raw
--   |  |--SEARCH f USING INDEX idx_fact_order_status (order_status=?)
--   |  |--SEARCH c USING INTEGER PRIMARY KEY (rowid=?)
--   |  |--SEARCH d USING INTEGER PRIMARY KEY (rowid=?)
--   |  |--USE TEMP B-TREE FOR GROUP BY
--   |  |--SCALAR SUBQUERY 1
--   |  |  |--SEARCH f2 USING COVERING INDEX idx_fact_date_key
--   |  |  `--SEARCH d2 USING INTEGER PRIMARY KEY (rowid=?)
--   |  `--USE TEMP B-TREE FOR count(DISTINCT)
--   `--SCAN rfm_raw
--
-- Analyse :
--   - SEARCH f USING INDEX idx_fact_order_status : l'index sur order_status
--     filtre efficacement les commandes 'delivered' (~96k sur 112k).
--   - SEARCH c/d USING INTEGER PRIMARY KEY : jointures sur les dimensions
--     via cle primaire (O(log n)), tres rapide.
--   - SCALAR SUBQUERY : la sous-requete MAX(full_date) utilise
--     idx_fact_date_key comme COVERING INDEX (pas besoin de lire la table).
--   - TEMP B-TREE : necessaire pour GROUP BY et COUNT(DISTINCT).
--
-- Verdict : ✅ Bon — les index existants sont bien exploites.

EXPLAIN QUERY PLAN
WITH rfm_raw AS (
    SELECT c.customer_unique_id,
        CAST(JULIANDAY((SELECT MAX(d2.full_date) FROM fact_orders f2
             JOIN dim_dates d2 ON f2.date_key = d2.date_key))
            - JULIANDAY(MAX(d.full_date)) AS INTEGER) AS recency,
        COUNT(DISTINCT f.order_id) AS frequency,
        ROUND(SUM(f.price), 2) AS monetary
    FROM fact_orders f
    JOIN dim_customers c ON f.customer_key = c.customer_key
    JOIN dim_dates d ON f.date_key = d.date_key
    WHERE f.order_status = 'delivered'
    GROUP BY c.customer_unique_id
)
SELECT * FROM rfm_raw LIMIT 5;


-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║ 3. cohorts_retention.sql — 4 CTEs + jointures + delta mois             ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝
-- Requete : la plus complexe du dashboard, 4 CTEs enchainees,
-- auto-jointure sur customer_unique_id, calcul de delta temporel.
--
-- Plan d'execution :
--   |--MATERIALIZE first_purchase
--   |  |--SEARCH f USING INDEX idx_fact_order_status (order_status=?)
--   |  |--SEARCH c USING INTEGER PRIMARY KEY (rowid=?)
--   |  `--USE TEMP B-TREE FOR GROUP BY
--   |--MATERIALIZE orders_monthly
--   |  |--MATERIALIZE eligible_cohorts
--   |  |  |--SCAN first_purchase
--   |  |  `--USE TEMP B-TREE FOR DISTINCT
--   |  |--SEARCH f USING INDEX idx_fact_order_status (order_status=?)
--   |  |--SEARCH c USING INTEGER PRIMARY KEY (rowid=?)
--   |  |--SEARCH fp USING AUTOMATIC COVERING INDEX (customer_unique_id=?)
--   |  |--SCAN ec
--   |  `--USE TEMP B-TREE FOR DISTINCT
--   |--SCAN fp
--   |--SEARCH om USING AUTOMATIC COVERING INDEX (customer_unique_id=?)
--   |--BLOOM FILTER ON ec (cohort_month=?)
--   |--SEARCH ec USING AUTOMATIC COVERING INDEX (cohort_month=?)
--   |--USE TEMP B-TREE FOR GROUP BY
--   `--USE TEMP B-TREE FOR count(DISTINCT)
--
-- Analyse :
--   - MATERIALIZE : SQLite materialise les CTEs (les calcule une fois
--     et stocke le resultat en memoire). C'est efficace ici car
--     first_purchase est reutilise dans orders_monthly et la requete finale.
--   - AUTOMATIC COVERING INDEX (customer_unique_id=?) : SQLite cree un
--     index temporaire pour les jointures sur customer_unique_id dans les
--     CTEs materialisees. Un index permanent sur dim_customers(customer_unique_id)
--     existe deja (UNIQUE constraint), mais les CTEs sont des tables
--     temporaires en memoire.
--   - BLOOM FILTER : filtre probabiliste utilise pour accelerer la jointure
--     avec eligible_cohorts. Technique avancee de SQLite 3.38+.
--
-- Verdict : ✅ Bon — les index automatiques et le bloom filter optimisent
--   bien les jointures. La materialisation des CTEs evite les recalculs.

EXPLAIN QUERY PLAN
WITH first_purchase AS (
    SELECT c.customer_unique_id, MIN(f.date_key / 100) AS first_month
    FROM fact_orders f
    JOIN dim_customers c ON f.customer_key = c.customer_key
    WHERE f.order_status = 'delivered' AND f.date_key IS NOT NULL
    GROUP BY c.customer_unique_id
),
eligible_cohorts AS (
    SELECT DISTINCT first_month AS cohort_month FROM first_purchase
    ORDER BY first_month LIMIT 12
),
orders_monthly AS (
    SELECT DISTINCT c.customer_unique_id, f.date_key / 100 AS order_month
    FROM fact_orders f
    JOIN dim_customers c ON f.customer_key = c.customer_key
    JOIN first_purchase fp ON fp.customer_unique_id = c.customer_unique_id
    JOIN eligible_cohorts ec ON fp.first_month = ec.cohort_month
    WHERE f.order_status = 'delivered' AND f.date_key IS NOT NULL
),
cohort_activity AS (
    SELECT fp.first_month AS cohort_month,
        (om.order_month / 100 * 12 + om.order_month % 100)
        - (fp.first_month / 100 * 12 + fp.first_month % 100) AS months_since_first,
        om.customer_unique_id
    FROM first_purchase fp
    JOIN orders_monthly om ON fp.customer_unique_id = om.customer_unique_id
    JOIN eligible_cohorts ec ON fp.first_month = ec.cohort_month
)
SELECT cohort_month, months_since_first, COUNT(DISTINCT customer_unique_id) AS nb_customers
FROM cohort_activity WHERE months_since_first BETWEEN 0 AND 11
GROUP BY cohort_month, months_since_first
ORDER BY cohort_month, months_since_first;


-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║ 4. top_products.sql — CTE + ROW_NUMBER + JOIN dim_products             ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝
-- Plan d'execution :
--   |--CO-ROUTINE (subquery)
--   |  |--CO-ROUTINE category_revenue
--   |  |  |--SEARCH f USING INDEX idx_fact_order_status (order_status=?)
--   |  |  |--SEARCH p USING INTEGER PRIMARY KEY (rowid=?)
--   |  |  |--USE TEMP B-TREE FOR GROUP BY
--   |  |  `--USE TEMP B-TREE FOR count(DISTINCT)
--   |  |--SCAN category_revenue
--   |  `--USE TEMP B-TREE FOR ORDER BY
--   `--SCAN (subquery)
--
-- Analyse :
--   - idx_fact_order_status filtre les commandes delivered.
--   - Jointure dim_products via PRIMARY KEY (O(log n)).
--   - Le GROUP BY et ORDER BY necessitent des tris temporaires,
--     mais sur un nombre reduit de categories (~70).
--
-- Verdict : ✅ Optimal — l'index et les cles primaires sont bien utilises.

EXPLAIN QUERY PLAN
WITH category_revenue AS (
    SELECT COALESCE(p.category_name_en, p.category_name_pt, 'Unknown') AS category_name,
        ROUND(SUM(f.price), 2) AS total_revenue,
        COUNT(DISTINCT f.order_id) AS nb_orders,
        ROUND(AVG(f.price), 2) AS avg_price
    FROM fact_orders f
    JOIN dim_products p ON f.product_key = p.product_key
    WHERE f.order_status = 'delivered'
    GROUP BY COALESCE(p.category_name_en, p.category_name_pt, 'Unknown')
)
SELECT ROW_NUMBER() OVER (ORDER BY total_revenue DESC) AS product_rank,
    category_name, total_revenue, nb_orders, avg_price
FROM category_revenue ORDER BY total_revenue DESC LIMIT 10;


-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║ SYNTHESE DES INDEX                                                     ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝
--
-- Index existants sur fact_orders (definis dans create_star_schema.sql) :
--   idx_fact_order_id      ON fact_orders(order_id)
--   idx_fact_date_key      ON fact_orders(date_key)
--   idx_fact_customer_key  ON fact_orders(customer_key)
--   idx_fact_seller_key    ON fact_orders(seller_key)
--   idx_fact_product_key   ON fact_orders(product_key)
--   idx_fact_order_status  ON fact_orders(order_status)
--   idx_fact_customer_geo  ON fact_orders(customer_geo_key)
--   idx_fact_seller_geo    ON fact_orders(seller_geo_key)
--
-- Index automatiques (UNIQUE constraints) sur les dimensions :
--   sqlite_autoindex_dim_customers_1    (customer_id UNIQUE)
--   sqlite_autoindex_dim_sellers_1      (seller_id UNIQUE)
--   sqlite_autoindex_dim_products_1     (product_id UNIQUE)
--   sqlite_autoindex_dim_geolocation_1  (zip_code_prefix UNIQUE)
--   sqlite_autoindex_fact_orders_1      (order_id, order_item_id UNIQUE)
--
-- Conclusion :
--   Les index en place couvrent bien les requetes du dashboard :
--   - idx_fact_order_status est le plus utilise (filtre WHERE delivered)
--   - Les cles primaires des dimensions assurent des jointures O(log n)
--   - SQLite cree des AUTOMATIC COVERING INDEX pour les CTEs quand necessaire
--   - Aucun index supplementaire n'est requis pour les performances actuelles
--
-- Index supplementaires envisages mais non necessaires :
--   - dim_customers(customer_unique_id) : deja couvert par AUTOMATIC INDEX
--     dans les CTEs, et la colonne est utilisee principalement dans des
--     GROUP BY qui necessitent un tri de toute facon.
--   - dim_dates(year, month) : les jointures se font sur date_key (PK),
--     et year/month sont utilises dans des GROUP BY post-jointure.
-- =============================================================================
