-- Exercice Advanced 1 : Top 10 produits avec % du total (2 CTEs)
-- Solution de référence

WITH total_revenue AS (
    SELECT SUM(price) as total
    FROM fact_orders
),
product_revenue AS (
    SELECT
        product_id,
        SUM(price) as revenue
    FROM fact_orders
    GROUP BY product_id
)
SELECT
    product_id,
    revenue,
    (revenue * 100.0 / total) as pct_of_total
FROM product_revenue, total_revenue
ORDER BY revenue DESC
LIMIT 10
