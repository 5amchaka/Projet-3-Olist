-- Exercice Intermediate 2 : Quintiles clients par montant total
-- Solution de référence

WITH customer_totals AS (
    SELECT
        customer_id,
        SUM(price) as total_spent
    FROM fact_orders
    GROUP BY customer_id
)
SELECT
    customer_id,
    total_spent,
    NTILE(5) OVER (ORDER BY total_spent DESC) as quintile
FROM customer_totals
ORDER BY total_spent DESC
