-- Exercice Advanced 1 : Top 10 produits avec % du total (2 CTEs)
-- Solution de référence

WITH total_revenue AS (
    SELECT SUM(price) as total
    FROM fact_orders
),
product_revenue AS (
    SELECT
        p.product_id,
        SUM(f.price) as revenue
    FROM fact_orders f
    INNER JOIN dim_products p ON f.product_key = p.product_key
    WHERE f.order_status = 'delivered'
    GROUP BY p.product_id
)
SELECT
    product_id,
    revenue,
    (revenue * 100.0 / total) as pct_of_total
FROM product_revenue, total_revenue
ORDER BY revenue DESC
LIMIT 10
