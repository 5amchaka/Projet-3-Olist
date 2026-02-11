-- =============================================================================
-- cohorts_retention.sql
-- Analyse de cohortes et retention client
-- =============================================================================
-- Une cohorte est un groupe de clients defini par leur mois de premiere
-- commande. L'analyse de retention mesure combien de clients de chaque
-- cohorte reviennent acheter dans les mois suivants.
--
-- Resultat : une ligne par (cohorte, mois depuis premier achat) avec :
--   - cohort_month       : mois de la cohorte (format AAAAMM, ex: 201701)
--   - months_since_first : nombre de mois ecoules depuis la premiere commande
--   - nb_customers       : nombre de clients uniques actifs ce mois-la
--
-- Concepts SQL utilises :
-- -----------------------------------------------------------------------
-- 1. VUE (v_customer_cohorts)
--    Encapsule le calcul du mois de premiere commande par client unique.
--    Remplace la CTE first_purchase repetee dans plusieurs requetes.
--
-- 2. CTEs MULTI-NIVEAUX
--    Trois CTEs enchainees decomposent le calcul complexe en etapes :
--    eligible_cohorts -> orders_monthly -> cohort_activity.
--
-- 3. Calcul de delta en mois a partir d'un entier AAAAMM
--    Le format AAAAMM (ex: 201708) ne peut pas etre soustrait directement
--    pour obtenir un nombre de mois (201802 - 201712 = 90, pas 2 mois).
--    On convertit d'abord en nombre absolu de mois : (AAAA * 12 + MM).
--    Ainsi, la difference donne bien le nombre de mois ecoules.
--
-- 4. COUNT(DISTINCT ...) pour la retention
--    On compte les clients uniques actifs a chaque delta temporel.
-- =============================================================================

-- CTE 1 : Les 12 premieres cohortes (pre-calculees pour performance)
WITH eligible_cohorts AS (
    SELECT DISTINCT first_month AS cohort_month
    FROM v_customer_cohorts
    ORDER BY first_month
    LIMIT 12
),

-- CTE 2 : Chaque commande avec son mois — restreint aux clients des cohortes eligibles
orders_monthly AS (
    SELECT DISTINCT
        c.customer_unique_id,
        f.date_key / 100 AS order_month
    FROM fact_orders f
    JOIN dim_customers c ON f.customer_key = c.customer_key
    JOIN v_customer_cohorts vc ON vc.customer_unique_id = c.customer_unique_id
    JOIN eligible_cohorts ec ON vc.first_month = ec.cohort_month
    WHERE f.order_status = 'delivered'
      AND f.date_key IS NOT NULL
),

-- CTE 3 : Jointure cohorte <-> activite mensuelle + calcul delta
cohort_activity AS (
    SELECT
        vc.first_month AS cohort_month,
        -- Calcul du delta en mois :
        -- AAAAMM -> nombre absolu de mois (annee * 12 + mois), puis difference
        (om.order_month / 100 * 12 + om.order_month % 100)
        - (vc.first_month / 100 * 12 + vc.first_month % 100)
        AS months_since_first,
        om.customer_unique_id
    FROM v_customer_cohorts vc
    JOIN orders_monthly om ON vc.customer_unique_id = om.customer_unique_id
    JOIN eligible_cohorts ec ON vc.first_month = ec.cohort_month
)

-- Resultat final : agregation par cohorte et delta
SELECT
    cohort_month,
    months_since_first,
    COUNT(DISTINCT customer_unique_id) AS nb_customers
FROM cohort_activity
WHERE months_since_first BETWEEN 0 AND 11
GROUP BY cohort_month, months_since_first
ORDER BY cohort_month, months_since_first;
