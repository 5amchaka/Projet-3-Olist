-- =============================================================================
-- seller_scoring.sql
-- Scoring multicriteres des vendeurs Olist
-- =============================================================================
-- Chaque vendeur est evalue sur 5 axes, chacun note de 1 a 5 (quintiles) :
--   1. Revenue       : chiffre d'affaires total
--   2. Volume        : nombre de commandes
--   3. Avis          : note moyenne des clients
--   4. Rapidite      : delai moyen de livraison (inverse : rapide = mieux)
--   5. Ponctualite   : pourcentage de livraisons a l'heure
--
-- Le score total (somme des 5 scores, max = 25) determine le classement.
--
-- Resultat : top 50 vendeurs avec metriques brutes, scores et rangs.
--
-- Concepts SQL utilises :
-- -----------------------------------------------------------------------
-- 1. NTILE(n) OVER (ORDER BY ...)
--    Divise les lignes en n groupes de taille egale (quintiles avec n=5).
--    Chaque vendeur recoit un score de 1 a 5 sur chaque axe.
--    Pour le delai de livraison, on inverse l'ordre (ASC au lieu de DESC)
--    car un delai court est meilleur.
--
-- 2. RANK() OVER (ORDER BY ...)
--    Attribue un rang avec gestion des ex-aequo. Si deux vendeurs ont
--    le meme score, ils recoivent le meme rang et le rang suivant est
--    saute (ex: 1, 2, 2, 4).
--
-- 3. DENSE_RANK() OVER (ORDER BY ...)
--    Similaire a RANK() mais sans saut de rang apres un ex-aequo
--    (ex: 1, 2, 2, 3). Utile pour un classement continu.
--
-- 4. CASE WHEN dans une agregation
--    On utilise CASE WHEN pour calculer le pourcentage de livraisons
--    a l'heure : AVG(CASE WHEN condition THEN 1.0 ELSE 0.0 END) * 100.
--    C'est equivalent a compter le % de lignes qui satisfont la condition.
--
-- 5. CTEs enchaines
--    seller_metrics calcule les metriques brutes, seller_scored attribue
--    les scores NTILE et le rang.
--
-- 6. PARTITION BY (implicite)
--    Ici, NTILE et RANK s'appliquent sur l'ensemble des vendeurs
--    (pas de PARTITION BY), donc le score est relatif a tous les vendeurs.
-- =============================================================================

-- CTE 1 : Calcul des metriques brutes par vendeur
-- On joint fact_orders avec dim_sellers pour les infos du vendeur.
-- Filtre sur les commandes livrees uniquement.
WITH seller_metrics AS (
    SELECT
        s.seller_id,
        s.city AS seller_city,
        s.state AS seller_state,

        -- Metrique 1 : Chiffre d'affaires total
        ROUND(SUM(f.price), 2) AS total_revenue,

        -- Metrique 2 : Nombre de commandes distinctes
        COUNT(DISTINCT f.order_id) AS nb_orders,

        -- Metrique 3 : Note moyenne des avis clients
        ROUND(AVG(f.review_score), 2) AS avg_review,

        -- Metrique 4 : Delai moyen de livraison en jours
        ROUND(AVG(f.delivery_days), 1) AS avg_delivery_days,

        -- Metrique 5 : Pourcentage de livraisons a l'heure (ou en avance)
        -- delivery_delta_days <= 0 signifie que la livraison est arrivee
        -- avant ou le jour de la date estimee.
        -- On utilise CASE WHEN pour convertir un booleen en 0/1, puis
        -- AVG * 100 donne le pourcentage.
        ROUND(
            AVG(CASE
                WHEN f.delivery_delta_days <= 0 THEN 1.0
                ELSE 0.0
            END) * 100,
            1
        ) AS on_time_pct

    FROM fact_orders f
    JOIN dim_sellers s ON f.seller_key = s.seller_key
    WHERE f.order_status = 'delivered'
    GROUP BY s.seller_id, s.city, s.state
),

-- CTE 2 : Attribution des scores par quintiles et classement
-- NTILE(5) divise les vendeurs en 5 groupes egaux sur chaque axe.
seller_scored AS (
    SELECT
        seller_id,
        seller_city,
        seller_state,
        total_revenue,
        nb_orders,
        avg_review,
        avg_delivery_days,
        on_time_pct,

        -- Score revenue : les vendeurs avec le plus gros CA = quintile 5
        NTILE(5) OVER (ORDER BY total_revenue ASC) AS revenue_score,

        -- Score volume : les vendeurs avec le plus de commandes = quintile 5
        NTILE(5) OVER (ORDER BY nb_orders ASC) AS volume_score,

        -- Score avis : les mieux notes = quintile 5
        NTILE(5) OVER (ORDER BY avg_review ASC) AS review_score_ntile,

        -- Score livraison (INVERSE) : les plus rapides = quintile 5
        -- ORDER BY DESC car un petit delai est meilleur, donc les plus
        -- rapides doivent recevoir le score le plus eleve.
        NTILE(5) OVER (ORDER BY avg_delivery_days DESC) AS delivery_score,

        -- Score ponctualite : les plus ponctuels = quintile 5
        NTILE(5) OVER (ORDER BY on_time_pct ASC) AS ontime_score

    FROM seller_metrics
)

-- Resultat final : top 50 vendeurs avec score total et classement
SELECT
    seller_id,
    seller_city,
    seller_state,

    -- Metriques brutes
    total_revenue,
    nb_orders,
    avg_review,
    avg_delivery_days,
    on_time_pct,

    -- Scores individuels (1 a 5)
    revenue_score,
    volume_score,
    review_score_ntile,
    delivery_score,
    ontime_score,

    -- Score total : somme des 5 scores (maximum = 25)
    (revenue_score + volume_score + review_score_ntile
     + delivery_score + ontime_score) AS total_score,

    -- RANK : rang avec sauts apres ex-aequo (1, 2, 2, 4)
    RANK() OVER (
        ORDER BY (revenue_score + volume_score + review_score_ntile
                  + delivery_score + ontime_score) DESC
    ) AS seller_rank,

    -- DENSE_RANK : rang sans sauts apres ex-aequo (1, 2, 2, 3)
    DENSE_RANK() OVER (
        ORDER BY (revenue_score + volume_score + review_score_ntile
                  + delivery_score + ontime_score) DESC
    ) AS seller_dense_rank

FROM seller_scored
ORDER BY total_score DESC
LIMIT 50;
