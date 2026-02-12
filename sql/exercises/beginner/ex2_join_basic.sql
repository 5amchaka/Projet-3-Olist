-- Exercice Beginner 2 : Top 5 catégories par CA
-- Solution de référence

SELECT
    COALESCE(p.category_name_en, p.category_name_pt, 'Unknown') as category,
    SUM(o.price) as total_revenue
FROM fact_orders o
INNER JOIN dim_products p ON o.product_key = p.product_key
WHERE o.order_status = 'delivered'
GROUP BY category
ORDER BY total_revenue DESC
LIMIT 5
