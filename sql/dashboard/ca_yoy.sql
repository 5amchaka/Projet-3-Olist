-- =============================================================================
-- ca_yoy.sql
-- Evolution du chiffre d'affaires annee sur annee (Year-over-Year)
-- =============================================================================
-- Retourne une ligne par annee avec :
--   - year             : annee
--   - annual_revenue   : CA annuel (commandes livrees)
--   - annual_orders    : nombre de commandes distinctes livrees
--   - prev_revenue     : CA de l'annee precedente
--   - yoy_growth_pct   : taux de croissance annuel (%)
--
-- Concepts SQL utilises :
-- -----------------------------------------------------------------------
-- 1. VUE + CTE
--    La vue v_monthly_sales fournit les metriques mensuelles. La CTE
--    `annual` les agrege par annee avant d'appliquer les window functions.
--
-- 2. LAG() OVER (ORDER BY ...)
--    Fonction de fenetrage qui accede a la valeur de la ligne precedente.
--    Ici, elle recupere le CA de l'annee N-1 pour calculer la croissance.
--
-- 3. NULLIF — Protection contre la division par zero
--
-- 4. ROUND — Formatage du pourcentage de croissance
-- =============================================================================

WITH annual AS (
    SELECT
        year,
        ROUND(SUM(monthly_revenue), 2) AS annual_revenue,
        SUM(monthly_orders)            AS annual_orders
    FROM v_monthly_sales
    GROUP BY year
)

SELECT
    year,
    annual_revenue,
    annual_orders,
    LAG(annual_revenue) OVER (ORDER BY year) AS prev_revenue,
    ROUND(
        (annual_revenue - LAG(annual_revenue) OVER (ORDER BY year))
        * 100.0
        / NULLIF(LAG(annual_revenue) OVER (ORDER BY year), 0),
        1
    ) AS yoy_growth_pct
FROM annual
ORDER BY year;
