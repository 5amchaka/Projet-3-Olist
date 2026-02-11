-- =============================================================================
-- ltv_cohorts.sql
-- Lifetime Value (LTV) par cohorte
-- =============================================================================
-- Retourne une ligne par (cohorte, mois depuis premier achat) avec :
--   - cohort_month       : mois de la cohorte (format AAAAMM)
--   - months_since_first : nombre de mois ecoules depuis la premiere commande
--   - nb_customers       : nombre de clients actifs
--   - cohort_revenue     : revenu genere par la cohorte ce mois
--   - cumulative_revenue : revenu cumule depuis le mois 0
--   - ltv_per_customer   : LTV par client (revenu cumule / taille cohorte mois 0)
--
-- Concepts SQL utilises :
-- -----------------------------------------------------------------------
-- 1. VUE (v_customer_cohorts)
--    Encapsule le mois de premiere commande par client unique.
--    Remplace la CTE first_purchase repetee dans plusieurs requetes.
--
-- 2. CTEs MULTI-NIVEAUX (3 CTEs)
--    Decomposition du calcul complexe en etapes lisibles.
--
-- 3. SUM() OVER (PARTITION BY ... ORDER BY ...) — Cumul par cohorte
--    Calcule le revenu cumule par cohorte en utilisant une fenetre
--    ordonnee par le delta en mois, partitionnee par cohorte.
--
-- 4. Sous-requete correlee pour la taille de cohorte
--    Recupere le nombre de clients au mois 0 pour calculer la LTV.
--
-- 5. Calcul delta mois a partir d'entiers AAAAMM
--    Meme technique que cohorts_retention.sql.
-- =============================================================================

-- CTE 1 : Les 12 premieres cohortes
WITH eligible_cohorts AS (
    SELECT DISTINCT first_month AS cohort_month
    FROM v_customer_cohorts
    ORDER BY first_month
    LIMIT 12
),

-- CTE 2 : Revenu par client par mois (restreint aux cohortes eligibles)
orders_monthly AS (
    SELECT
        c.customer_unique_id,
        vc.first_month AS cohort_month,
        f.date_key / 100 AS order_month,
        SUM(f.price) AS revenue
    FROM fact_orders f
    JOIN dim_customers c ON f.customer_key = c.customer_key
    JOIN v_customer_cohorts vc ON vc.customer_unique_id = c.customer_unique_id
    JOIN eligible_cohorts ec ON vc.first_month = ec.cohort_month
    WHERE f.order_status = 'delivered'
      AND f.date_key IS NOT NULL
    GROUP BY c.customer_unique_id, vc.first_month, f.date_key / 100
),

-- CTE 3 : Agregation par cohorte et delta mois
cohort_ltv AS (
    SELECT
        cohort_month,
        (order_month / 100 * 12 + order_month % 100)
        - (cohort_month / 100 * 12 + cohort_month % 100)
        AS months_since_first,
        COUNT(DISTINCT customer_unique_id) AS nb_customers,
        ROUND(SUM(revenue), 2) AS cohort_revenue
    FROM orders_monthly
    GROUP BY cohort_month, months_since_first
)

-- Resultat final : ajout du cumul et du LTV par client
SELECT
    cl.cohort_month,
    cl.months_since_first,
    cl.nb_customers,
    cl.cohort_revenue,
    ROUND(
        SUM(cl.cohort_revenue) OVER (
            PARTITION BY cl.cohort_month
            ORDER BY cl.months_since_first
            ROWS UNBOUNDED PRECEDING
        ),
        2
    ) AS cumulative_revenue,
    ROUND(
        SUM(cl.cohort_revenue) OVER (
            PARTITION BY cl.cohort_month
            ORDER BY cl.months_since_first
            ROWS UNBOUNDED PRECEDING
        )
        * 1.0
        / NULLIF(
            (SELECT cl0.nb_customers
             FROM cohort_ltv cl0
             WHERE cl0.cohort_month = cl.cohort_month
               AND cl0.months_since_first = 0),
            0
        ),
        2
    ) AS ltv_per_customer
FROM cohort_ltv cl
WHERE cl.months_since_first BETWEEN 0 AND 11
ORDER BY cl.cohort_month, cl.months_since_first;
