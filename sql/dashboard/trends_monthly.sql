-- =============================================================================
-- trends_monthly.sql
-- Tendances mensuelles : revenue, commandes, croissance et cumul
-- =============================================================================
-- Retourne une ligne par mois avec :
--   - monthly_revenue  : CA mensuel (commandes livrees)
--   - monthly_orders   : nombre de commandes distinctes livrees
--   - growth_pct       : variation en % par rapport au mois precedent
--   - running_total    : cumul du CA depuis le debut
--
-- Concepts SQL :
-- -----------------------------------------------------------------------
-- 1. VUE (v_monthly_sales)
--    La vue encapsule le JOIN fact_orders <-> dim_dates et le GROUP BY
--    mensuel. Elle pre-calcule CA, commandes et panier moyen.
--    Reutilisee dans basket_avg.sql et ca_yoy.sql.
--
-- 2. Fonctions de fenetre (Window Functions) — OVER (ORDER BY ...)
--    LAG() accede a la ligne precedente pour calculer la croissance.
--    SUM() OVER (ORDER BY ...) calcule un cumul glissant (running total).
--
-- 3. ROUND et NULLIF pour eviter la division par zero
-- =============================================================================

SELECT
    month_label,
    monthly_revenue,
    monthly_orders,
    ROUND(
        (monthly_revenue - LAG(monthly_revenue) OVER (ORDER BY year, month))
        * 100.0
        / NULLIF(LAG(monthly_revenue) OVER (ORDER BY year, month), 0),
        1
    ) AS growth_pct,
    ROUND(
        SUM(monthly_revenue) OVER (ORDER BY year, month),
        2
    ) AS running_total
FROM v_monthly_sales
ORDER BY year, month;
