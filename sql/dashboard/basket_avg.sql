-- =============================================================================
-- basket_avg.sql
-- Panier moyen mensuel
-- =============================================================================
-- Retourne une ligne par mois avec :
--   - month_label     : mois au format AAAA-MM
--   - monthly_revenue : CA mensuel
--   - monthly_orders  : nombre de commandes distinctes
--   - avg_basket      : panier moyen (CA / nombre de commandes)
--
-- Concepts SQL utilises :
-- -----------------------------------------------------------------------
-- 1. VUE (v_monthly_sales)
--    La vue pre-calcule les metriques mensuelles (CA, commandes, panier).
--    Elle encapsule le JOIN fact_orders <-> dim_dates et le GROUP BY,
--    evitant de repeter cette logique dans chaque requete.
--
-- 2. Reutilisabilite
--    Meme base que trends_monthly.sql et ca_yoy.sql, mais chaque
--    requete selectionne les colonnes et calculs dont elle a besoin.
-- =============================================================================

SELECT
    month_label,
    monthly_revenue,
    monthly_orders,
    avg_basket
FROM v_monthly_sales
ORDER BY year, month;
