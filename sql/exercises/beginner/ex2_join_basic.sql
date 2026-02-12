-- Exercice Beginner 2 : Top 5 catégories par CA
-- Solution de référence

SELECT
    p.category,
    SUM(o.price) as total_revenue
FROM fact_orders o
INNER JOIN dim_products p ON o.product_key = p.product_key
GROUP BY p.category
ORDER BY total_revenue DESC
LIMIT 5
