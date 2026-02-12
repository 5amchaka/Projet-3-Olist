-- Exercice Advanced 2 : Clients avec 2+ commandes
-- Solution de référence (méthode simple GROUP BY)

SELECT
    c.customer_unique_id as customer_id,
    COUNT(DISTINCT f.order_id) as nb_orders
FROM fact_orders f
INNER JOIN dim_customers c ON f.customer_key = c.customer_key
WHERE f.order_status = 'delivered'
GROUP BY c.customer_unique_id
HAVING COUNT(DISTINCT f.order_id) >= 2
ORDER BY nb_orders DESC
