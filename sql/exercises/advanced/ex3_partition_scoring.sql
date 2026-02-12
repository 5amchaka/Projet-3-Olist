-- Exercice Advanced 3 : Top 3 vendeurs par état (PARTITION BY)
-- Solution de référence

WITH seller_revenue AS (
    SELECT
        s.state as state,
        s.seller_id,
        SUM(o.price) as revenue
    FROM fact_orders o
    INNER JOIN dim_sellers s ON o.seller_key = s.seller_key
    WHERE o.order_status = 'delivered'
    GROUP BY s.state, s.seller_id
),
ranked_sellers AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY state ORDER BY revenue DESC) as rank_in_state
    FROM seller_revenue
)
SELECT
    state,
    seller_id,
    revenue,
    rank_in_state
FROM ranked_sellers
WHERE rank_in_state <= 3
ORDER BY state, rank_in_state
