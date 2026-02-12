-- Exercice Advanced 3 : Top 3 vendeurs par état (PARTITION BY)
-- Solution de référence

WITH seller_revenue AS (
    SELECT
        s.seller_id,
        s.seller_state as state,
        SUM(o.price) as revenue
    FROM fact_orders o
    INNER JOIN dim_sellers s ON o.seller_key = s.seller_key
    GROUP BY s.seller_id, s.seller_state
),
ranked_sellers AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY state ORDER BY revenue DESC) as rank_in_state
    FROM seller_revenue
)
SELECT * FROM ranked_sellers
WHERE rank_in_state <= 3
ORDER BY state, rank_in_state
