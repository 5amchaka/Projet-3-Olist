-- Exercice Advanced 2 : Clients avec 2+ commandes
-- Solution de référence (méthode simple GROUP BY)

SELECT
    customer_id,
    COUNT(*) as nb_orders
FROM fact_orders
GROUP BY customer_id
HAVING COUNT(*) >= 2
ORDER BY nb_orders DESC
