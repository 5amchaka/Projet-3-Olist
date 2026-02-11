La startup e-commerce n'a aucune visibilité sur ses performances.

Voici globalement ce qu'elle voudrait suivre.

💰 Ventes
Chiffre d'affaires (jour, mois, année)
Évolution CA vs N-1
Top 10 produits

👥 Clients
Nouveaux clients vs récurrents
Panier moyen
Taux de conversion
Analyse RFM

📊 Cohortes
Rétention par mois de première commande
LTV (Lifetime Value) par cohorte

Objectifs :
- Créer des requêtes optimisé, mesurer l'évolution de vos requêtes avant et après optimisation de votre part
- Créer des KPI/graphiques adéquates
- (optionnel) Dashboard avec design professionnel (power bi ou streamlit)

﻿# Les CTE (Common Table Expressions)

Les expressions de table communes (CTE) permettent de définir des tables temporaires, ce qui rend les requêtes plus lisibles et modulaires.

## 1. Syntaxe avec WITH
```sql
WITH customer_orders AS (
    SELECT
        o.customer_id,
        COUNT(*) AS nb_orders
    FROM olist_orders_dataset o
    GROUP BY o.customer_id
)
SELECT
    c.customer_unique_id,
    c.customer_city,
    co.nb_orders
FROM olist_customers_dataset c
JOIN customer_orders co ON c.customer_id = co.customer_id
ORDER BY co.nb_orders DESC;
```

- **Lisibilité :** Évite les sous-requêtes imbriquées difficiles à lire.

- **Réutilisabilité :** Une même CTE peut être appelée plusieurs fois au sein d'une même requête.

﻿# Fonctions de Fenêtrage (Window Functions)

Les fonctions de fenêtrage effectuent des calculs sur un ensemble de lignes associées à la ligne actuelle, mais ne les regroupent pas (contrairement à `GROUP BY`).

## 1. RANK() et DENSE_RANK()
```sql
-- Classer les produits par chiffre d'affaires dans chaque catégorie
WITH product_revenue AS (
    SELECT
        oi.product_id,
        p.product_category_name,
        SUM(oi.price + oi.freight_value) AS revenue
    FROM olist_order_items_dataset oi
    JOIN olist_products_dataset p ON p.product_id = oi.product_id
    GROUP BY oi.product_id, p.product_category_name
)
SELECT
    product_id,
    product_category_name,
    revenue,
    RANK() OVER (
        PARTITION BY product_category_name
        ORDER BY revenue DESC
    ) AS revenue_rank
FROM product_revenue;
```

## 2. LAG() et LEAD()
Accéder à la ligne précédente ou suivante.
```sql
-- Comparer le paiement d'une commande avec la précédente pour un même client
WITH customer_payments AS (
    SELECT
        o.customer_id,
        o.order_id,
        o.order_purchase_timestamp,
        op.payment_value
    FROM olist_orders_dataset o
    JOIN olist_order_payments_dataset op ON op.order_id = o.order_id
)
SELECT
    customer_id,
    order_id,
    order_purchase_timestamp,
    payment_value,
    LAG(payment_value) OVER (
        PARTITION BY customer_id
        ORDER BY order_purchase_timestamp
    ) AS prev_payment_value
FROM customer_payments;
```

## 3. Sommes cumulées
```sql
WITH daily_revenue AS (
    SELECT
        CAST(DATE_TRUNC('day', o.order_purchase_timestamp) AS DATE) AS order_day,
        SUM(oi.price + oi.freight_value) AS revenue
    FROM olist_orders_dataset o
    JOIN olist_order_items_dataset oi ON oi.order_id = o.order_id
    GROUP BY 1
)
SELECT
    order_day,
    revenue,
    SUM(revenue) OVER (ORDER BY order_day) AS running_total
FROM daily_revenue;
```

# Exercices :

1. Récupérer le classement de chaque client en fonction du montant total de ses paiements (à l'aide de l'expression régulière CTE sur `olist_order_payments_dataset`, puis en appelant la fonction `RANK()`).

2. Pour chaque commande, afficher le montant du paiement et le montant moyen des commandes du client (à l'aide des fonctions `AVG() OVER()` sur `olist_orders_dataset` et `olist_order_payments_dataset`).

3. Calculer la différence en jours entre deux commandes consécutives d'un même client (à l'aide de la fonction `LAG()` sur `order_purchase_timestamp`).

﻿# Index et structures de données

## Introduction
Les index accélèrent les recherches en créant des structures de données optimisées. Cela fonctionne comme une table des matières d'un livre qui permet d'accéder directement à la bonne page.

## Concept d'index
Sans index : scan complet (lecture de toutes les lignes).

Avec index : recherche ciblée.

## Types d'index courants
### 1. B-Tree Index (par défaut)
Idéal pour :
- Comparaisons (`=`, `<`, `>`, `BETWEEN`)
- Tris (`ORDER BY`)
- Préfixes (`LIKE 'abc%'`)

```sql
CREATE INDEX idx_olist_orders_purchase_ts
ON olist_orders_dataset(order_purchase_timestamp);

CREATE INDEX idx_olist_products_category
ON olist_products_dataset(product_category_name);
```

### 2. Hash Index
Idéal pour :
- Égalités strictes (`=`)
- Clés primaires

Non supporté selon moteurs : `<`, `>`, `LIKE`, `ORDER BY`.

### 3. Index composites
Index sur plusieurs colonnes :

```sql
CREATE INDEX idx_olist_orders_customer_purchase
ON olist_orders_dataset(customer_id, order_purchase_timestamp DESC);
```

Utilise l'index :
- `WHERE customer_id = '9ef432eb6251297304e76186b10a928d'` -> Oui
- `WHERE customer_id = '9ef432eb6251297304e76186b10a928d' AND order_purchase_timestamp >= '2018-01-01'` -> Oui
- `WHERE order_purchase_timestamp >= '2018-01-01'` -> Non (il manque `customer_id`)

## Quand créer un index ?
Index utiles :
- Colonnes fréquemment utilisées dans la clause `WHERE`
- Colonnes de la clause `JOIN ON`
- Colonnes de la clause `ORDER BY`
- Clés étrangères
- Colonnes à forte cardinalité

Index inutiles :
- Petites tables (< 1 000 lignes)
- Colonnes rarement utilisées
- Colonnes à faible cardinalité (ex. : `order_status`)
- Colonnes fréquemment modifiées

## Exemples d'optimisation
Sans index (lent) :

-- Simulation : Scanner 1M lignes pour trouver 1 id
```sql
SELECT *
FROM olist_orders_dataset
WHERE customer_id = '9ef432eb6251297304e76186b10a928d';
```
-- Scan complet : 10 lignes lues

Avec index (rapide) :
-- Avec index sur title : Lookup direct
-- 1 seule ligne lue 
```sql
CREATE INDEX idx_olist_orders_customer
ON olist_orders_dataset(customer_id);

SELECT *
FROM olist_orders_dataset
WHERE customer_id = '9ef432eb6251297304e76186b10a928d';
```

## Compromis des index
Avantages :
- Lectures plus rapides
- Tri optimisé
- JOIN plus efficaces

Inconvénients :
- Espace disque supplémentaire
- `INSERT/UPDATE/DELETE` plus lents
- Maintenance nécessaire

Règle d'or : indexer les colonnes lues souvent, pas celles modifiées souvent.

## Index utiles sur Olist
-- Index automatique sur clé primaire : id
-- Index utiles à créer :
-- - pour GROUP BY
-- - pour filtres temporels
-- - pour recherches produit

```sql
-- Recherche commandes client
CREATE INDEX idx_olist_orders_customer ON olist_orders_dataset(customer_id);

-- Filtres temporels
CREATE INDEX idx_olist_orders_purchase_ts ON olist_orders_dataset(order_purchase_timestamp);

-- Jointure et analyses produit
CREATE INDEX idx_olist_order_items_product ON olist_order_items_dataset(product_id);
```

## Vérifier l'utilisation des index
```sql
EXPLAIN
SELECT *
FROM olist_orders_dataset
WHERE customer_id = '9ef432eb6251297304e76186b10a928d';
```

## Exercice
Dans une table Olist de commandes volumineuse, quelles colonnes indexer ?
- `order_id` (clé primaire)
- `customer_id` (jointures + filtres)
- `order_purchase_timestamp` (filtres temporels)
- `order_status` (faible cardinalité, à évaluer)

Résumé

- Index : Structure de données utilisée pour accélérer les requêtes 
- Arbre B : Index par défaut (utilisé pour la comparaison et le tri) 
- Compromis : Vitesse de lecture versus espace de stockage/écriture 
- Principe : Créer des index pour les colonnes fréquemment consultées plutôt que pour celles fréquemment modifiées.

﻿# Indexation

Les index peuvent accélérer les recherches, mais ralentir les écritures.

## 1. Création d'index

```sql
CREATE INDEX idx_orders_customer_purchase
ON olist_orders_dataset(customer_id, order_purchase_timestamp DESC);

CREATE INDEX idx_order_items_product
ON olist_order_items_dataset(product_id);

```

## 2. Quand créer des index ?

- Colonnes utilisées dans la clause `WHERE`.
- Colonnes utilisées dans les jointures (`JOIN`).
- Colonnes utilisées pour le tri (`ORDER BY`).

## 3. Précautions

- Ne créez pas d'index pour les colonnes à faible cardinalité (par exemple, `order_status`).
- Évitez de créer des index sur toutes les colonnes d'une table (espace de stockage supplémentaire et surcharge d'écriture).

﻿# EXPLAIN - Analyser les plans d'exécution

## Introduction
`EXPLAIN` montre le plan d'exécution d'une requête : comment le moteur SQL la traite.

## Syntaxe
```sql
EXPLAIN
SELECT *
FROM olist_orders_dataset
WHERE year = 2025;
```

## Lecture d'un plan EXPLAIN
Opérations courantes :
- `SEQ_SCAN` : scan complet (lent si table grande)
- `INDEX_SCAN` / `INDEX_LOOKUP` : utilise un index (rapide)
- `HASH_JOIN` (Join avec table de hachage - rapide) / `NESTED_LOOP_JOIN` (Boucles imbriquées - lent) / `MERGE_JOIN` (Fusion de tables triées) : types de jointures
- `FILTER` (Application de WHERE), `PROJECTION` (Sélection de colonnes), `AGGREGATE` (GROUP BY, SUM, COUNT), `ORDER` (Tri ORDER BY): étapes classiques

## EXPLAIN ANALYZE - Avec timing réel
```sql
EXPLAIN ANALYZE
SELECT
    o.order_id,
    SUM(oi.price + oi.freight_value) AS order_total
FROM olist_orders_dataset o
JOIN olist_order_items_dataset oi ON oi.order_id = o.order_id
WHERE o.order_purchase_timestamp >= '2018-01-01'
GROUP BY o.order_id;
```

Affiche :
- Plan d'exécution
- Temps réel
- Nombre de lignes traitées
- Mémoire utilisée

## Identifier les problèmes
### Problème 1 : scan complet
```sql
EXPLAIN
SELECT *
FROM olist_orders_dataset
WHERE year = 2025;
```
-- Résultat : SEQ_SCAN (mauvais si table grande)

Solution : créer un index sur `year`.

### Problème 2 : jointure coûteuse (Nested loop join)
```sql
EXPLAIN
SELECT o.order_id, oi.product_id
FROM olist_orders_dataset o
JOIN olist_order_items_dataset oi ON oi.order_id = o.order_id;
```
Solution : indexer les colonnes de jointure (`order_id`, `product_id` selon besoin).

### Problème 3 : tri coûteux (Sort sans index)
```sql
EXPLAIN
SELECT order_id, order_purchase_timestamp
FROM olist_orders_dataset
ORDER BY age DESC;
```
Solution : index sur `age` ou accepter le tri.

## Coûts estimés
Le moteur estime un coût par opération (ex. `cost=123 rows=456`).
Plus le coût est bas, mieux c'est.

## Exercice
Comparez les plans de :

```sql
-- Requête 1
SELECT *
FROM olist_orders_dataset
WHERE order_status = 'delivered';

-- Requête 2
SELECT order_id, customer_id
FROM olist_orders_dataset
WHERE order_status = 'delivered';
```

Solution

La requête 2 est plus rapide pour les raisons suivantes :
Moins de colonnes à lire (projection réduite)
Moins de données à transférer
Même nombre d’analyses, mais charge de travail moindre

Résumé
- EXPLAIN : Afficher le plan d’exécution 
- EXPLAIN ANALYZE : Temps d’exécution réel 
- SEQ_SCAN : Lent (analyse complète de la table) 
- INDEX_SCAN : Rapide (utilisation de l’index) 
- Coût : Comparer les plans d’exécution

﻿# Analyse des requêtes (EXPLAIN)

Pour optimiser les requêtes, il est essentiel de comprendre comment le moteur de base de données les exécute.

## 1. EXPLAIN et EXPLAIN ANALYZE

- `EXPLAIN` : Affiche le plan d'exécution prévu par l'optimiseur.
- `EXPLAIN ANALYZE` : Exécute réellement la requête et affiche les statistiques correspondantes.

```sql
EXPLAIN ANALYZE
SELECT
o.order_id,
o.order_purchase_timestamp,
SUM(oi.price + oi.freight_value) AS order_total
FROM olist_orders_dataset o
JOIN olist_order_items_dataset oi ON oi.order_id = o.order_id
WHERE o.customer_id = '9ef432eb6251297304e76186b10a928d'
GROUP BY o.order_id, o.order_purchase_timestamp
ORDER BY o.order_purchase_timestamp DESC;
```

## 2. Analyse séquentielle (Seq Scan) vs. Analyse par index (Index Scan)

- **Analyse séquentielle** : Lit l'intégralité de la table (plus lente avec des millions de lignes).

- **Analyse d'index** : Utilise un index pour un accès ciblé presque instantané.

﻿# Bonnes pratiques SQL

## Principe général
Règle d'or : faire le moins de travail possible.

- Filtrer tôt (`WHERE` avant `JOIN`)
- Sélectionner peu de colonnes
- Limiter les résultats (`LIMIT`)

## 1. Sélection de colonnes
Mauvais :
```sql
SELECT *
FROM olist_orders_dataset;
```
Problèmes :
Lit toutes les colonnes (inutile)
Transfert de données volumineux
Cache moins efficace

Bon :
```sql
SELECT order_id, customer_id, order_purchase_timestamp
FROM olist_orders_dataset;
```

Testez les deux !

## 2. Filtrage WHERE
Mauvais :
```sql
SELECT customer_id
FROM olist_customers_dataset
WHERE UPPER(customer_state) = 'SP';
```

Problème : Fonction sur colonne → Index inutilisable

Bon :
```sql
SELECT customer_id
FROM olist_customers_dataset
WHERE customer_state = 'Sp';
```
OU stocker déjà en uppercase.
!! éviter les fonctions sur les colonnes filtrées (dans le WHERE) pour permettre l'utilisation d'index.

## 3. ORDER BY et LIMIT
Mauvais :
```sql
SELECT order_id, order_purchase_timestamp
FROM olist_orders_dataset
ORDER BY order_purchase_timestamp DESC;
```
-- Trie TOUS les commandes alors qu'on en veut 100

Bon :
```sql
SELECT order_id, order_purchase_timestamp
FROM olist_orders_dataset
ORDER BY order_purchase_timestamp DESC
LIMIT 100;
```
-- Optimiseur peut arrêter après 100

## 4. JOIN efficaces
Mauvais :
```sql
SELECT *
FROM olist_orders_dataset o, olist_order_items_dataset oi
WHERE o.order_id = oi.order_id;
```
-- Cartesian product puis filtre (lent)

Bon :
```sql
SELECT o.order_id, o.customer_id, oi.product_id, oi.price
FROM olist_orders_dataset o
JOIN olist_order_items_dataset oi ON oi.order_id = o.order_id;
```
-- JOIN explicite (optimisé)

## 5. Sous-requêtes vs CTE
Mauvais (si calcul répété) :
```sql
SELECT op.order_id, op.payment_value
FROM olist_order_payments_dataset op
WHERE op.payment_value > (
    SELECT AVG(payment_value) FROM olist_order_payments_dataset
)
AND EXISTS (
    SELECT 1
    FROM olist_order_payments_dataset op2
    WHERE op2.order_id = op.order_id
      AND op2.payment_value > (
          SELECT AVG(payment_value) FROM olist_order_payments_dataset
      )
);
```
Problème : Calcule AVG plusieurs fois

Bon :
```sql
WITH avg_payment AS (
    SELECT AVG(payment_value) AS avg_value
    FROM olist_order_payments_dataset
)
SELECT op.order_id, op.payment_value
FROM olist_order_payments_dataset op
CROSS JOIN avg_payment ap
WHERE op.payment_value > ap.avg_value;
```
Calcul de AVG une fois, plus lisible.

## 6. EXISTS vs IN
Quand utiliser `EXISTS` (grand volume/table) :
```sql
SELECT o.order_id
FROM olist_orders_dataset o
WHERE EXISTS (
    SELECT 1
    FROM olist_order_items_dataset oi
    JOIN olist_sellers_dataset s ON s.seller_id = oi.seller_id
    WHERE oi.order_id = o.order_id
      AND s.seller_state = 'SP'
);
```
S'arrête dès qu'une ligne est trouvée, plus rapide pour grandes tables.

Quand utiliser `IN` (petite liste) :
```sql
SELECT order_id
FROM olist_orders_dataset
WHERE order_status IN ('delivered', 'shipped');
```
Liste courte, évaluation rapide.

## 7. DISTINCT vs GROUP BY
`DISTINCT` simple (moins efficace) :
```sql
SELECT DISTINCT customer_state
FROM olist_customers_dataset;
```

`GROUP BY` (plus efficace si agrégation) :
```sql
SELECT customer_state, COUNT(*)
FROM olist_customers_dataset
GROUP BY customer_state;
```

## 8. Éviter les NOT IN avec NULL
Dangereux :
```sql
SELECT o.order_id
FROM olist_orders_dataset o
WHERE o.order_id NOT IN (
    SELECT r.order_id
    FROM olist_order_reviews_dataset r
);
```
Si `olist_order_reviews_dataset` contient des `order_id` NULL, la requête ne retournera aucun résultat.

Sûr :
```sql
SELECT o.order_id
FROM olist_orders_dataset o
WHERE NOT EXISTS (
    SELECT 1
    FROM olist_order_reviews_dataset r
    WHERE r.order_id = o.order_id
);
```
OU
```sql
SELECT o.order_id
FROM olist_orders_dataset oWHERE o.order_id NOT IN (
    SELECT r.order_id
    FROM olist_order_reviews_dataset r
    WHERE r.order_id IS NOT NULL
);
```

## 9. Préférer CTE aux sous-requêtes imbriquées
Difficile à lire :
```sql
SELECT order_id, customer_id
FROM (
    SELECT order_id, customer_id, order_purchase_timestamp
    FROM (
        SELECT *
        FROM olist_orders_dataset
        WHERE order_status = 'delivered'
    ) t1
    WHERE order_purchase_timestamp >= '2018-01-01'
) t2;
```

Lisible :
```sql
WITH delivered_orders AS (
    SELECT order_id, customer_id, order_purchase_timestamp
    FROM olist_orders_dataset
    WHERE order_status = 'delivered'
),
recent_orders AS (
    SELECT order_id, customer_id
    FROM delivered_orders
    WHERE order_purchase_timestamp >= '2018-01-01'
)
SELECT order_id, customer_id
FROM recent_orders;
```

## 10. LIMIT pour tests
```sql
-- Développement
SELECT * FROM olist_order_items_dataset LIMIT 10;

-- Production (si besoin de tout)
SELECT * FROM olist_order_items_dataset;
```

## Checklist performance
- Ai-je besoin de toutes ces colonnes ?
- Puis-je filtrer plus tôt ?
- Ai-je un `LIMIT` approprié ?
- Mes colonnes de `WHERE/JOIN` sont-elles indexées ?
- Ai-je testé avec `EXPLAIN` ?
- Mes CTE évitent-elles les recalculs ?

## Exercice
Optimisez cette requête :
```sql
SELECT *
FROM olist_orders_dataset
WHERE UPPER(order_status) = 'DELIVERED'
ORDER BY order_purchase_timestamp DESC;
```

Solution possible :
```sql
SELECT order_id, customer_id, order_status, order_purchase_timestamp -- Pas SELECT *
FROM olist_orders_dataset
WHERE order_status = 'delivered' -- Pas UPPER() sur colonne
ORDER BY order_purchase_timestamp DESC
LIMIT 100; -- Ajouter LIMIT si pas besoin de tout
```

Résumé
- Sélectionner uniquement les colonnes nécessaires
- Filtrer tôt et éviter les fonctions sur les colonnes filtrées
- Limiter les résultats pour les tests et si pas besoin de tout
- Utiliser des JOIN explicites avec des colonnes indexées
- Préférer les CTE pour la lisibilité/réutilisation et éviter les recalculs
- Utiliser EXISTS pour les grandes tables, IN pour les petites listes

﻿# Performance avancée et monitoring

## Introduction
Techniques avancées pour maximiser les performances SQL et surveiller la santé de vos requêtes.

## 1. Partitionnement
Diviser une grande table en partitions plus petites.

```sql
-- Illustration : partitionnement annuel
-- olist_orders_2016, olist_orders_2017, olist_orders_2018

SELECT *
FROM olist_orders_dataset
WHERE order_purchase_timestamp >= '2018-01-01'
  AND order_purchase_timestamp < '2019-01-01';
```

Avantages :
- Scan plus rapide
- Maintenance par partition (`VACUUM`, `ANALYZE`)
- Archivage simplifié

## 2. Materialized Views (vues matérialisées)
Pré-calculer des agrégations coûteuses.

```sql
CREATE MATERIALIZED VIEW mv_olist_sales_by_category_month AS
SELECT
    DATE_TRUNC('month', o.order_purchase_timestamp) AS month_start,
    p.product_category_name,
    SUM(oi.price + oi.freight_value) AS sales_amount,
    COUNT(DISTINCT o.order_id) AS orders_count
FROM olist_orders_dataset o
JOIN olist_order_items_dataset oi ON oi.order_id = o.order_id
JOIN olist_products_dataset p ON p.product_id = oi.product_id
GROUP BY 1, 2;

SELECT *
FROM mv_olist_sales_by_category_month;
```

Mise à jour :
```sql
REFRESH MATERIALIZED VIEW mv_olist_sales_by_category_month;
```

## 3. Cache et pagination
Mauvais (`OFFSET` lent) :
```sql
SELECT order_id, order_purchase_timestamp
FROM olist_orders_dataset
ORDER BY order_purchase_timestamp DESC, order_id DESC
OFFSET 10000 LIMIT 100;
```
-- Lit 10100 lignes, garde 100.

Bon (keyset pagination) :
```sql
-- Page 1
SELECT order_id, order_purchase_timestamp
FROM olist_orders_dataset
ORDER BY order_purchase_timestamp DESC, order_id DESC
LIMIT 100;

-- Page suivante avec curseur
SELECT order_id, order_purchase_timestamp
FROM olist_orders_dataset
WHERE (order_purchase_timestamp, order_id) < ('2018-08-01 10:00:00', 'f9e4b658b201a9f2ecdecbb34bed034b')
ORDER BY order_purchase_timestamp DESC, order_id DESC
LIMIT 100;
```

## 4. Batch processing
Traiter par lots au lieu d'une transaction géante.

-- Mauvais : UPDATE 1M lignes en 1 fois
```sql
UPDATE olist_order_items_dataset
SET freight_value = freight_value * 1.02;
```

-- Bon : Par lots de 1000
```sql
UPDATE olist_order_items_dataset
SET freight_value = freight_value * 1.02
WHERE order_id IN (
    SELECT order_id
    FROM olist_orders_dataset
    ORDER BY order_purchase_timestamp
    LIMIT 1000 OFFSET 0
);
```
-- Répéter avec OFFSET 1000, 2000, etc.

## 5. Vacuum et maintenance
```sql
VACUUM; -- Nettoyer l'espace disque 
VACUUM ANALYZE; -- Réorganiser les données et mettre à jour les statistiques pour l'optimiseur
```
Quand : après gros `DELETE/UPDATE`.

## 6. Checklist monitoring
À surveiller :
- Temps moyen d'exécution par type de requête
- Nombre de scans complets : `SEQ_SCAN`
- Ratio cache hit/miss
- Croissance de la base
- Nombre de requêtes lentes (>5s)

## 7. Cas d'étude : optimisation réelle
Avant :
-- 10M lignes, 30 secondes
```sql
SELECT *
FROM olist_orders_dataset
WHERE year = 2025
ORDER BY order_purchase_timestamp DESC;
```

Problèmes :
- `SELECT *` (trop de colonnes)
- Pas d'index sur `year`
- Scan complet

Après :
-- Ajout index
```sql
CREATE INDEX idx_olist_orders_year_purchase
ON olist_orders_dataset(year, order_purchase_timestamp DESC);

-- Requête optimisée
SELECT order_id, order_purchase_timestamp, order_status
FROM olist_orders_dataset
WHERE year = 2025
ORDER BY order_purchase_timestamp DESC
LIMIT 100;
```
-- Résultat : 0.05 secondes (600x plus rapide !)

## Exercice final : optimisation complète
Optimisez cette requête :
```sql
SELECT *
FROM olist_order_items_dataset oi
WHERE oi.product_id IN (
    SELECT p.product_id
    FROM olist_products_dataset p
    WHERE UPPER(p.product_category_name) = 'CAMA_MESA_BANHO'
)
ORDER BY oi.price DESC;
```

Solution possible :
```sql
-- 1. Index
CREATE INDEX idx_olist_products_category
ON olist_products_dataset(product_category_name);

CREATE INDEX idx_olist_order_items_product_price
ON olist_order_items_dataset(product_id, price DESC);

-- 2. Requête optimisée
WITH target_products AS (
    SELECT product_id
    FROM olist_products_dataset
    WHERE product_category_name = 'cama_mesa_banho'
)
SELECT oi.order_id, oi.product_id, oi.price, oi.freight_value
FROM olist_order_items_dataset oi
JOIN target_products tp ON tp.product_id = oi.product_id
ORDER BY oi.price DESC
LIMIT 100;
```

Améliorations :
- Colonnes spécifiques (pas *)
- CTE pour éviter la sous-requête imbriquée
- Pas de fonction sur `product_category_name` (pas UPPER())
- Limit pour pagination
- Index sur les colonnes utilisées dans le JOIN et l'ORDER BY

Résumé
- Partitionnement : Diviser les grandes tables pour accélérer les scans
- Vues matérialisées : Pré-calculer les agrégations
- Pagination : Préférer la keyset pagination au OFFSET

﻿# 01 - Les Vues (Views)

Une vue est une requête SQL sauvegardée que vous pouvez interroger comme une table.

## 1. Création d'une vue
```sql
CREATE VIEW v_olist_customers_sp AS
SELECT
    c.customer_id,
    c.customer_unique_id,
    c.customer_city,
    COUNT(o.order_id) AS nb_orders
FROM olist_customers_dataset c
LEFT JOIN olist_orders_dataset o ON o.customer_id = c.customer_id
WHERE c.customer_state = 'SP'
GROUP BY c.customer_id, c.customer_unique_id, c.customer_city;
```

## 2. Vues Matérialisées
Contrairement à une vue classique, elle stocke physiquement les données du résultat. Utile pour les calculs lourds qui ne changent pas souvent. 
!! Ne pas oublier de mettre à jour si nécessaire.

```sql
-- Syntaxe Postgres/DuckDB
CREATE MATERIALIZED VIEW mv_olist_monthly_sales AS
SELECT
    DATE_TRUNC('month', o.order_purchase_timestamp) AS month_start,
    SUM(oi.price + oi.freight_value) AS total_sales,
    COUNT(DISTINCT o.order_id) AS nb_orders
FROM olist_orders_dataset o
JOIN olist_order_items_dataset oi ON oi.order_id = o.order_id
GROUP BY 1;

-- Mise à jour
REFRESH MATERIALIZED VIEW mv_olist_monthly_sales;
```

# 02 - Transactions et ACID

Les transactions garantissent que plusieurs opérations sont traitées comme une seule unité atomique.

## 1. Propriétés ACID
- **A**tomicity : tout ou rien.
- **C**onsistency : cohérence des données.
- **I**solation : les transactions ne s'interfèrent pas.
- **D**urability : persistance après validation.

## 2. Syntaxe
```sql
BEGIN; -- Démarre une transaction

UPDATE olist_orders_dataset
SET order_status = 'shipped'
WHERE order_id = 'e481f51cbdc54678b7cc49136f2d6af7';

UPDATE olist_order_payments_dataset
SET payment_value = payment_value - 5
WHERE order_id = 'e481f51cbdc54678b7cc49136f2d6af7';

COMMIT; -- Valide les changements
-- OU
ROLLBACK; -- Annule tout si un problème est survenu
```