-- Exercice Intermediate 2 : Quintiles clients par montant total
-- Solution de référence

WITH customer_totals AS (
    SELECT
        c.customer_unique_id as customer_id,
        SUM(f.price) as total_spent
    FROM fact_orders f
    INNER JOIN dim_customers c ON f.customer_key = c.customer_key
    WHERE f.order_status = 'delivered'
    GROUP BY c.customer_unique_id
)
SELECT
    customer_id,
    total_spent,
    NTILE(5) OVER (ORDER BY total_spent DESC) as quintile
FROM customer_totals
ORDER BY total_spent DESC
