-- Exercice Beginner 1 : Filtrer commandes livrées en 2017, tri prix DESC
-- Solution de référence

SELECT
    order_id,
    order_date,
    price
FROM v_orders_enriched
WHERE
    order_status = 'delivered'
    AND order_date >= '2017-01-01'
    AND order_date < '2018-01-01'
ORDER BY price DESC
