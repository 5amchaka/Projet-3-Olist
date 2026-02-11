-- =============================================================================
-- rfm_segmentation.sql
-- Segmentation RFM (Recency, Frequency, Monetary) multi-niveaux
-- =============================================================================
-- La segmentation RFM est une technique marketing qui classe les clients
-- selon trois axes :
--   - Recency (R)   : quand a eu lieu le dernier achat ? (plus recent = mieux)
--   - Frequency (F)  : combien de commandes distinctes ? (plus = mieux)
--   - Monetary (M)   : combien a depense au total ? (plus = mieux)
--
-- Resultat : une ligne par segment avec :
--   - segment        : nom du segment (Champions, Loyal, At Risk, etc.)
--   - nb_customers   : nombre de clients dans le segment
--   - avg_monetary   : depense moyenne du segment
--   - avg_frequency  : frequence moyenne du segment
--
-- Concepts SQL utilises :
-- -----------------------------------------------------------------------
-- 1. CTEs MULTI-NIVEAUX (WITH cte1 AS (...), cte2 AS (...), ...)
--    Chaine de CTEs ou chaque etape transforme le resultat de la precedente.
--    Cela decompose un calcul complexe en etapes lisibles et maintenables.
--    Ici on a 3 CTEs : rfm_raw -> rfm_scored -> rfm_segmented.
--
-- 2. NTILE(n) OVER (ORDER BY ...)
--    Fonction de fenetrage qui divise les lignes en n groupes de taille
--    egale (ou quasi-egale). NTILE(5) cree des quintiles (scores de 1 a 5).
--    Pour la recence, on inverse l'ordre pour que recent = score eleve.
--
-- 3. CASE WHEN avec conditions multiples
--    Classification en segments marketing basee sur la combinaison des
--    scores R, F et M. L'ordre des WHEN est important : le premier
--    qui correspond est applique.
--
-- 4. JULIANDAY() (specifique SQLite)
--    Convertit une date en nombre de jours juliens. La difference entre
--    deux JULIANDAY donne le nombre de jours entre deux dates.
--
-- 5. Sous-requete scalaire
--    (SELECT MAX(full_date) FROM ...) retourne la date la plus recente
--    de la base, utilisee comme reference pour le calcul de recence.
--
-- 6. GROUP BY + agregations finales
--    Le resultat final agregee les clients par segment pour obtenir
--    les statistiques de chaque groupe.
-- =============================================================================

-- CTE 1 : Calcul des metriques RFM brutes par client unique
-- On joint fact_orders (livrees) avec dim_customers et dim_dates
-- pour identifier chaque client par customer_unique_id.
WITH rfm_raw AS (
    SELECT
        c.customer_unique_id,

        -- RECENCY : nombre de jours depuis le dernier achat.
        -- JULIANDAY convertit une date en jours juliens ; la difference
        -- donne directement un nombre de jours.
        -- La date de reference est la date max de la base (sous-requete scalaire).
        CAST(
            JULIANDAY(
                (SELECT MAX(d2.full_date)
                 FROM fact_orders f2
                 JOIN dim_dates d2 ON f2.date_key = d2.date_key)
            )
            - JULIANDAY(MAX(d.full_date))
        AS INTEGER) AS recency,

        -- FREQUENCY : nombre de commandes distinctes du client
        -- COUNT(DISTINCT) car le grain de fact_orders est l'article
        COUNT(DISTINCT f.order_id) AS frequency,

        -- MONETARY : montant total depense
        ROUND(SUM(f.price), 2) AS monetary

    FROM fact_orders f
    JOIN dim_customers c ON f.customer_key = c.customer_key
    JOIN dim_dates d ON f.date_key = d.date_key
    WHERE f.order_status = 'delivered'
    GROUP BY c.customer_unique_id
),

-- CTE 2 : Attribution des scores RFM via NTILE(5) — quintiles
-- NTILE(5) divise les clients en 5 groupes de taille egale.
-- Score 5 = meilleur pour chaque dimension.
rfm_scored AS (
    SELECT
        customer_unique_id,
        recency,
        frequency,
        monetary,

        -- Score Recency : ORDER BY recency DESC fait que les plus petites
        -- recences (achats recents) se retrouvent dans le quintile 5 (meilleur).
        NTILE(5) OVER (ORDER BY recency DESC) AS r_score,

        -- Score Frequency : les clients les plus frequents = quintile 5
        NTILE(5) OVER (ORDER BY frequency ASC) AS f_score,

        -- Score Monetary : les clients qui depensent le plus = quintile 5
        NTILE(5) OVER (ORDER BY monetary ASC) AS m_score

    FROM rfm_raw
),

-- CTE 3 : Classification en segments marketing
-- CASE WHEN pour attribuer un segment selon la combinaison R, F, M.
-- L'ordre des conditions est important : "At Risk" est teste avant "Loyal"
-- car un client At Risk a aussi f_score >= 3.
rfm_segmented AS (
    SELECT
        customer_unique_id,
        recency,
        frequency,
        monetary,
        r_score,
        f_score,
        m_score,
        CASE
            -- Champions : clients recents ET frequents (les meilleurs)
            WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
            -- At Risk : clients autrefois fideles mais plus actifs recemment
            WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
            -- Loyal : clients qui achetent souvent (teste apres At Risk)
            WHEN f_score >= 3 THEN 'Loyal'
            -- Lost : clients inactifs et peu frequents
            WHEN r_score <= 2 AND f_score <= 2 THEN 'Lost'
            -- New : clients recents mais premiere commande
            WHEN r_score >= 4 AND f_score = 1 THEN 'New'
            -- Others : tous les autres profils
            ELSE 'Others'
        END AS segment
    FROM rfm_scored
)

-- Resultat final : agregation par segment
-- On resume chaque segment avec le nombre de clients et les moyennes.
SELECT
    segment,
    COUNT(*) AS nb_customers,
    ROUND(AVG(monetary), 2) AS avg_monetary,
    ROUND(AVG(frequency), 2) AS avg_frequency
FROM rfm_segmented
GROUP BY segment
ORDER BY nb_customers DESC;
