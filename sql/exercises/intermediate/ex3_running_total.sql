-- Exercice Intermediate 3 : Running total mensuel du CA
-- Solution de référence

SELECT
    order_month as month,
    monthly_revenue,
    SUM(monthly_revenue) OVER (ORDER BY order_month ROWS UNBOUNDED PRECEDING) as cumulative_revenue
FROM v_monthly_sales
ORDER BY order_month
