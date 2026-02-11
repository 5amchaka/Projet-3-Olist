-- =============================================================================
-- new_vs_recurring.sql
-- Nouveaux clients vs clients recurrents par mois
-- =============================================================================
-- Retourne une ligne par mois avec :
--   - month_label   : mois au format AAAA-MM
--   - new_customers : nombre de clients dont c'est le premier achat ce mois
--   - recurring     : nombre de clients ayant deja achete avant
--   - total         : nombre total de clients actifs ce mois
--   - new_pct       : pourcentage de nouveaux clients
--
-- Concepts SQL utilises :
-- -----------------------------------------------------------------------
-- 1. VUE (v_customer_cohorts)
--    Encapsule le calcul du mois de premiere commande par client.
--    Evite de repeter le MIN(date_key / 100) dans chaque requete.
--
-- 2. CTEs MULTI-NIVEAUX
--    Deux CTEs enchainees : order_months -> classified.
--
-- 3. CASE WHEN — Classification nouveau vs recurrent
--    Si le mois de la commande = mois de premiere commande, le client est
--    nouveau ; sinon il est recurrent.
--
-- 4. COUNT(DISTINCT CASE WHEN ...) — Comptage conditionnel
--    Evite les doublons quand un client passe plusieurs commandes le meme mois.
--
-- 5. Calcul de pourcentage avec protection NULLIF
-- =============================================================================

-- CTE 1 : Chaque client actif par mois, avec son mois de premiere commande
WITH order_months AS (
    SELECT DISTINCT
        c.customer_unique_id,
        f.date_key / 100 AS order_month,
        vc.first_month
    FROM fact_orders f
    JOIN dim_customers c ON f.customer_key = c.customer_key
    JOIN v_customer_cohorts vc ON vc.customer_unique_id = c.customer_unique_id
    WHERE f.order_status = 'delivered'
      AND f.date_key IS NOT NULL
),

-- CTE 2 : Classification de chaque client-mois
classified AS (
    SELECT
        order_month,
        customer_unique_id,
        CASE
            WHEN order_month = first_month THEN 'new'
            ELSE 'recurring'
        END AS customer_type
    FROM order_months
)

SELECT
    (order_month / 100) || '-' || PRINTF('%02d', order_month % 100) AS month_label,

    COUNT(DISTINCT CASE
        WHEN customer_type = 'new' THEN customer_unique_id
    END) AS new_customers,

    COUNT(DISTINCT CASE
        WHEN customer_type = 'recurring' THEN customer_unique_id
    END) AS recurring,

    COUNT(DISTINCT customer_unique_id) AS total,

    ROUND(
        COUNT(DISTINCT CASE WHEN customer_type = 'new' THEN customer_unique_id END)
        * 100.0
        / NULLIF(COUNT(DISTINCT customer_unique_id), 0),
        1
    ) AS new_pct

FROM classified
GROUP BY order_month
ORDER BY order_month;
