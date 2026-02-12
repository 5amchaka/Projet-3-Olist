-- Exercice Beginner 3 : CA et nombre de commandes par état client
-- Solution de référence

SELECT
    c.state as state,
    SUM(o.price) as total_revenue,
    COUNT(DISTINCT o.order_id) as nb_orders
FROM fact_orders o
INNER JOIN dim_customers c ON o.customer_key = c.customer_key
GROUP BY c.state
ORDER BY total_revenue DESC
