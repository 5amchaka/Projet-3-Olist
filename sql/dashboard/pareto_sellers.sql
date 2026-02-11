-- =============================================================================
-- pareto_sellers.sql
-- Analyse Pareto (80/20) des vendeurs Olist
-- =============================================================================
-- Le principe de Pareto (loi 80/20) stipule qu'environ 80% du chiffre
-- d'affaires est genere par 20% des vendeurs.
--
-- Retourne les TOP 100 vendeurs avec :
--   - seller_rank        : rang du vendeur (par CA decroissant)
--   - seller_id          : identifiant du vendeur
--   - seller_city        : ville du vendeur
--   - seller_state       : etat du vendeur
--   - total_revenue      : CA total du vendeur
--   - cumulative_revenue : CA cumule
--   - cumulative_pct     : pourcentage cumule du CA total
--   - pareto_group       : '80%' (top) ou '20%' (reste)
--
-- Concepts SQL utilises :
-- -----------------------------------------------------------------------
-- 1. ROW_NUMBER() OVER (ORDER BY ...)
--    Attribue un rang unique a chaque ligne selon l'ordre specifie.
--    Contrairement a RANK(), ROW_NUMBER() ne produit jamais d'ex-aequo :
--    chaque vendeur recoit un rang distinct.
--
-- 2. SUM() OVER (ORDER BY ... ROWS UNBOUNDED PRECEDING)
--    Fonction fenetre cumulative. Calcule la somme de toutes les lignes
--    depuis le debut (UNBOUNDED PRECEDING) jusqu'a la ligne courante.
--    Produit un "running total" du CA, essentiel pour tracer la courbe
--    de Pareto.
--
-- 3. PERCENT_RANK() OVER (ORDER BY ...)
--    Calcule le rang en percentile de chaque ligne. Retourne une valeur
--    entre 0 et 1. Formule : (rang - 1) / (nb_lignes - 1).
--    Permet d'identifier ou se situe chaque vendeur dans la distribution.
--
-- 4. Sous-requete scalaire
--    (SELECT SUM(...) FROM ...) dans le SELECT principal pour calculer
--    le total general et en deduire le pourcentage cumule.
--
-- 5. CTE enchaines
--    Deux CTEs : seller_revenue calcule le CA par vendeur,
--    seller_ranked ajoute rang, cumul et percentile.
--
-- 6. LIMIT
--    Restreint le resultat aux 100 premiers vendeurs pour le dashboard.
-- =============================================================================

-- CTE 1 : Calcul du CA par vendeur (commandes livrees uniquement)
WITH seller_revenue AS (
    SELECT
        s.seller_id,
        s.city AS seller_city,
        s.state AS seller_state,
        ROUND(SUM(f.price), 2) AS total_revenue
    FROM fact_orders f
    JOIN dim_sellers s ON f.seller_key = s.seller_key
    WHERE f.order_status = 'delivered'
    GROUP BY s.seller_id, s.city, s.state
    HAVING SUM(f.price) > 0
),

-- CTE 2 : Ajout du rang, du cumul et du pourcentage
seller_ranked AS (
    SELECT
        -- ROW_NUMBER attribue un rang unique par CA decroissant
        ROW_NUMBER() OVER (ORDER BY total_revenue DESC) AS seller_rank,

        seller_id,
        seller_city,
        seller_state,
        total_revenue,

        -- Cumul glissant du CA : somme de toutes les lignes precedentes
        -- et de la ligne courante, dans l'ordre du CA decroissant
        SUM(total_revenue) OVER (
            ORDER BY total_revenue DESC
            ROWS UNBOUNDED PRECEDING
        ) AS cumulative_revenue,

        -- Pourcentage cumule par rapport au CA total
        -- La sous-requete scalaire calcule le total general
        ROUND(
            100.0 * SUM(total_revenue) OVER (
                ORDER BY total_revenue DESC
                ROWS UNBOUNDED PRECEDING
            ) / (SELECT SUM(total_revenue) FROM seller_revenue),
            2
        ) AS cumulative_pct,

        -- PERCENT_RANK : rang en percentile (0 a 1)
        -- Le meilleur vendeur a 0.0, le pire a 1.0
        ROUND(PERCENT_RANK() OVER (ORDER BY total_revenue DESC), 4) AS pct_rank

    FROM seller_revenue
)

-- Resultat final : classification Pareto + limitation aux top 100
SELECT
    seller_rank,
    seller_id,
    seller_city,
    seller_state,
    total_revenue,
    cumulative_revenue,
    cumulative_pct,
    -- Classification Pareto basee sur le pourcentage cumule du CA
    -- Les vendeurs qui contribuent aux premiers 80% du CA = groupe '80%'
    CASE
        WHEN cumulative_pct <= 80 THEN '80%'
        ELSE '20%'
    END AS pareto_group
FROM seller_ranked
ORDER BY seller_rank
LIMIT 100;
