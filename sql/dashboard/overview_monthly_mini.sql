-- =============================================================================
-- overview_monthly_mini.sql
-- Sparkline mensuelle : revenue par mois (commandes livrees)
-- =============================================================================
-- Retourne une ligne par mois avec le chiffre d'affaires mensuel.
-- Utilise pour la sparkline (area chart) de la page Vue d'ensemble.
--
-- Concepts SQL :
-- - JOIN entre fact_orders et dim_dates pour acceder aux colonnes temporelles
-- - GROUP BY sur des expressions (year, month) pour agreger par mois
-- - Filtrage WHERE sur order_status pour ne garder que les livrees
-- - ORDER BY pour un tri chronologique
-- =============================================================================

SELECT
    d.year,
    d.month,
    d.year || '-' || PRINTF('%02d', d.month) AS month_label,
    ROUND(SUM(f.price), 2) AS monthly_revenue
FROM fact_orders f
JOIN dim_dates d ON f.date_key = d.date_key
WHERE f.order_status = 'delivered'
GROUP BY d.year, d.month
ORDER BY d.year, d.month;
