-- Exercice Intermediate 1 : Variation YoY du CA mensuel avec LAG
-- Solution de référence

SELECT
    CAST(SUBSTR(order_month, 1, 4) AS INTEGER) as year,
    CAST(SUBSTR(order_month, 6, 2) AS INTEGER) as month,
    monthly_revenue as revenue,
    LAG(monthly_revenue, 12) OVER (ORDER BY order_month) as revenue_previous_year,
    (monthly_revenue - LAG(monthly_revenue, 12) OVER (ORDER BY order_month)) /
        NULLIF(LAG(monthly_revenue, 12) OVER (ORDER BY order_month), 0) * 100 as yoy_growth_pct
FROM v_monthly_sales
ORDER BY order_month
