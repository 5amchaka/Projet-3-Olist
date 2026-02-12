-- Exercice Intermediate 1 : Variation YoY du CA mensuel avec LAG
-- Solution de référence

SELECT
    year,
    month,
    monthly_revenue as revenue,
    LAG(monthly_revenue, 12) OVER (ORDER BY year, month) as revenue_previous_year,
    (monthly_revenue - LAG(monthly_revenue, 12) OVER (ORDER BY year, month)) /
        NULLIF(LAG(monthly_revenue, 12) OVER (ORDER BY year, month), 0) * 100 as yoy_growth_pct
FROM v_monthly_sales
ORDER BY year, month
