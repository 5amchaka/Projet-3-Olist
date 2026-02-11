-- =============================================================================
-- views.sql
-- Vues SQL reutilisables pour le data warehouse Olist
-- =============================================================================
-- Les vues (CREATE VIEW) encapsulent des requetes frequemment utilisees
-- dans un objet nomme permanent. Avantages :
--   - Reutilisabilite : evite de repeter le meme JOIN/GROUP BY partout
--   - Lisibilite : SELECT * FROM v_monthly_sales au lieu d'une requete longue
--   - Maintenance : un seul endroit a modifier si le schema evolue
--   - Securite : peut restreindre l'acces a certaines colonnes
--
-- IMPORTANT : une vue ne stocke PAS de donnees. C'est un alias pour une
-- requete. A chaque SELECT sur la vue, la requete sous-jacente est executee.
-- Pour des raisons de performance, les vues materialisees (MATERIALIZED VIEW)
-- stockent le resultat, mais SQLite ne les supporte pas nativement.
--
-- Execution :
--   sqlite3 data/database/olist_dw.db < sql/views.sql
-- =============================================================================


-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║ Vue 1 : v_monthly_sales                                                ║
-- ║ Ventes mensuelles aggregees                                            ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝
-- Cette vue pre-calcule les metriques mensuelles les plus demandees :
-- CA, nombre de commandes, panier moyen.
-- Reutilisee dans : trends_monthly, basket_avg, ca_yoy.
--
-- Concepts SQL :
--   - CREATE VIEW ... AS SELECT ... — definition de la vue
--   - DROP VIEW IF EXISTS — idempotence (re-execution sans erreur)
--   - JOIN + GROUP BY + fonctions d'agregation

DROP VIEW IF EXISTS v_monthly_sales;

CREATE VIEW v_monthly_sales AS
SELECT
    d.year,
    d.month,
    d.year || '-' || PRINTF('%02d', d.month) AS month_label,
    ROUND(SUM(f.price), 2)                   AS monthly_revenue,
    COUNT(DISTINCT f.order_id)                AS monthly_orders,
    ROUND(
        SUM(f.price) * 1.0 / NULLIF(COUNT(DISTINCT f.order_id), 0),
        2
    )                                         AS avg_basket
FROM fact_orders f
JOIN dim_dates d ON f.date_key = d.date_key
WHERE f.order_status = 'delivered'
GROUP BY d.year, d.month;


-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║ Vue 2 : v_customer_cohorts                                             ║
-- ║ Clients avec leur cohorte (mois de premier achat)                      ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝
-- Associe chaque client unique a sa cohorte (mois du premier achat).
-- Reutilisee dans : cohorts_retention, new_vs_recurring, ltv_cohorts.
--
-- Concepts SQL :
--   - MIN() pour determiner la premiere commande
--   - Calcul AAAAMM a partir de date_key (division entiere)
--   - FORMAT du mois en AAAA-MM pour l'affichage

DROP VIEW IF EXISTS v_customer_cohorts;

CREATE VIEW v_customer_cohorts AS
SELECT
    c.customer_unique_id,
    MIN(f.date_key / 100)  AS first_month,
    (MIN(f.date_key / 100) / 100) || '-' || PRINTF('%02d', MIN(f.date_key / 100) % 100)
                            AS first_month_label,
    COUNT(DISTINCT f.order_id) AS total_orders,
    ROUND(SUM(f.price), 2)    AS total_spent
FROM fact_orders f
JOIN dim_customers c ON f.customer_key = c.customer_key
WHERE f.order_status = 'delivered'
  AND f.date_key IS NOT NULL
GROUP BY c.customer_unique_id;


-- ╔═══════════════════════════════════════════════════════════════════════════╗
-- ║ Vue 3 : v_orders_enriched                                              ║
-- ║ Commandes enrichies (fact + toutes les dimensions)                     ║
-- ╚═══════════════════════════════════════════════════════════════════════════╝
-- Vue denormalisee qui joint la table de faits avec toutes les dimensions.
-- Permet des analyses ad-hoc sans ecrire de JOIN a chaque fois.
--
-- Concepts SQL :
--   - JOIN multiples (4 tables)
--   - COALESCE pour les valeurs NULL
--   - Selection de colonnes utiles (pas SELECT *)

DROP VIEW IF EXISTS v_orders_enriched;

CREATE VIEW v_orders_enriched AS
SELECT
    -- Identifiants
    f.order_id,
    f.order_item_id,
    f.order_status,

    -- Temporel
    d.full_date       AS order_date,
    d.year,
    d.month,
    d.day_name,
    d.is_weekend,

    -- Client
    c.customer_unique_id,
    c.city             AS customer_city,
    c.state            AS customer_state,

    -- Produit
    COALESCE(p.category_name_en, p.category_name_pt, 'Unknown')
                       AS product_category,

    -- Metriques
    f.price,
    f.freight_value,
    f.review_score,
    f.delivery_days,
    f.delivery_delta_days

FROM fact_orders f
LEFT JOIN dim_dates     d ON f.date_key     = d.date_key
LEFT JOIN dim_customers c ON f.customer_key = c.customer_key
LEFT JOIN dim_products  p ON f.product_key  = p.product_key;
