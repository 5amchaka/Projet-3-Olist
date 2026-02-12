"""
Structure de données centrale pour le cours SQL avancé.

Ce module définit :
- Les dataclasses pour représenter le contenu pédagogique
- Les 5 modules du cours (15 leçons au total)
- L'index des 30+ concepts SQL annotables
- La cartographie des requêtes SQL existantes vers les leçons
"""

from dataclasses import dataclass
from typing import Callable, Literal
import pandas as pd


# ============================================================================
# DATACLASSES
# ============================================================================

@dataclass
class SQLConcept:
    """Représente un concept SQL annoté dans le code."""
    keyword: str  # "LAG", "NTILE", "WITH"
    name: str  # "LAG() OVER (ORDER BY ...)"
    short_desc: str  # Tooltip (1 phrase)
    detailed_desc: str  # Panel détaillé (markdown)
    example_sql: str  # Code SQL minimal
    category: Literal["aggregate", "window", "cte", "join", "index", "function"]


@dataclass
class Exercise:
    """Représente un exercice SQL interactif."""
    id: str  # "beginner_ex1_select"
    title: str
    description: str  # Énoncé markdown
    starter_sql: str  # Code de départ
    solution_sql: str  # Solution référence
    validator: Callable[[pd.DataFrame], tuple[bool, str]]  # (success, message)
    hint: str | None = None


@dataclass
class Lesson:
    """Représente une leçon du cours."""
    title: str
    theory: str  # Markdown ~200-300 mots
    concepts: list[SQLConcept]  # Concepts annotables
    demo_sql_file: str  # Requête existante (ex: "trends_monthly.sql")
    exercise: Exercise | None = None
    exploration_link: str | None = None  # Lien page ("/ventes", etc.)


@dataclass
class Module:
    """Représente un module du cours."""
    id: str  # "module_1_fundamentals"
    icon: str  # Material icon
    title: str
    subtitle: str
    lessons: list[Lesson]
    estimated_duration_min: int


# ============================================================================
# INDEX DES CONCEPTS SQL
# ============================================================================

CONCEPTS_INDEX: dict[str, SQLConcept] = {
    # === BASICS ===
    "SELECT": SQLConcept(
        keyword="SELECT",
        name="SELECT - Projection",
        short_desc="Sélectionne les colonnes à afficher dans le résultat",
        detailed_desc="""## SELECT : Projection des colonnes

La clause `SELECT` définit quelles colonnes apparaîtront dans le résultat de la requête.

**Bonnes pratiques** :
- ✅ Lister explicitement les colonnes nécessaires
- ❌ Éviter `SELECT *` en production (performances + sécurité)
- ✅ Utiliser des alias clairs avec `AS`
""",
        example_sql="SELECT order_id, order_status, price FROM fact_orders",
        category="aggregate"
    ),

    "WHERE": SQLConcept(
        keyword="WHERE",
        name="WHERE - Filtrage",
        short_desc="Filtre les lignes selon une condition",
        detailed_desc="""## WHERE : Filtrage des lignes

La clause `WHERE` s'applique **avant** l'agrégation. Elle filtre les lignes sources.

**Opérateurs courants** :
- `=`, `!=`, `<`, `>`, `<=`, `>=`
- `IN (...)`, `NOT IN (...)`
- `BETWEEN ... AND ...`
- `LIKE '%pattern%'`
- `IS NULL`, `IS NOT NULL`
""",
        example_sql="WHERE order_status = 'delivered' AND date_key BETWEEN 20170101 AND 20171231",
        category="aggregate"
    ),

    "JOIN": SQLConcept(
        keyword="JOIN",
        name="JOIN - Jointures",
        short_desc="Combine plusieurs tables selon une clé commune",
        detailed_desc="""## JOIN : Combinaison de tables

Les jointures relient les dimensions au fait dans un schéma en étoile.

**Types** :
- `INNER JOIN` : Garde uniquement les correspondances (le plus courant)
- `LEFT JOIN` : Garde toutes les lignes de gauche
- `RIGHT JOIN` : Garde toutes les lignes de droite
- `FULL OUTER JOIN` : Garde tout (rarement utile)

**Performance** : Toujours joindre sur des colonnes indexées (clés étrangères).
""",
        example_sql="""SELECT o.order_id, c.state
FROM fact_orders o
INNER JOIN dim_customers c ON o.customer_key = c.customer_key""",
        category="join"
    ),

    "GROUP BY": SQLConcept(
        keyword="GROUP BY",
        name="GROUP BY - Agrégation",
        short_desc="Regroupe les lignes pour calculer des agrégats",
        detailed_desc="""## GROUP BY : Regroupement

Agrège les lignes partageant les mêmes valeurs dans les colonnes de regroupement.

**Règle d'or** : Toute colonne dans `SELECT` qui n'est PAS dans une fonction d'agrégation DOIT être dans `GROUP BY`.

**Agrégats courants** :
- `COUNT(*)`, `COUNT(DISTINCT col)`
- `SUM(col)`, `AVG(col)`
- `MIN(col)`, `MAX(col)`
""",
        example_sql="""SELECT c.state, COUNT(DISTINCT o.order_id) as nb_orders, SUM(o.price) as total_revenue
FROM fact_orders o
INNER JOIN dim_customers c ON o.customer_key = c.customer_key
GROUP BY c.state""",
        category="aggregate"
    ),

    # === WINDOW FUNCTIONS ===
    "LAG": SQLConcept(
        keyword="LAG",
        name="LAG() OVER (ORDER BY ...)",
        short_desc="Accède à la valeur de la ligne précédente",
        detailed_desc="""## LAG : Accès à la ligne précédente

`LAG(colonne, offset)` retourne la valeur de `colonne` située `offset` lignes **avant** la ligne courante.

**Usage typique** : Calculs de croissance (MoM, YoY).

**Exemple** : Variation mensuelle du CA
```sql
SELECT
    month,
    revenue,
    LAG(revenue, 1) OVER (ORDER BY month) as prev_month_revenue,
    (revenue - LAG(revenue, 1) OVER (ORDER BY month)) / NULLIF(LAG(revenue, 1) OVER (ORDER BY month), 0) * 100 as growth_pct
FROM monthly_sales
```
""",
        example_sql="LAG(revenue, 1) OVER (ORDER BY year, month)",
        category="window"
    ),

    "LEAD": SQLConcept(
        keyword="LEAD",
        name="LEAD() OVER (ORDER BY ...)",
        short_desc="Accède à la valeur de la ligne suivante",
        detailed_desc="""## LEAD : Accès à la ligne suivante

Symétrique de `LAG`, retourne la valeur `offset` lignes **après** la ligne courante.

**Usage** : Calculs forward-looking (ex: délai jusqu'au prochain achat).
""",
        example_sql="LEAD(date_key, 1) OVER (PARTITION BY customer_key ORDER BY date_key)",
        category="window"
    ),

    "ROW_NUMBER": SQLConcept(
        keyword="ROW_NUMBER",
        name="ROW_NUMBER() OVER (ORDER BY ...)",
        short_desc="Attribue un numéro séquentiel unique à chaque ligne",
        detailed_desc="""## ROW_NUMBER : Numérotation séquentielle

Attribue un rang **unique** (1, 2, 3...) à chaque ligne selon l'ordre spécifié.

**Usage typique** : Top N par groupe.

**Exemple** : Top 3 produits par catégorie
```sql
WITH ranked AS (
    SELECT
        category,
        product_name,
        revenue,
        ROW_NUMBER() OVER (PARTITION BY category ORDER BY revenue DESC) as rank
    FROM product_sales
)
SELECT * FROM ranked WHERE rank <= 3
```
""",
        example_sql="ROW_NUMBER() OVER (PARTITION BY category ORDER BY revenue DESC)",
        category="window"
    ),

    "NTILE": SQLConcept(
        keyword="NTILE",
        name="NTILE(n) OVER (ORDER BY ...)",
        short_desc="Divise les lignes en n groupes égaux (quintiles, quartiles)",
        detailed_desc="""## NTILE : Distribution en buckets

`NTILE(n)` répartit les lignes en `n` groupes de taille égale.

**Usages courants** :
- `NTILE(4)` : Quartiles (Q1, Q2, Q3, Q4)
- `NTILE(5)` : Quintiles (segmentation RFM, Pareto)
- `NTILE(10)` : Déciles

**Exemple** : Segmentation clients par montant
```sql
SELECT
    customer_id,
    total_spent,
    NTILE(5) OVER (ORDER BY total_spent DESC) as quintile
FROM customer_totals
```

Le quintile 1 = top 20%, quintile 5 = bottom 20%.
""",
        example_sql="NTILE(5) OVER (ORDER BY revenue DESC) as quintile",
        category="window"
    ),

    "PARTITION BY": SQLConcept(
        keyword="PARTITION BY",
        name="PARTITION BY - Groupes de fenêtre",
        short_desc="Divise le jeu de données en partitions indépendantes pour les window functions",
        detailed_desc="""## PARTITION BY : Regroupement pour window functions

`PARTITION BY` est l'équivalent de `GROUP BY` pour les window functions.

**Différence clé** :
- `GROUP BY` : Réduit le nombre de lignes (1 ligne par groupe)
- `PARTITION BY` : Garde toutes les lignes, calcule sur chaque partition

**Exemple** : Rang par catégorie
```sql
SELECT
    category,
    product_name,
    revenue,
    RANK() OVER (PARTITION BY category ORDER BY revenue DESC) as rank_in_category
FROM products
```

Chaque catégorie a son propre classement (1, 2, 3...).
""",
        example_sql="ROW_NUMBER() OVER (PARTITION BY state ORDER BY revenue DESC)",
        category="window"
    ),

    # === CTEs ===
    "WITH": SQLConcept(
        keyword="WITH",
        name="WITH - Common Table Expressions",
        short_desc="Définit une table temporaire (CTE) pour améliorer la lisibilité",
        detailed_desc="""## WITH : Common Table Expressions (CTEs)

Les CTEs créent des "tables temporaires" nommées utilisables dans la requête principale.

**Avantages** :
- ✅ Lisibilité (vs sous-requêtes imbriquées)
- ✅ Réutilisation (référencer plusieurs fois)
- ✅ Chaînage (CTE2 utilise CTE1)

**Exemple** : Calcul RFM en 3 étapes
```sql
WITH rfm_raw AS (
    SELECT customer_unique_id, ... FROM rfm_base
),
rfm_scored AS (
    SELECT *, NTILE(5) OVER (...) as r_score FROM rfm_raw
),
rfm_final AS (
    SELECT *, CASE WHEN ... END as segment FROM rfm_scored
)
SELECT * FROM rfm_final
```
""",
        example_sql="""WITH monthly_sales AS (
    SELECT month_label as month, monthly_revenue as revenue
    FROM v_monthly_sales
)
SELECT * FROM monthly_sales""",
        category="cte"
    ),

    "CASE WHEN": SQLConcept(
        keyword="CASE WHEN",
        name="CASE WHEN - Logique conditionnelle",
        short_desc="Applique une logique if/then/else dans SQL",
        detailed_desc="""## CASE WHEN : Conditions

Équivalent du `if/else` en SQL.

**Syntaxe** :
```sql
CASE
    WHEN condition1 THEN valeur1
    WHEN condition2 THEN valeur2
    ELSE valeur_par_defaut
END
```

**Usages** :
- Classification (segments, flags)
- Agrégation conditionnelle : `SUM(CASE WHEN ... THEN 1 ELSE 0 END)`
- Transformation de données
""",
        example_sql="""CASE
    WHEN score >= 80 THEN 'Premium'
    WHEN score >= 50 THEN 'Standard'
    ELSE 'At Risk'
END as segment""",
        category="function"
    ),

    # === AGGREGATES ===
    "COUNT": SQLConcept(
        keyword="COUNT",
        name="COUNT - Comptage",
        short_desc="Compte le nombre de lignes ou valeurs non-NULL",
        detailed_desc="""## COUNT : Comptage

- `COUNT(*)` : Compte toutes les lignes (y compris NULL)
- `COUNT(colonne)` : Compte les valeurs non-NULL
- `COUNT(DISTINCT colonne)` : Compte les valeurs uniques

**Piège fréquent** : `COUNT(colonne)` ignore les NULL !
""",
        example_sql="SELECT COUNT(*) as total_items, COUNT(DISTINCT order_id) as total_orders FROM fact_orders",
        category="aggregate"
    ),

    "SUM": SQLConcept(
        keyword="SUM",
        name="SUM - Somme",
        short_desc="Additionne les valeurs numériques",
        detailed_desc="""## SUM : Sommation

Calcule la somme des valeurs numériques. Ignore les NULL.

**Window function** : `SUM() OVER (...)` calcule des totaux glissants.

**Exemple** : Cumul mensuel
```sql
SELECT
    month,
    revenue,
    SUM(revenue) OVER (ORDER BY month ROWS UNBOUNDED PRECEDING) as cumulative
FROM monthly_sales
```
""",
        example_sql="SUM(price) as total_revenue",
        category="aggregate"
    ),

    # === INDEX ===
    "CREATE INDEX": SQLConcept(
        keyword="CREATE INDEX",
        name="CREATE INDEX - Optimisation",
        short_desc="Crée un index B-Tree pour accélérer les recherches",
        detailed_desc="""## CREATE INDEX : Indexation

Les index accélèrent les recherches sur les colonnes indexées (WHERE, JOIN).

**Structure** : B-Tree (arbre équilibré) → recherche en O(log n) vs scan O(n).

**Quand indexer** :
- ✅ Colonnes de filtrage fréquentes (WHERE, JOIN)
- ✅ Clés étrangères
- ✅ Colonnes de tri (ORDER BY)
- ❌ Colonnes peu sélectives (ex: booléens)
- ❌ Tables < 1000 lignes (overhead inutile)

**Exemple** :
```sql
CREATE INDEX idx_fact_date_key ON fact_orders(date_key);
CREATE INDEX idx_fact_order_status ON fact_orders(order_status);
```
""",
        example_sql="CREATE INDEX idx_fact_date_key ON fact_orders(date_key);",
        category="index"
    ),

    "EXPLAIN": SQLConcept(
        keyword="EXPLAIN",
        name="EXPLAIN QUERY PLAN",
        short_desc="Affiche le plan d'exécution d'une requête",
        detailed_desc="""## EXPLAIN QUERY PLAN : Analyse de performance

Affiche comment SQLite exécute la requête.

**Mots-clés critiques** :
- 🔴 `SCAN TABLE` : Parcours complet (lent)
- 🟢 `SEARCH TABLE ... USING INDEX` : Utilise un index (rapide)
- 🟡 `SEARCH TABLE ... USING AUTOMATIC COVERING INDEX` : Index temporaire (moyen)

**Workflow** :
1. `EXPLAIN QUERY PLAN SELECT ...`
2. Identifier les SCAN
3. Créer des index sur les colonnes filtrées/jointes
4. Re-EXPLAIN pour vérifier l'amélioration
""",
        example_sql="EXPLAIN QUERY PLAN SELECT * FROM fact_orders WHERE date_key >= 20170101;",
        category="index"
    ),

    "JULIANDAY": SQLConcept(
        keyword="JULIANDAY",
        name="JULIANDAY - Calcul temporel",
        short_desc="Convertit une date en nombre de jours depuis 4714 BC (SQLite)",
        detailed_desc="""## JULIANDAY : Arithmétique de dates

SQLite n'a pas de type DATE natif. `JULIANDAY` convertit les dates en flottants pour calculer des différences.

**Exemple** : Nombre de jours entre deux dates
```sql
SELECT
    customer_unique_id,
    JULIANDAY('now') - JULIANDAY(last_order_date) as days_since_last_order
FROM customer_last_orders
```

**Alternative** : `STRFTIME` pour extraire composants (année, mois).
""",
        example_sql="JULIANDAY('now') - JULIANDAY(order_date) as recency_days",
        category="function"
    ),

    # === OPTIMIZATION ===
    "MATERIALIZED": SQLConcept(
        keyword="MATERIALIZED",
        name="WITH ... AS MATERIALIZED",
        short_desc="Force l'exécution unique d'une CTE (optimisation)",
        detailed_desc="""## MATERIALIZED : CTEs matérialisées

Par défaut, SQLite peut réévaluer une CTE à chaque référence (inline).

`MATERIALIZED` force l'évaluation **une seule fois** et stocke le résultat temporairement.

**Quand utiliser** :
- ✅ CTE référencée plusieurs fois
- ✅ CTE coûteuse (agrégations, jointures complexes)
- ❌ CTE utilisée une seule fois (overhead inutile)

**Exemple** :
```sql
WITH customer_stats AS MATERIALIZED (
    SELECT customer_key, SUM(price) as total FROM fact_orders GROUP BY customer_key
)
SELECT * FROM customer_stats WHERE total > 1000
UNION ALL
SELECT * FROM customer_stats WHERE total < 100
```
""",
        example_sql="WITH stats AS MATERIALIZED (...)",
        category="cte"
    ),
}


# ============================================================================
# MODULES DU COURS - 5 modules × 3 leçons = 15 leçons
# ============================================================================

from .exercises import (
    get_beginner_ex1_validator,
    get_beginner_ex2_validator,
    get_beginner_ex3_validator,
    get_intermediate_ex1_validator,
    get_intermediate_ex2_validator,
    get_intermediate_ex3_validator,
    get_advanced_ex1_validator,
    get_advanced_ex2_validator,
    get_advanced_ex3_validator,
)


# === MODULE 1 : FONDAMENTAUX SQL ===

module_1 = Module(
    id="module_1_fundamentals",
    icon="school",
    title="Fondamentaux SQL",
    subtitle="SELECT, JOIN, GROUP BY - Les bases du requêtage",
    estimated_duration_min=25,
    lessons=[
        Lesson(
            title="SELECT, WHERE, ORDER BY - Anatomie d'une requête",
            theory="""## Les fondations du SQL

Toute requête SQL commence par trois clauses fondamentales :
- **SELECT** : Quelles colonnes afficher (projection)
- **WHERE** : Quelles lignes garder (filtrage)
- **ORDER BY** : Dans quel ordre afficher les résultats (tri)

### Ordre d'exécution
L'ordre d'écriture (SELECT → WHERE → ORDER BY) diffère de l'ordre d'exécution réel :
1. **FROM** : Identifier la table source
2. **WHERE** : Filtrer les lignes (avant agrégation)
3. **SELECT** : Projeter les colonnes
4. **ORDER BY** : Trier le résultat final

### Bonnes pratiques
- ✅ Toujours lister explicitement les colonnes (éviter `SELECT *`)
- ✅ Utiliser des alias clairs (`AS monthly_revenue`)
- ✅ Indexer les colonnes filtrées dans WHERE pour de meilleures performances
- ✅ Filtrer tôt pour réduire le volume de données

Dans le Data Warehouse Olist, vous travaillerez principalement avec la table centrale `fact_orders` (112k lignes, grain article). Le filtrage temporel se fait via `date_key` (ou via `v_orders_enriched` qui expose `order_date`) et le filtrage de statut via `order_status`.
""",
            concepts=[
                CONCEPTS_INDEX["SELECT"],
                CONCEPTS_INDEX["WHERE"],
                CONCEPTS_INDEX["COUNT"],
            ],
            demo_sql_file="overview_monthly_mini.sql",
            exercise=Exercise(
                id="beginner_ex1_select",
                title="Filtrer et trier les commandes",
                description="""## Exercice : Filtrage et tri basiques

**Objectif** : Extraire les commandes livrées en 2017, triées par prix décroissant.

**Consignes** :
1. Sélectionner uniquement les colonnes : `order_id`, `order_date`, `price`
2. Filtrer sur `order_status = 'delivered'` ET `order_date >= '2017-01-01'` ET `order_date < '2018-01-01'`
3. Trier par prix décroissant (`ORDER BY price DESC`)
4. Le résultat doit contenir au moins 50 lignes

**Source conseillée** : `v_orders_enriched` (inclut `order_date`, `order_status`, `price`)
""",
                starter_sql="""-- Filtrer les commandes livrées en 2017, tri prix DESC
SELECT
    -- Vos colonnes ici

FROM v_orders_enriched
WHERE
    -- Vos conditions ici

ORDER BY -- Votre tri ici
""",
                solution_sql="""SELECT
    order_id,
    order_date,
    price
FROM v_orders_enriched
WHERE
    order_status = 'delivered'
    AND order_date >= '2017-01-01'
    AND order_date < '2018-01-01'
ORDER BY price DESC
""",
                validator=get_beginner_ex1_validator(),
                hint="💡 Combinez plusieurs conditions avec AND. Utilisez >= et < pour les dates."
            ),
            exploration_link="/",
        ),

        Lesson(
            title="JOIN et dimensions - Schéma en étoile",
            theory="""## Schéma en étoile et jointures

Le Data Warehouse Olist utilise un **schéma en étoile** :
- **1 table de faits** : `fact_orders` (transactions, ~112k lignes)
- **5 tables de dimensions** : `dim_customers`, `dim_sellers`, `dim_products`, `dim_geolocation`, `dim_dates`

### Pourquoi des jointures ?
Les faits contiennent des **clés étrangères** (integers) plutôt que des attributs descriptifs (strings) pour :
- ✅ Réduire la taille de stockage (int = 4 bytes, string = 50+ bytes)
- ✅ Accélérer les jointures (égalité sur int vs string)
- ✅ Centraliser les dimensions (1 client = 1 ligne dans dim_customers, même s'il a 50 commandes)

### Types de JOIN
- **INNER JOIN** : Garde uniquement les correspondances (le plus courant)
- **LEFT JOIN** : Garde toutes les lignes de gauche, NULL à droite si pas de match
- **RIGHT JOIN** : Inverse de LEFT (rarement utilisé)
- **FULL OUTER JOIN** : Garde tout (SQLite ne le supporte pas nativement)

### Performance
Les clés étrangères sont **toujours indexées** dans un bon DWH. Les jointures sur ces clés sont très rapides (O(log n)).
""",
            concepts=[
                CONCEPTS_INDEX["JOIN"],
                CONCEPTS_INDEX["GROUP BY"],
                CONCEPTS_INDEX["SUM"],
            ],
            demo_sql_file="overview_monthly_mini.sql",
            exercise=Exercise(
                id="beginner_ex2_join",
                title="Top catégories par chiffre d'affaires",
                description="""## Exercice : Jointure fact → dimension produits

**Objectif** : Identifier les 5 catégories de produits qui génèrent le plus de CA.

**Consignes** :
1. Joindre `fact_orders` avec `dim_products` sur `product_key`
2. Construire une colonne `category` avec `COALESCE(category_name_en, category_name_pt, 'Unknown')`
3. Calculer `SUM(price)` par catégorie
4. Trier par CA décroissant et garder les 5 premiers (`LIMIT 5`)
5. Colonnes attendues : `category`, `total_revenue`

**Indices** :
- Utilisez `INNER JOIN` (les produits sans catégorie sont rares)
- Pensez à `GROUP BY` après la jointure
""",
                starter_sql="""-- Top 5 catégories par CA
SELECT
    -- Vos colonnes et agrégats

FROM fact_orders o
-- Votre jointure ici

-- Votre regroupement

-- Votre tri et limite
""",
                solution_sql="""SELECT
    COALESCE(p.category_name_en, p.category_name_pt, 'Unknown') as category,
    SUM(o.price) as total_revenue
FROM fact_orders o
INNER JOIN dim_products p ON o.product_key = p.product_key
WHERE o.order_status = 'delivered'
GROUP BY category
ORDER BY total_revenue DESC
LIMIT 5
""",
                validator=get_beginner_ex2_validator(),
                hint="💡 Utilisez COALESCE(category_name_en, category_name_pt, 'Unknown') puis alias `category`."
            ),
            exploration_link="/ventes",
        ),

        Lesson(
            title="GROUP BY et agrégations - Métriques métier",
            theory="""## Agréger pour obtenir des insights

Les agrégations transforment des lignes individuelles en **métriques métier** :
- `COUNT(*)` : Nombre de lignes de faits (articles)
- `SUM(price)` : Chiffre d'affaires
- `AVG(price)` : Panier moyen par article
- `COUNT(DISTINCT order_id)` : Nombre de commandes uniques

### Règle d'or GROUP BY
**Toute colonne dans SELECT qui n'est PAS dans une fonction d'agrégation DOIT être dans GROUP BY.**

```sql
-- ✅ Correct
SELECT c.state, COUNT(DISTINCT o.order_id) as nb_orders
FROM fact_orders o
INNER JOIN dim_customers c ON o.customer_key = c.customer_key
GROUP BY c.state

-- ❌ Erreur : o.price n'est ni agrégée ni dans GROUP BY
SELECT c.state, o.price, COUNT(*)
FROM fact_orders o
INNER JOIN dim_customers c ON o.customer_key = c.customer_key
GROUP BY c.state
```

### HAVING vs WHERE
- **WHERE** : Filtre **avant** l'agrégation (lignes individuelles)
- **HAVING** : Filtre **après** l'agrégation (groupes)

```sql
-- Garder uniquement les états avec > 100 commandes
SELECT c.state, COUNT(DISTINCT o.order_id) as nb
FROM fact_orders o
INNER JOIN dim_customers c ON o.customer_key = c.customer_key
WHERE o.order_status = 'delivered'  -- Filtre avant
GROUP BY c.state
HAVING COUNT(DISTINCT o.order_id) > 100  -- Filtre après
```

### Vues SQL
Les vues sont des "requêtes sauvegardées" réutilisables. Dans le DWH Olist, `v_monthly_sales` pré-calcule les agrégations mensuelles.
""",
            concepts=[
                CONCEPTS_INDEX["GROUP BY"],
                CONCEPTS_INDEX["SUM"],
                CONCEPTS_INDEX["COUNT"],
                CONCEPTS_INDEX["CASE WHEN"],
            ],
            demo_sql_file="basket_avg.sql",
            exercise=Exercise(
                id="beginner_ex3_groupby",
                title="Chiffre d'affaires par état client",
                description="""## Exercice : Agrégation par dimension géographique

**Objectif** : Calculer le CA et nombre de commandes par état client.

**Consignes** :
1. Joindre `fact_orders` avec `dim_customers` sur `customer_key`
2. Grouper par `state` (colonne dans dim_customers)
3. Calculer :
   - `SUM(price)` → alias `total_revenue`
   - `COUNT(DISTINCT order_id)` → alias `nb_orders`
4. Trier par CA décroissant
5. Colonnes attendues : `state`, `total_revenue`, `nb_orders`

**Résultat attendu** : Au moins 20 états
""",
                starter_sql="""-- CA et nombre de commandes par état
SELECT
    -- Vos colonnes

FROM fact_orders o
-- Votre jointure

-- Votre regroupement

-- Votre tri
""",
                solution_sql="""SELECT
    c.state as state,
    SUM(o.price) as total_revenue,
    COUNT(DISTINCT o.order_id) as nb_orders
FROM fact_orders o
INNER JOIN dim_customers c ON o.customer_key = c.customer_key
GROUP BY c.state
ORDER BY total_revenue DESC
""",
                validator=get_beginner_ex3_validator(),
                hint="💡 N'oubliez pas GROUP BY sur c.state et COUNT(DISTINCT o.order_id)."
            ),
            exploration_link="/clients",
        ),
    ]
)


# === MODULE 2 : WINDOW FUNCTIONS ===

module_2 = Module(
    id="module_2_window_functions",
    icon="view_stream",
    title="Window Functions",
    subtitle="LAG, ROW_NUMBER, NTILE - Calculs avancés sans perdre de lignes",
    estimated_duration_min=30,
    lessons=[
        Lesson(
            title="LAG et comparaisons temporelles - Croissance MoM/YoY",
            theory="""## Window Functions : Le meilleur des deux mondes

Les window functions permettent de **calculer sur des groupes SANS réduire le nombre de lignes**.

### GROUP BY vs Window Functions
```sql
-- GROUP BY : 1 ligne par mois (perd le détail)
SELECT month, SUM(revenue) FROM sales GROUP BY month

-- Window function : Garde toutes les lignes
SELECT *, SUM(revenue) OVER (PARTITION BY month) as monthly_total FROM sales
```

### LAG : Accès à la ligne précédente
`LAG(colonne, offset)` retourne la valeur `offset` lignes avant dans l'ordre spécifié.

**Usage typique** : Calculs de croissance (Month-over-Month, Year-over-Year).

```sql
SELECT
    month,
    revenue,
    LAG(revenue, 1) OVER (ORDER BY month) as prev_month,
    (revenue - LAG(revenue, 1) OVER (ORDER BY month)) / NULLIF(LAG(revenue, 1) OVER (ORDER BY month), 0) * 100 as growth_pct
FROM monthly_sales
```

### Clause OVER
La clause `OVER (...)` définit :
- **ORDER BY** : L'ordre pour LAG/LEAD (obligatoire)
- **PARTITION BY** : Les groupes indépendants (optionnel)

Sans PARTITION BY, la window function s'applique sur **tout le dataset**.
""",
            concepts=[
                CONCEPTS_INDEX["LAG"],
                CONCEPTS_INDEX["LEAD"],
                CONCEPTS_INDEX["PARTITION BY"],
            ],
            demo_sql_file="trends_monthly.sql",
            exercise=Exercise(
                id="intermediate_ex1_lag",
                title="Variation Year-over-Year du CA",
                description="""## Exercice : Croissance annuelle avec LAG

**Objectif** : Calculer la variation YoY (Year-over-Year) du chiffre d'affaires mensuel.

**Consignes** :
1. Partir de la vue `v_monthly_sales` (colonnes : `year`, `month`, `monthly_revenue`)
2. Utiliser `LAG(monthly_revenue, 12) OVER (ORDER BY year, month)` pour obtenir le CA du même mois l'année précédente
4. Calculer le % de croissance : `(revenue - revenue_previous_year) / NULLIF(revenue_previous_year, 0) * 100`
5. Colonnes attendues : `year`, `month`, `revenue`, `revenue_previous_year`, `yoy_growth_pct`

**Note** : Les 12 premiers mois auront `revenue_previous_year = NULL` (normal).
""",
                starter_sql="""-- Croissance YoY mensuelle
SELECT
    -- Colonnes temporelles year, month
    -- LAG pour CA année précédente
    -- Calcul % croissance

FROM v_monthly_sales
ORDER BY year, month
""",
                solution_sql="""SELECT
    year,
    month,
    monthly_revenue as revenue,
    LAG(monthly_revenue, 12) OVER (ORDER BY year, month) as revenue_previous_year,
    (monthly_revenue - LAG(monthly_revenue, 12) OVER (ORDER BY year, month))
        / NULLIF(LAG(monthly_revenue, 12) OVER (ORDER BY year, month), 0) * 100 as yoy_growth_pct
FROM v_monthly_sales
ORDER BY year, month
""",
                validator=get_intermediate_ex1_validator(),
                hint="💡 LAG(col, 12) saute 12 mois en arrière. NULLIF évite la division par zéro."
            ),
            exploration_link="/trends",
        ),

        Lesson(
            title="ROW_NUMBER et ranking - Top N par groupe",
            theory="""## Classements avec window functions

Trois fonctions de ranking :
- **ROW_NUMBER()** : Rang unique (1, 2, 3, 4...) même en cas d'égalité
- **RANK()** : Saute des rangs en cas d'égalité (1, 2, 2, 4...)
- **DENSE_RANK()** : Ne saute pas de rangs (1, 2, 2, 3...)

### ROW_NUMBER : Top N par groupe
Pattern classique avec `PARTITION BY` :

```sql
WITH ranked AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY category ORDER BY revenue DESC) as rank
    FROM products
)
SELECT * FROM ranked WHERE rank <= 3
```

Ici, chaque `category` a son propre classement. Le TOP 3 par catégorie est obtenu en filtrant `rank <= 3`.

### Performance
Les window functions sont efficaces, mais attention :
- ✅ Filtrer AVANT la window function (WHERE) pour réduire le volume
- ❌ Ne PAS utiliser window function dans WHERE (erreur de syntaxe)
- ✅ Utiliser CTE pour filtrer après ranking

### PARTITION BY
Divise le dataset en groupes indépendants. Chaque groupe a son propre calcul.

Sans PARTITION BY → calcul global (ex: rang global sur tout le dataset).
""",
            concepts=[
                CONCEPTS_INDEX["ROW_NUMBER"],
                CONCEPTS_INDEX["PARTITION BY"],
                CONCEPTS_INDEX["WITH"],
            ],
            demo_sql_file="top_products.sql",
            exercise=Exercise(
                id="intermediate_ex2_rownumber",
                title="Top 3 vendeurs par état",
                description="""## Exercice : Ranking avec PARTITION BY

**Objectif** : Identifier les 3 meilleurs vendeurs par état (selon le CA).

**Consignes** :
1. CTE 1 : Agréger `fact_orders` + `dim_sellers` → CA par (seller_id, state)
2. CTE 2 : Ajouter `ROW_NUMBER() OVER (PARTITION BY state ORDER BY revenue DESC) as rank_in_state`
3. Requête finale : Filtrer `rank_in_state <= 3`
4. Colonnes attendues : `state`, `seller_id`, `revenue`, `rank_in_state`

**Résultat attendu** : Plusieurs états avec 3 vendeurs chacun (sauf si <3 vendeurs dans l'état).
""",
                starter_sql="""-- Top 3 vendeurs par état
WITH seller_revenue AS (
    -- Agréger CA par vendeur + état

),
ranked_sellers AS (
    -- Ajouter ROW_NUMBER avec PARTITION BY state

)
SELECT
    state,
    seller_id,
    revenue,
    rank_in_state
FROM ranked_sellers
WHERE rank_in_state <= 3
ORDER BY state, rank_in_state
""",
                solution_sql="""WITH seller_revenue AS (
    SELECT
        s.state,
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
""",
                validator=get_advanced_ex3_validator(),  # Réutilise le validateur advanced ex3
                hint="💡 PARTITION BY state crée un classement indépendant par état."
            ),
            exploration_link="/pareto",
        ),

        Lesson(
            title="NTILE et percentiles - Segmentation Pareto",
            theory="""## Segmentation avec NTILE

`NTILE(n)` répartit les lignes en `n` groupes (buckets) de taille égale.

### Usages courants
- `NTILE(4)` : **Quartiles** (Q1=top 25%, Q4=bottom 25%)
- `NTILE(5)` : **Quintiles** (segmentation RFM, top 20%)
- `NTILE(10)` : **Déciles**
- `NTILE(100)` : **Percentiles**

### Principe de Pareto (80/20)
"80% du CA est généré par 20% des clients/produits."

Vérification avec NTILE :
```sql
WITH quintiles AS (
    SELECT
        seller_id,
        revenue,
        NTILE(5) OVER (ORDER BY revenue DESC) as quintile
    FROM seller_totals
)
SELECT
    quintile,
    SUM(revenue) as segment_revenue,
    SUM(revenue) * 100.0 / SUM(SUM(revenue)) OVER () as pct_of_total
FROM quintiles
GROUP BY quintile
```

Le quintile 1 (top 20%) devrait représenter ~70-80% du CA si Pareto s'applique.

### NTILE vs PERCENT_RANK
- **NTILE** : Groupes de taille égale (ex: 20% des lignes)
- **PERCENT_RANK** : Position relative continue (0.0 à 1.0)
""",
            concepts=[
                CONCEPTS_INDEX["NTILE"],
                CONCEPTS_INDEX["SUM"],
                CONCEPTS_INDEX["CASE WHEN"],
            ],
            demo_sql_file="pareto_sellers.sql",
            exercise=Exercise(
                id="intermediate_ex2_ntile",
                title="Quintiles clients par montant total",
                description="""## Exercice : Segmentation clients avec NTILE

**Objectif** : Répartir les clients en 5 quintiles selon leur montant total dépensé.

**Consignes** :
1. CTE : Joindre `fact_orders` + `dim_customers`, puis agréger par `customer_unique_id` (alias `customer_id`)
2. Requête finale : Ajouter `NTILE(5) OVER (ORDER BY total_spent DESC) as quintile`
3. Colonnes attendues : `customer_id`, `total_spent`, `quintile`
4. Quintile 1 = top 20% (plus gros montants), quintile 5 = bottom 20%

**Vérification** : Chaque quintile devrait contenir ~20% des clients (±5%).
""",
                starter_sql="""-- Segmentation clients en quintiles
WITH customer_totals AS (
    -- Agréger montant total par client

)
SELECT
    -- Ajouter NTILE(5)

FROM customer_totals
ORDER BY total_spent DESC
""",
                solution_sql="""WITH customer_totals AS (
    SELECT
        c.customer_unique_id as customer_id,
        SUM(f.price) as total_spent
    FROM fact_orders f
    INNER JOIN dim_customers c ON f.customer_key = c.customer_key
    WHERE f.order_status = 'delivered'
    GROUP BY c.customer_unique_id
)
SELECT
    customer_id,
    total_spent,
    NTILE(5) OVER (ORDER BY total_spent DESC) as quintile
FROM customer_totals
ORDER BY total_spent DESC
""",
                validator=get_intermediate_ex2_validator(),
                hint="💡 NTILE(5) ORDER BY DESC → quintile 1 = plus gros montants."
            ),
            exploration_link="/rfm",
        ),
    ]
)


# === MODULE 3 : CTEs AVANCÉES ===

module_3 = Module(
    id="module_3_ctes_advanced",
    icon="account_tree",
    title="CTEs Avancées",
    subtitle="WITH clause, chaînage, matérialisation - Structurer des requêtes complexes",
    estimated_duration_min=35,
    lessons=[
        Lesson(
            title="CTEs multi-niveaux - Segmentation RFM",
            theory="""## Common Table Expressions : Lisibilité et réutilisation

Les CTEs (Common Table Expressions) sont des "tables temporaires" nommées définies avec `WITH`.

### Pourquoi utiliser des CTEs ?
- ✅ **Lisibilité** : Décomposer une requête complexe en étapes logiques
- ✅ **Réutilisation** : Référencer la même CTE plusieurs fois
- ✅ **Chaînage** : CTE2 peut utiliser CTE1, CTE3 peut utiliser CTE2...
- ✅ **Debugging** : Tester chaque CTE indépendamment

### Exemple : Segmentation RFM en 3 étapes
```sql
WITH rfm_raw AS (
    -- Étape 1 : Calculer R, F, M par client
    SELECT customer_unique_id, recency, frequency, monetary FROM ...
),
rfm_scored AS (
    -- Étape 2 : Convertir en scores 1-5 avec NTILE
    SELECT *, NTILE(5) OVER (ORDER BY recency DESC) as r_score FROM rfm_raw
),
rfm_segmented AS (
    -- Étape 3 : Classifier en segments métier
    SELECT *, CASE WHEN r_score >= 4 AND m_score >= 4 THEN 'Champions' ... END FROM rfm_scored
)
SELECT * FROM rfm_segmented
```

Chaque CTE est testable indépendamment : `SELECT * FROM rfm_raw LIMIT 10`.

### CTEs vs Sous-requêtes
- **CTE** : Nommée, réutilisable, lisible (recommandé)
- **Sous-requête** : Inline, non réutilisable (éviter si complexe)
""",
            concepts=[
                CONCEPTS_INDEX["WITH"],
                CONCEPTS_INDEX["NTILE"],
                CONCEPTS_INDEX["CASE WHEN"],
            ],
            demo_sql_file="rfm_segmentation.sql",
            exercise=Exercise(
                id="advanced_ex1_cte",
                title="Top 10 produits avec % du total",
                description="""## Exercice : CTEs chaînées

**Objectif** : Afficher le TOP 10 produits avec leur % du CA total.

**Consignes** :
1. CTE 1 (`total_revenue`) : Calculer le CA total global (`SELECT SUM(price) as total FROM fact_orders`)
2. CTE 2 (`product_revenue`) : Joindre `dim_products` et agréger CA par `product_id`
3. Requête finale :
   - Joindre les 2 CTEs (produit croisé, pas de clé)
   - Calculer `pct_of_total = (product_revenue / total_revenue) * 100`
   - Trier DESC, LIMIT 10
4. Colonnes attendues : `product_id`, `revenue`, `pct_of_total`

**Résultat attendu** : Exactement 10 produits.
""",
                starter_sql="""-- Top 10 produits avec % total
WITH total_revenue AS (
    -- CA total global

),
product_revenue AS (
    -- CA par produit

)
SELECT
    -- Calcul % du total

FROM product_revenue, total_revenue
ORDER BY revenue DESC
LIMIT 10
""",
                solution_sql="""WITH total_revenue AS (
    SELECT SUM(price) as total FROM fact_orders
),
product_revenue AS (
    SELECT
        p.product_id,
        SUM(f.price) as revenue
    FROM fact_orders f
    INNER JOIN dim_products p ON f.product_key = p.product_key
    WHERE f.order_status = 'delivered'
    GROUP BY p.product_id
)
SELECT
    product_id,
    revenue,
    (revenue * 100.0 / total) as pct_of_total
FROM product_revenue, total_revenue
ORDER BY revenue DESC
LIMIT 10
""",
                validator=get_advanced_ex1_validator(),
                hint="💡 Produit croisé (FROM cte1, cte2) pour accéder au total dans chaque ligne."
            ),
            exploration_link="/rfm",
        ),

        Lesson(
            title="Sous-requêtes vs CTEs - Performance",
            theory="""## Sous-requêtes : Types et pièges

Trois types de sous-requêtes :
1. **Sous-requête scalaire** : Retourne 1 valeur (dans SELECT)
2. **Sous-requête de liste** : Retourne 1 colonne (dans IN)
3. **Sous-requête corrélée** : Référence la requête externe (lent !)

### Sous-requête corrélée : Attention !
```sql
-- ❌ LENT : Exécutée N fois (1 fois par client)
SELECT
    c.customer_unique_id,
    (SELECT AVG(f2.price) FROM fact_orders f2 WHERE f2.customer_key = c.customer_key) as avg_order
FROM dim_customers c
```

### CTE MATERIALIZED : Solution
```sql
-- ✅ RAPIDE : Exécutée 1 seule fois
WITH customer_avg AS MATERIALIZED (
    SELECT customer_key, AVG(price) as avg_order
    FROM fact_orders
    GROUP BY customer_key
)
SELECT c.customer_unique_id, ca.avg_order
FROM dim_customers c
LEFT JOIN customer_avg ca ON c.customer_key = ca.customer_key
```

### Quand utiliser MATERIALIZED ?
- ✅ CTE référencée plusieurs fois
- ✅ CTE coûteuse (agrégations, jointures)
- ❌ CTE simple utilisée 1 fois (overhead inutile)

**Note** : SQLite matérialise automatiquement dans certains cas, mais être explicite améliore la lisibilité.
""",
            concepts=[
                CONCEPTS_INDEX["WITH"],
                CONCEPTS_INDEX["MATERIALIZED"],
            ],
            demo_sql_file="rfm_segmentation.sql",  # Réutilise RFM qui a des CTEs
            exercise=None,  # Pas d'exercice, leçon théorique
            exploration_link="/optimisation",
        ),

        Lesson(
            title="Calculs temporels avancés - LTV par cohorte",
            theory="""## Manipulations de dates en SQL

SQLite n'a pas de type DATE natif. Les dates sont stockées en TEXT (format ISO 8601 : 'YYYY-MM-DD').

### Fonctions temporelles
- **JULIANDAY(date)** : Convertit en nombre de jours depuis 4714 BC
- **STRFTIME(format, date)** : Formate une date ('%Y', '%m', '%Y-%m')
- **DATE(date, modifier)** : Ajoute/retire des durées ('start of month', '+7 days')

### Calcul de différences
```sql
-- Nombre de jours entre deux dates
SELECT JULIANDAY('2018-01-31') - JULIANDAY('2018-01-01')  -- = 30

-- Récence client (jours depuis dernier achat)
SELECT JULIANDAY('now') - JULIANDAY(MAX(order_date)) as recency_days
FROM v_orders_enriched
WHERE customer_unique_id = 'xxx'
```

### Cohortes mensuelles
Une cohorte = groupe de clients acquis le même mois.

**Analyse de rétention par cohorte** :
1. Identifier mois de première commande (cohorte)
2. Pour chaque commande, calculer delta en mois vs cohorte
3. Agréger : % clients actifs par cohorte à M+1, M+2, M+3...

Le calcul de "mois écoulés" en SQLite nécessite de l'arithmétique sur des entiers YYYYMM.
""",
            concepts=[
                CONCEPTS_INDEX["JULIANDAY"],
                CONCEPTS_INDEX["WITH"],
                CONCEPTS_INDEX["SUM"],
            ],
            demo_sql_file="ltv_cohorts.sql",
            exercise=Exercise(
                id="intermediate_ex3_running",
                title="Running total mensuel du CA",
                description="""## Exercice : Cumul glissant avec window function

**Objectif** : Calculer le chiffre d'affaires cumulé mois par mois.

**Consignes** :
1. Partir de `v_monthly_sales` (colonnes : `year`, `month`, `month_label`, `monthly_revenue`)
2. Utiliser `SUM(monthly_revenue) OVER (ORDER BY year, month ROWS UNBOUNDED PRECEDING)` pour le cumul
3. Colonnes attendues : `month`, `monthly_revenue`, `cumulative_revenue`
4. Le cumul doit être strictement croissant
5. Dernier cumul = somme de tous les monthly_revenue

**Note** : `ROWS UNBOUNDED PRECEDING` signifie "depuis le début jusqu'à la ligne courante".
""",
                starter_sql="""-- Running total mensuel
SELECT
    month_label as month,
    monthly_revenue,
    -- Votre SUM() OVER ici

FROM v_monthly_sales
ORDER BY year, month
""",
                solution_sql="""SELECT
    month_label as month,
    monthly_revenue,
    SUM(monthly_revenue) OVER (ORDER BY year, month ROWS UNBOUNDED PRECEDING) as cumulative_revenue
FROM v_monthly_sales
ORDER BY year, month
""",
                validator=get_intermediate_ex3_validator(),
                hint="💡 SUM() OVER avec ROWS UNBOUNDED PRECEDING crée un cumul depuis le début."
            ),
            exploration_link="/cohorts",
        ),
    ]
)


# === MODULE 4 : CAS COMPLEXES ===

module_4 = Module(
    id="module_4_complex_cases",
    icon="psychology",
    title="Cas Complexes",
    subtitle="Self-join, scoring multi-critères, analyses métier avancées",
    estimated_duration_min=40,
    lessons=[
        Lesson(
            title="Auto-jointures et cohortes - Rétention clients",
            theory="""## Self-join : Joindre une table avec elle-même

Un **self-join** compare les lignes d'une table entre elles.

### Cas d'usage
- Comparer deux événements du même client (première commande vs suivantes)
- Calculer des deltas temporels (time between purchases)
- Matrices de rétention (cohortes)

### Exemple : Taux de réachat
```sql
WITH first_orders AS (
    SELECT
        c.customer_unique_id as customer_id,
        MIN(f.date_key) as first_order_key
    FROM fact_orders f
    INNER JOIN dim_customers c ON f.customer_key = c.customer_key
    WHERE f.order_status = 'delivered'
      AND f.date_key IS NOT NULL
    GROUP BY c.customer_unique_id
),
subsequent_orders AS (
    SELECT DISTINCT
        c.customer_unique_id as customer_id
    FROM fact_orders f
    INNER JOIN dim_customers c ON f.customer_key = c.customer_key
    INNER JOIN first_orders fo ON c.customer_unique_id = fo.customer_id
    WHERE f.order_status = 'delivered'
      AND f.date_key > fo.first_order_key
)
SELECT
    COUNT(DISTINCT fo.customer_id) as total_customers,
    COUNT(DISTINCT so.customer_id) as repeat_customers,
    ROUND(
        COUNT(DISTINCT so.customer_id) * 100.0
        / NULLIF(COUNT(DISTINCT fo.customer_id), 0),
        1
    ) as repeat_rate_pct
FROM first_orders fo
LEFT JOIN subsequent_orders so ON fo.customer_id = so.customer_id
```

### Matrices de rétention
Une matrice de rétention croise :
- **Lignes** : Cohortes (mois d'acquisition)
- **Colonnes** : Périodes relatives (M0, M+1, M+2...)
- **Valeurs** : % clients actifs

Nécessite un self-join entre "première commande" et "toutes les commandes" pour calculer le delta en mois.
""",
            concepts=[
                CONCEPTS_INDEX["WITH"],
                CONCEPTS_INDEX["JULIANDAY"],
                CONCEPTS_INDEX["CASE WHEN"],
            ],
            demo_sql_file="cohorts_retention.sql",
            exercise=Exercise(
                id="advanced_ex2_selfjoin",
                title="Clients avec 2+ commandes",
                description="""## Exercice : Identifier les clients récurrents

**Objectif** : Lister les clients qui ont passé au moins 2 commandes.

**Consignes** :
1. Joindre `fact_orders` et `dim_customers` pour obtenir `customer_unique_id`
2. Agréger par client avec `COUNT(DISTINCT order_id)` (grain commande)
3. Filtrer avec `HAVING COUNT(DISTINCT order_id) >= 2`
4. Colonnes attendues : `customer_id`, `nb_orders`
5. Résultat attendu : Au moins 10 clients

**Note** : Le grain de `fact_orders` est l'article de commande, pas la commande complète.
""",
                starter_sql="""-- Clients récurrents (2+ commandes)
SELECT
    c.customer_unique_id as customer_id,
    -- Compter les commandes

FROM fact_orders f
INNER JOIN dim_customers c ON f.customer_key = c.customer_key
WHERE f.order_status = 'delivered'
GROUP BY c.customer_unique_id
-- Filtrer >= 2
ORDER BY nb_orders DESC
""",
                solution_sql="""SELECT
    c.customer_unique_id as customer_id,
    COUNT(DISTINCT f.order_id) as nb_orders
FROM fact_orders f
INNER JOIN dim_customers c ON f.customer_key = c.customer_key
WHERE f.order_status = 'delivered'
GROUP BY c.customer_unique_id
HAVING COUNT(DISTINCT f.order_id) >= 2
ORDER BY nb_orders DESC
""",
                validator=get_advanced_ex2_validator(),
                hint="💡 Utilisez COUNT(DISTINCT f.order_id) pour compter les commandes, puis HAVING >= 2."
            ),
            exploration_link="/cohorts",
        ),

        Lesson(
            title="Scoring multi-critères - Évaluation vendeurs",
            theory="""## Scoring composite : Combiner plusieurs métriques

Un **score composite** agrège plusieurs KPIs en un indicateur unique.

### Méthodologie
1. Identifier les KPIs pertinents (5-7 max)
2. Normaliser chaque KPI (0-100 ou 1-5) avec NTILE
3. Pondérer selon l'importance métier
4. Sommer pour obtenir le score final

### Exemple : Score vendeur (5 KPIs)
```sql
WITH seller_kpis AS (
    SELECT
        s.seller_id,
        SUM(f.price) as revenue,
        COUNT(DISTINCT f.order_id) as volume,
        AVG(f.review_score) as avg_rating,
        AVG(f.delivery_days) as avg_delivery,
        AVG(CASE WHEN f.delivery_delta_days <= 0 THEN 1.0 ELSE 0.0 END) * 100 as on_time_pct
    FROM fact_orders f
    INNER JOIN dim_sellers s ON f.seller_key = s.seller_key
    WHERE f.order_status = 'delivered'
    GROUP BY s.seller_id
),
seller_scores AS (
    SELECT
        seller_id,
        revenue,
        volume,
        avg_rating,
        avg_delivery,
        on_time_pct,
        NTILE(5) OVER (ORDER BY revenue ASC) as revenue_score,
        NTILE(5) OVER (ORDER BY volume ASC) as volume_score,
        NTILE(5) OVER (ORDER BY avg_rating ASC) as rating_score,
        NTILE(5) OVER (ORDER BY avg_delivery DESC) as delivery_score,
        NTILE(5) OVER (ORDER BY on_time_pct ASC) as punctuality_score
    FROM seller_kpis
)
SELECT
    seller_id,
    (revenue_score + volume_score + rating_score + delivery_score + punctuality_score) as total_score
FROM seller_scores
ORDER BY total_score DESC
```

### RANK vs DENSE_RANK
- **RANK()** : Saute des rangs en cas d'égalité (1, 2, 2, 4...)
- **DENSE_RANK()** : Ne saute pas (1, 2, 2, 3...)

Utiliser DENSE_RANK si vous voulez des rangs contigus.
""",
            concepts=[
                CONCEPTS_INDEX["NTILE"],
                CONCEPTS_INDEX["CASE WHEN"],
                CONCEPTS_INDEX["WITH"],
            ],
            demo_sql_file="seller_scoring.sql",
            exercise=None,  # Pas d'exercice, démonstration complexe suffisante
            exploration_link="/scoring",
        ),

        Lesson(
            title="Analyses avancées métier - Nouveaux vs Récurrents",
            theory="""## Classifications métier avec SQL

Les analyses métier nécessitent souvent des **flags booléens** et des **classifications**.

### Nouveaux vs Récurrents
Un client est "nouveau" au mois M si c'est sa première commande.

```sql
WITH order_months AS (
    SELECT DISTINCT
        c.customer_unique_id,
        f.date_key / 100 as order_month,
        vc.first_month
    FROM fact_orders f
    INNER JOIN dim_customers c ON f.customer_key = c.customer_key
    INNER JOIN v_customer_cohorts vc ON vc.customer_unique_id = c.customer_unique_id
    WHERE f.order_status = 'delivered'
      AND f.date_key IS NOT NULL
)
SELECT
    (order_month / 100) || '-' || PRINTF('%02d', order_month % 100) as month_label,
    COUNT(DISTINCT CASE WHEN order_month = first_month THEN customer_unique_id END) as new_customers,
    COUNT(DISTINCT CASE WHEN order_month > first_month THEN customer_unique_id END) as recurring_customers
FROM order_months
GROUP BY order_month
ORDER BY order_month
```

### Clients "at risk"
Clients inactifs depuis N jours :

```sql
WITH last_orders AS (
    SELECT
        c.customer_unique_id as customer_id,
        MAX(d.full_date) as last_order_date
    FROM fact_orders f
    INNER JOIN dim_customers c ON f.customer_key = c.customer_key
    INNER JOIN dim_dates d ON f.date_key = d.date_key
    WHERE f.order_status = 'delivered'
    GROUP BY c.customer_unique_id
)
SELECT
    customer_id,
    JULIANDAY('now') - JULIANDAY(last_order_date) as days_since_last_order
FROM last_orders
WHERE JULIANDAY('now') - JULIANDAY(last_order_date) > 180  -- 6 mois
```

### MIN() OVER : Flag "première occurrence"
```sql
WITH customer_orders AS (
    SELECT DISTINCT
        c.customer_unique_id as customer_id,
        f.date_key / 100 as order_month
    FROM fact_orders f
    INNER JOIN dim_customers c ON f.customer_key = c.customer_key
    WHERE f.order_status = 'delivered'
      AND f.date_key IS NOT NULL
)
SELECT
    customer_id,
    order_month,
    CASE
        WHEN order_month = MIN(order_month) OVER (PARTITION BY customer_id) THEN 1
        ELSE 0
    END as is_first_order
FROM customer_orders
```

C'est plus élégant qu'un self-join dans certains cas.
""",
            concepts=[
                CONCEPTS_INDEX["CASE WHEN"],
                CONCEPTS_INDEX["WITH"],
                CONCEPTS_INDEX["JULIANDAY"],
            ],
            demo_sql_file="new_vs_recurring.sql",
            exercise=None,  # Leçon théorique
            exploration_link="/clients",
        ),
    ]
)


# === MODULE 5 : OPTIMISATION ===

module_5 = Module(
    id="module_5_optimization",
    icon="speed",
    title="Optimisation & Performance",
    subtitle="Index, EXPLAIN, CTEs matérialisées - Diagnostiquer et optimiser",
    estimated_duration_min=30,
    lessons=[
        Lesson(
            title="Index et EXPLAIN - Diagnostiquer les ralentissements",
            theory="""## Index B-Tree : Accélérer les recherches

Un **index** est une structure qui permet d'accéder plus vite à certaines lignes.
Son intérêt dépend de la requête (sélectivité du filtre, tri, jointure) et de la volumétrie.

### Exemple sur le schéma Olist
```sql
-- Filtre très courant et souvent peu sélectif
SELECT * FROM fact_orders WHERE order_status = 'delivered';

-- Filtre généralement plus sélectif
SELECT * FROM fact_orders WHERE date_key = 20170615;
```

### EXPLAIN QUERY PLAN
Affiche le plan d'exécution :

```sql
EXPLAIN QUERY PLAN
SELECT * FROM fact_orders WHERE date_key >= 20170101;
```

**Interprétation typique** :
- `SCAN TABLE fact_orders` : parcours complet de table
- `SEARCH TABLE fact_orders USING INDEX ...` : utilisation d'index

### Quand indexer ?
- ✅ Colonnes dans WHERE (filtrage)
- ✅ Colonnes dans JOIN (clés étrangères)
- ✅ Colonnes dans ORDER BY (tri)
- ❌ Colonnes peu sélectives (ex: booléens avec 50/50)
- ❌ Tables < 1000 lignes (overhead inutile)

### Covering Index
Un index "couvrant" contient toutes les colonnes nécessaires :

```sql
CREATE INDEX idx_fact_status_date_price ON fact_orders(order_status, date_key, price);
SELECT date_key, price
FROM fact_orders
WHERE order_status = 'delivered' AND date_key >= 20170101;
```

Selon le plan, SQLite peut parfois répondre avec moins d'accès à la table de base.
""",
            concepts=[
                CONCEPTS_INDEX["CREATE INDEX"],
                CONCEPTS_INDEX["EXPLAIN"],
            ],
            demo_sql_file="trends_monthly.sql",  # Réutilise une requête existante
            exercise=None,  # Exercice pratique dans explorations
            exploration_link="/optimisation",
        ),

        Lesson(
            title="Projection et sélectivité - SELECT stratégique",
            theory="""## Optimiser la projection et le filtrage

### Projection ciblée
```sql
-- Plus de colonnes que nécessaire
SELECT * FROM fact_orders WHERE order_status = 'delivered'

-- Colonnes utiles uniquement
SELECT order_id, price FROM fact_orders WHERE order_status = 'delivered'
```

Réduire la projection diminue le volume de données à lire et transférer, surtout sur de gros jeux.

### Covering Index avec projection minimale
```sql
CREATE INDEX idx_fact_status_price ON fact_orders(order_status, price);

-- Peut bénéficier d'un index couvrant selon le plan
SELECT order_status, SUM(price)
FROM fact_orders
WHERE order_status = 'delivered'
GROUP BY order_status
```

### Sélectivité des filtres
La **sélectivité** = % de lignes gardées par le filtre.

- ✅ Haute sélectivité (< 10%) : Index très utile
- ❌ Faible sélectivité (> 50%) : Index peu utile

```sql
-- Haute sélectivité → Index utile
WHERE date_key = 20170615

-- Faible sélectivité → gain souvent limité
WHERE order_status = 'delivered'
```

### LIMIT early
Ajoutez `LIMIT` tôt pour éviter de traiter toutes les lignes :

```sql
-- ✅ Stoppe dès 10 lignes trouvées
SELECT order_id, date_key, price
FROM fact_orders
WHERE order_status = 'delivered'
ORDER BY date_key
LIMIT 10
```
""",
            concepts=[
                CONCEPTS_INDEX["SELECT"],
                CONCEPTS_INDEX["CREATE INDEX"],
            ],
            demo_sql_file="overview_kpis.sql",
            exercise=None,
            exploration_link="/optimisation",
        ),

        Lesson(
            title="CTEs matérialisées - Éviter les recalculs",
            theory="""## MATERIALIZED : Calculer une fois, utiliser plusieurs fois

Par défaut, SQLite peut **inliner** une CTE (l'intégrer dans la requête externe). Une CTE référencée plusieurs fois peut alors être recalculée.

### Sous-requête corrélée : cas coûteux
```sql
SELECT
    c.customer_unique_id as customer_id,
    (
        SELECT COUNT(DISTINCT f.order_id)
        FROM fact_orders f
        WHERE f.customer_key = c.customer_key
    ) as nb_orders
FROM dim_customers c
```

### CTE MATERIALIZED : La solution
```sql
WITH customer_orders AS MATERIALIZED (
    SELECT customer_key, COUNT(DISTINCT order_id) as nb_orders
    FROM fact_orders
    GROUP BY customer_key
)
SELECT
    c.customer_unique_id as customer_id,
    COALESCE(co.nb_orders, 0) as nb_orders
FROM dim_customers c
LEFT JOIN customer_orders co ON c.customer_key = co.customer_key
```

Le gain dépend de la charge et du plan, mais cette forme évite les recalculs inutiles.

### Quand utiliser ?
- ✅ CTE référencée 2+ fois
- ✅ CTE avec agrégations/jointures coûteuses
- ✅ CTE utilisée dans UNION ALL
- ❌ CTE simple (1 table, 1 filtre, 1 usage)

### Vérifier avec EXPLAIN
```sql
EXPLAIN QUERY PLAN
WITH customer_orders AS MATERIALIZED (
    SELECT customer_key, COUNT(DISTINCT order_id) as nb_orders
    FROM fact_orders
    GROUP BY customer_key
)
SELECT c.customer_unique_id, COALESCE(co.nb_orders, 0) as nb_orders
FROM dim_customers c
LEFT JOIN customer_orders co ON c.customer_key = co.customer_key
```

Cherchez "MATERIALIZE" dans le plan.
""",
            concepts=[
                CONCEPTS_INDEX["MATERIALIZED"],
                CONCEPTS_INDEX["WITH"],
            ],
            demo_sql_file="rfm_segmentation.sql",
            exercise=None,
            exploration_link="/optimisation",
        ),
    ]
)


# === ASSEMBLAGE FINAL ===

COURSE_MODULES = [
    module_1,
    module_2,
    module_3,
    module_4,
    module_5,
]
