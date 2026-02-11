-- =============================================================================
-- top_products.sql
-- Top 10 produits par chiffre d'affaires
-- =============================================================================
-- Retourne les 10 categories de produits generant le plus de CA, avec :
--   - product_rank     : rang du produit (par CA decroissant)
--   - category_name    : nom de la categorie (anglais)
--   - total_revenue    : chiffre d'affaires total de la categorie
--   - nb_orders        : nombre de commandes distinctes
--   - avg_price        : prix moyen par article
--
-- Concepts SQL utilises :
-- -----------------------------------------------------------------------
-- 1. VUE (v_orders_enriched)
--    Vue denormalisee joignant fact_orders avec toutes les dimensions.
--    Le COALESCE sur la categorie produit et les JOINs multiples sont
--    encapsules une seule fois dans la vue.
--
-- 2. CTE (Common Table Expression) — WITH ... AS (...)
--    Agregation du CA par categorie dans une CTE dediee.
--
-- 3. ROW_NUMBER() OVER (ORDER BY ...)
--    Attribue un rang unique a chaque categorie, par CA decroissant.
--    Contrairement a RANK(), ROW_NUMBER() ne produit jamais d'ex-aequo.
--
-- 4. LIMIT — Restriction du resultat aux N premieres lignes
-- =============================================================================

WITH category_revenue AS (
    SELECT
        product_category                   AS category_name,
        ROUND(SUM(price), 2)               AS total_revenue,
        COUNT(DISTINCT order_id)           AS nb_orders,
        ROUND(AVG(price), 2)               AS avg_price
    FROM v_orders_enriched
    WHERE order_status = 'delivered'
    GROUP BY product_category
)

SELECT
    ROW_NUMBER() OVER (ORDER BY total_revenue DESC) AS product_rank,
    category_name,
    total_revenue,
    nb_orders,
    avg_price
FROM category_revenue
ORDER BY total_revenue DESC
LIMIT 10;
