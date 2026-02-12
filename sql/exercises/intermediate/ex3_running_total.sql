-- Exercice Intermediate 3 : Running total mensuel du CA
-- Solution de référence

SELECT
    month_label as month,
    monthly_revenue,
    SUM(monthly_revenue) OVER (ORDER BY year, month ROWS UNBOUNDED PRECEDING) as cumulative_revenue
FROM v_monthly_sales
ORDER BY year, month
