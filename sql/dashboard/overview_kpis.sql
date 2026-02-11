-- =============================================================================
-- overview_kpis.sql
-- KPIs globaux du dashboard Olist
-- =============================================================================
-- Retourne UNE seule ligne contenant les indicateurs cles de performance :
--   - total_orders      : nombre total de commandes livrees
--   - total_revenue     : chiffre d'affaires total (commandes livrees)
--   - avg_review        : note moyenne des avis clients
--   - avg_delivery_days : delai moyen de livraison (commandes livrees)
--
-- Concepts SQL utilises :
-- -----------------------------------------------------------------------
-- 1. AGREGATIONS (COUNT, SUM, AVG)
--    Les fonctions d'agregation operent sur un ensemble de lignes pour
--    retourner une valeur unique. COUNT compte, SUM additionne, AVG calcule
--    la moyenne.
--
-- 2. COUNT(DISTINCT ...)
--    Compte les valeurs uniques. Ici on compte les order_id distincts car
--    la table fact_orders a une granularite "article de commande"
--    (plusieurs lignes par commande).
--
-- 3. CASE WHEN ... THEN ... ELSE ... END
--    Expression conditionnelle SQL. Permet de filtrer au sein d'une
--    agregation sans clause WHERE, en retournant NULL pour les lignes
--    non desirees (les fonctions d'agregation ignorent les NULL).
--
-- 4. NULLIF(valeur, 0)
--    Retourne NULL si la valeur vaut 0. Utile pour eviter une division
--    par zero (division par NULL = NULL au lieu d'une erreur).
--
-- 5. ROUND(valeur, decimales)
--    Arrondit un nombre a virgule flottante au nombre de decimales
--    souhaite pour un affichage propre.
--
-- 6. Sous-requetes dans SELECT
--    Chaque colonne utilise un CASE WHEN pour calculer son KPI specifique.
--    Cela permet de combiner des filtres differents (delivered vs tous)
--    dans une seule ligne de resultat.
-- =============================================================================

SELECT
    -- Nombre total de commandes livrees
    -- COUNT(DISTINCT ...) car chaque commande (order_id) peut avoir
    -- plusieurs articles (order_item_id) dans fact_orders.
    -- Le CASE WHEN filtre uniquement les commandes livrees.
    COUNT(DISTINCT CASE
        WHEN order_status = 'delivered' THEN order_id
        ELSE NULL
    END) AS total_orders,

    -- Chiffre d'affaires total (uniquement commandes livrees)
    -- SUM ignore les NULL, donc le CASE WHEN exclut les non-livrees.
    -- ROUND arrondit a 2 decimales pour un affichage monetaire.
    ROUND(
        SUM(CASE
            WHEN order_status = 'delivered' THEN price
            ELSE NULL
        END),
        2
    ) AS total_revenue,

    -- Note moyenne des avis (toutes commandes confondues)
    -- AVG ignore automatiquement les review_score NULL.
    ROUND(
        AVG(review_score),
        2
    ) AS avg_review,

    -- Delai moyen de livraison en jours (uniquement commandes livrees)
    -- On filtre sur delivered car delivery_days n'a de sens que pour
    -- les commandes effectivement livrees.
    ROUND(
        AVG(CASE
            WHEN order_status = 'delivered' THEN delivery_days
            ELSE NULL
        END),
        1
    ) AS avg_delivery_days

FROM fact_orders;
