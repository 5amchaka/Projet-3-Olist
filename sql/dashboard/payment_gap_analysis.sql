-- =============================================================================
-- payment_gap_analysis.sql
-- Analyse des ecarts entre montants payes et montants factures
-- =============================================================================
--
-- CONTEXTE
-- -----------------------------------------------------------------------
-- Dans le dataset Olist, chaque commande a :
--   - Un montant facture : SUM(price) + SUM(freight_value)  (table fact_orders)
--   - Un montant paye   : order_payment_total               (table fact_orders)
--
-- order_payment_total provient de SUM(payment_value) agrege depuis le CSV
-- brut olist_order_payments_dataset.csv lors de l'ETL (src/etl/load.py:129).
--
-- On observe 384 commandes (0.39%) avec un ecart (delta) > 0.01 R$.
-- Ce fichier documente les requetes d'investigation et les conclusions.
--
--
-- CAUSES IDENTIFIEES
-- -----------------------------------------------------------------------
-- 1. INTERETS DE FINANCEMENT (juros) — ~290 commandes
--    Au Bresil, les paiements par carte de credit en plusieurs fois
--    (parcelamento) incluent des interets dans payment_value.
--    Le CSV brut contient le champ payment_installments (non charge dans
--    le data warehouse) qui permet de le verifier :
--      - Commandes avec ecart : 5.22 parcelas en moyenne
--      - Commandes sans ecart : 2.85 parcelas en moyenne
--      - Correlation delta / installments = 0.61
--    Les 10 plus gros ecarts sont tous des paiements credit_card
--    avec 10 a 24 parcelas.
--
-- 2. PAIEMENTS MIXTES (voucher + carte) — ~18 commandes
--    L'ETL agregue SUM(payment_value) et ne garde que le payment_type
--    dominant (mode). On perd donc l'info du paiement mixte.
--    Exemple : commande fbf352b... = credit_card 6x (69.12 R$) +
--    voucher 1x (91.68 R$). Le delta apparent provient du fait que
--    le voucher couvre une partie du montant et les interets carte
--    s'ajoutent sur l'autre partie.
--
-- 3. ARRONDIS BOLETO — ~26 commandes
--    Ecarts negligeables (±0.03 R$), lies aux arrondis de centimes
--    lors de la generation du boleto bancaire.
--
-- 4. ECARTS DEBIT_CARD NEGATIFS — ~10 commandes
--    Le client paye MOINS que le facture (-1.60 a -16.50 R$).
--    Cause non identifiee dans les donnees disponibles.
--    → Voir "Pistes de recherche" en fin de fichier.
--
--
-- IMPACT
-- -----------------------------------------------------------------------
--   - 99.61% des commandes n'ont aucun ecart
--   - Somme nette des ecarts : +2 870.77 R$ (surpayes > sous-payes)
--   - Ecart moyen quand il existe : +7.48 R$
--
-- =============================================================================


-- ─────────────────────────────────────────────────────────────────────────────
-- 1. STATISTIQUES GLOBALES
-- ─────────────────────────────────────────────────────────────────────────────

SELECT
    COUNT(*)                        AS nb_commandes_avec_ecart,
    ROUND(AVG(delta), 2)            AS delta_moyen,
    ROUND(MIN(delta), 2)            AS delta_min,
    ROUND(MAX(delta), 2)            AS delta_max,
    ROUND(SUM(ABS(delta)), 2)       AS somme_abs_deltas
FROM (
    SELECT
        order_id,
        MAX(order_payment_total) - (SUM(price) + SUM(freight_value)) AS delta
    FROM fact_orders
    GROUP BY order_id
    HAVING ABS(delta) > 0.01
);
-- Resultat attendu :
--   nb_commandes_avec_ecart = 384
--   delta_moyen = 7.48, delta_min = -51.62, delta_max = 182.81


-- ─────────────────────────────────────────────────────────────────────────────
-- 2. REPARTITION SURPAYE / SOUS-PAYE
-- ─────────────────────────────────────────────────────────────────────────────

SELECT
    CASE
        WHEN delta > 0.01  THEN 'surpaye (paid > invoiced)'
        WHEN delta < -0.01 THEN 'sous-paye (paid < invoiced)'
        ELSE 'exact'
    END                             AS type_ecart,
    COUNT(*)                        AS nb_commandes,
    ROUND(AVG(ABS(delta)), 2)       AS ecart_abs_moyen,
    ROUND(SUM(delta), 2)            AS somme_delta
FROM (
    SELECT
        order_id,
        MAX(order_payment_total) - (SUM(price) + SUM(freight_value)) AS delta
    FROM fact_orders
    GROUP BY order_id
)
GROUP BY type_ecart;
-- Resultat attendu :
--   surpaye  : 290 commandes, somme = +3070.40
--   sous-paye:  94 commandes, somme =  -199.63
--   exact    : 98282 commandes


-- ─────────────────────────────────────────────────────────────────────────────
-- 3. HISTOGRAMME DES DELTAS PAR TRANCHE
-- ─────────────────────────────────────────────────────────────────────────────

SELECT
    CASE
        WHEN delta < -10     THEN '< -10'
        WHEN delta < -1      THEN '-10 a -1'
        WHEN delta < -0.01   THEN '-1 a -0.01'
        WHEN delta <= 0.01   THEN 'exact (+-0.01)'
        WHEN delta <= 1      THEN '0.01 a 1'
        WHEN delta <= 10     THEN '1 a 10'
        WHEN delta <= 50     THEN '10 a 50'
        ELSE '> 50'
    END                             AS tranche_delta,
    COUNT(*)                        AS nb_commandes
FROM (
    SELECT
        order_id,
        MAX(order_payment_total) - (SUM(price) + SUM(freight_value)) AS delta
    FROM fact_orders
    GROUP BY order_id
)
GROUP BY tranche_delta
ORDER BY MIN(delta);


-- ─────────────────────────────────────────────────────────────────────────────
-- 4. ANALYSE CROISEE PAR TYPE DE PAIEMENT
-- ─────────────────────────────────────────────────────────────────────────────

SELECT
    payment_type,
    COUNT(DISTINCT order_id)        AS nb_commandes,
    SUM(CASE WHEN ABS(delta) > 0.01 THEN 1 ELSE 0 END)
                                    AS nb_avec_ecart,
    ROUND(
        100.0 * SUM(CASE WHEN ABS(delta) > 0.01 THEN 1 ELSE 0 END)
        / COUNT(DISTINCT order_id), 2
    )                               AS pct_ecart,
    ROUND(AVG(CASE WHEN ABS(delta) > 0.01 THEN delta END), 2)
                                    AS delta_moyen
FROM (
    SELECT
        order_id,
        payment_type,
        MAX(order_payment_total) - (SUM(price) + SUM(freight_value)) AS delta
    FROM fact_orders
    GROUP BY order_id, payment_type
)
GROUP BY payment_type
ORDER BY nb_avec_ecart DESC;
-- Resultat attendu :
--   credit_card : 346 ecarts (0.46%), delta moyen +8.45
--   boleto      :  26 ecarts (0.13%), delta moyen ~0
--   debit_card  :  10 ecarts (0.66%), delta moyen -5.20
--   voucher     :   2 ecarts (0.10%), delta moyen -0.01


-- ─────────────────────────────────────────────────────────────────────────────
-- 5. TOP 20 DES PLUS GROS ECARTS (detail)
-- ─────────────────────────────────────────────────────────────────────────────

SELECT
    order_id,
    ROUND(SUM(price) + SUM(freight_value), 2) AS invoiced_total,
    ROUND(MAX(order_payment_total), 2)        AS paid_total,
    ROUND(
        MAX(order_payment_total) - (SUM(price) + SUM(freight_value)), 2
    )                                         AS delta
FROM fact_orders
GROUP BY order_id
HAVING ABS(delta) > 0.01
ORDER BY ABS(delta) DESC
LIMIT 20;


-- =============================================================================
-- PISTES DE RECHERCHE
-- =============================================================================
--
-- A. Charger payment_installments dans le data warehouse
--    Le champ payment_installments existe dans le CSV brut mais n'est pas
--    charge dans fact_orders. L'ajouter permettrait de :
--      - Confirmer definitivement la cause juros avec une jointure directe
--      - Calculer le taux d'interet implicite par commande :
--        taux = (payment_value / (price + freight)) - 1
--      - Segmenter les clients par comportement de financement
--
-- B. Ecarts negatifs debit_card (10 commandes, -1.60 a -16.50 R$)
--    Hypotheses a verifier :
--      - Cashback ou remise appliquee par le processeur de paiement
--      - Erreur de saisie montant lors du paiement par debit
--      - Annulation partielle d'un article non reflétée dans order_items
--    Verification possible : croiser avec order_status et le nombre
--    d'items pour detecter des annulations partielles :
--
--    SELECT f.order_id, f.order_status, COUNT(*) AS nb_items,
--           MAX(f.order_payment_total) - (SUM(f.price) + SUM(f.freight_value)) AS delta
--    FROM fact_orders f
--    WHERE f.payment_type = 'debit_card'
--    GROUP BY f.order_id
--    HAVING delta < -0.01
--    ORDER BY delta;
--
-- C. Paiements mixtes (voucher + carte)
--    L'ETL actuel (src/etl/load.py:128-131) agrege les paiements par
--    commande et ne garde que le type dominant. Pour un audit complet,
--    envisager :
--      - Ajouter une colonne nb_payment_types dans fact_orders
--      - Ou creer une table bridge dim_payment_methods
--      - Cela permettrait d'isoler les commandes mixtes sans recourir
--        au CSV brut
--
-- =============================================================================
