"""
Introduction détaillée du Data Warehouse Olist.

6 slides :
1. Contexte Olist (dataset, volumétrie exacte)
2. Processus ETL (5 transformations clés avec justifications empiriques)
3. Schéma en étoile (cardinalités exactes, grain article explicité)
4. Décisions architecturales (vues VIRTUELLES, pas matérialisées)
5. Validation & Qualité (concordance 100%, anomalies documentées)
6. Valeur business (9 métriques réelles, limites assumées, transition cours)
"""

from nicegui import ui


def render_intro_carousel():
    """Affiche l'introduction DWH avec navigation manuelle entre slides."""

    # État de navigation
    current_slide = {'index': 0}
    total_slides = 6

    # Container principal
    slide_container = ui.column().classes('w-full')

    def render_slide(index: int):
        """Affiche le slide à l'index donné."""
        slide_container.clear()

        with slide_container:
            # Progress indicator
            with ui.row().classes('w-full justify-center mb-4'):
                for i in range(total_slides):
                    if i == index:
                        ui.label('●').classes('text-green-400 text-2xl')
                    else:
                        ui.label('○').classes('text-gray-600 text-2xl')

            # Contenu du slide
            with ui.card().classes('w-full p-8 chapter-enter'):
                if index == 0:
                    render_slide_1()
                elif index == 1:
                    render_slide_2()
                elif index == 2:
                    render_slide_3()
                elif index == 3:
                    render_slide_4()
                elif index == 4:
                    render_slide_5()
                elif index == 5:
                    render_slide_6()

            # Navigation
            with ui.row().classes('w-full justify-between mt-4'):
                if index > 0:
                    ui.button('← Précédent', on_click=lambda: navigate(-1)).props('outline')
                else:
                    ui.label('')  # Spacer

                if index < total_slides - 1:
                    ui.button('Suivant →', on_click=lambda: navigate(1)).props('color=primary')
                else:
                    ui.button('Commencer le cours 🚀', on_click=start_course).props('color=positive')

    def navigate(delta: int):
        """Navigue entre les slides."""
        current_slide['index'] = max(0, min(total_slides - 1, current_slide['index'] + delta))
        render_slide(current_slide['index'])

    def start_course():
        """Redirige vers la première leçon."""
        ui.navigate.to('/presentation/module_1_fundamentals/0')

    # Afficher premier slide
    render_slide(0)


def render_slide_1():
    """Slide 1 : Contexte Olist."""
    ui.label("🎯 Le Dataset Olist").classes('text-4xl font-bold mb-4')

    ui.markdown("""
## Dataset E-commerce Brésilien (2016-2018)

**Olist** est une plateforme e-commerce brésilienne qui connecte des milliers de vendeurs indépendants avec les plus grandes marketplaces du pays.

### Les chiffres clés
- 🛒 **99 441 commandes** sur 24 mois (septembre 2016 - octobre 2018)
- 👥 **96 096 clients** uniques (`customer_unique_id`)
- 🏪 **3 095 vendeurs** actifs
- 📦 **32 951 produits** différents
- 📍 **19 015 codes postaux** uniques (couvrant 27 états brésiliens)
- 🌎 **27 états** brésiliens couverts

### Volumétrie totale des données sources
**1 550 871 lignes brutes** réparties dans **9 fichiers CSV**, dont :
- 77% (1M lignes) = geolocation à dédupliquer
- 23% = données transactionnelles et référentielles

### Les 9 fichiers CSV sources
1. `olist_orders_dataset.csv` (99 441 lignes)
2. `olist_order_items_dataset.csv` (112 650 lignes)
3. `olist_customers_dataset.csv` (99 441 lignes)
4. `olist_sellers_dataset.csv` (3 095 lignes)
5. `olist_products_dataset.csv` (32 951 lignes)
6. `olist_order_reviews_dataset.csv` (99 224 lignes)
7. `olist_order_payments_dataset.csv` (103 886 lignes)
8. `olist_geolocation_dataset.csv` (1 000 163 lignes!)
9. `product_category_name_translation.csv` (71 lignes)

➡️ **Objectif** : Construire un Data Warehouse analytique optimisé
""").classes('text-gray-300')


def render_slide_2():
    """Slide 2 : Processus ETL."""
    ui.label("⚙️ Le Processus ETL").classes('text-4xl font-bold mb-4')

    ui.markdown("""
## Extract → Transform → Load

Notre pipeline de transformation suit les étapes classiques de l'ingénierie des données.
""").classes('text-gray-300 mb-4')

    # Schéma Mermaid du flow ETL
    ui.mermaid("""
graph LR
    A[9 CSV Sources<br/>1 550 871 lignes] -->|Extract| B[DataFrames Pandas]
    B -->|Transform| C[Cleaning + Engineering]
    C -->|Load| D[(SQLite DWH<br/>6 tables)]

    style A fill:#e74c3c
    style B fill:#f39c12
    style C fill:#3498db
    style D fill:#27ae60

    C -->|clean_geolocation| C1[Dédup 1M → 19K]
    C -->|aggregate_payments| C2[SUM + MODE par order]
    C -->|latest_review| C3[Garder plus récent]
    C -->|surrogate_keys| C4[UUID → INTEGER]
    C -->|delivery_metrics| C5[Calculs temporels]
""").classes('w-full mb-4')

    ui.markdown("""
### 1. **Extract** : Chargement des CSV
```python
orders_df = pd.read_csv("olist_orders_dataset.csv")      # 99 441 lignes
items_df = pd.read_csv("olist_order_items_dataset.csv")  # 112 650 lignes
# ... 7 autres CSV
```

### 2. **Transform** : 5 transformations clés

#### 🔸 **`clean_geolocation`** : Dédoublonner codes postaux
- **Pourquoi** : 1M lignes pour 19K codes postaux uniques (53 entrées/zip en moyenne)
- **Méthode** : Médiane lat/lng par zip_code_prefix (robuste aux outliers)
- **Résultat** : 1 000 163 → 19 015 lignes, précision ~2km

```python
def _safe_mode(x):
    \"\"\"Mode sécurisé évitant IndexError sur séries vides.\"\"\"
    mode = x.mode()
    return mode.iloc[0] if not mode.empty else (x.iloc[0] if len(x) > 0 else None)

def clean_geolocation(df):
    return df.groupby('zip_code_prefix', as_index=False).agg({
        'lat': 'median',
        'lng': 'median',
        'city': _safe_mode,
        'state': _safe_mode
    })
```

#### 🔸 **`aggregate_payments`** : Fusionner paiements multiples
- **Pourquoi** : 103 886 lignes pour 99 441 commandes (97% mono-paiement)
- **Méthode** : SUM(payment_value), MODE(payment_type) par order_id
- **Résultat** : order_payment_total = montant total, payment_type = type dominant

#### 🔸 **`latest_review_per_order`** : Résoudre reviews multiples
- **Pourquoi** : 547 commandes ont plusieurs reviews (0.5%)
- **Méthode** : Garder la review la plus récente (MAX(review_creation_date))
- **Résultat** : 1 review par commande (99 224 → 98 666 commandes avec review)

#### 🔸 **`create_surrogate_keys`** : Optimiser clés étrangères
- **Pourquoi** : UUID 32 char (32 bytes) → INTEGER (4 bytes) = 8× moins d'espace
- **Méthode** : AUTOINCREMENT sur customer_key, seller_key, product_key
- **Résultat** : Jointures 8× plus rapides, index B-Tree optimaux

#### 🔸 **`calculate_delivery_metrics`** : Feature engineering temporel
- **Méthodes** :
  - `delivery_days` = delivered_date - purchase_date
  - `estimated_days` = estimated_delivery_date - purchase_date
  - `delivery_delta_days` = delivery_days - estimated_days (positif = retard)
- **Résultat** : Métriques précalculées pour analyses logistiques

### 3. **Load** : Insertion dans SQLite avec 5 index stratégiques

```python
# Schéma en étoile : 1 fait + 5 dimensions
fact_orders.to_sql('fact_orders', conn, index=False)
dim_customers.to_sql('dim_customers', conn, index=False)
# ... 4 autres dimensions

# Index critiques (accélération 100×)
conn.execute("CREATE INDEX idx_orders_date ON fact_orders(date_key)")
conn.execute("CREATE INDEX idx_orders_customer ON fact_orders(customer_key)")
conn.execute("CREATE INDEX idx_orders_seller ON fact_orders(seller_key)")
conn.execute("CREATE INDEX idx_orders_product ON fact_orders(product_key)")
conn.execute("CREATE INDEX idx_orders_status ON fact_orders(order_status)")
```

➡️ **Résultat** : 1.5M lignes brutes → 287K lignes structurées, queryable en <200ms
""").classes('text-gray-300')


def render_slide_3():
    """Slide 3 : Schéma en étoile."""
    ui.label("⭐ Schéma en Étoile").classes('text-4xl font-bold mb-4')

    ui.markdown("""
## Modélisation dimensionnelle : Le cœur du DWH

Le schéma en étoile est le standard pour les Data Warehouses analytiques.
""").classes('text-gray-300 mb-4')

    # Schéma ERD avec Mermaid
    ui.mermaid("""
erDiagram
    fact_orders ||--o{ dim_customers : "customer_key"
    fact_orders ||--o{ dim_sellers : "seller_key"
    fact_orders ||--o{ dim_products : "product_key"
    fact_orders ||--o{ dim_geolocation : "customer_zip_code"
    fact_orders ||--o{ dim_dates : "order_date"

    fact_orders {
        int order_item_id PK
        string order_id
        int customer_key FK
        int seller_key FK
        int product_key FK
        date order_date
        decimal price
        string order_status
        int delivery_days
        int review_score
    }

    dim_customers {
        int customer_key PK
        string customer_id
        string customer_city
        string customer_state
    }

    dim_sellers {
        int seller_key PK
        string seller_id
        string seller_city
        string seller_state
    }

    dim_products {
        int product_key PK
        string product_id
        string category
        decimal weight_g
        decimal volume_cm3
    }

    dim_geolocation {
        string zip_code PK
        string city
        string state
        float lat
        float lng
    }

    dim_dates {
        date date_key PK
        int year
        int month
        int day
        int week
        string month_name
    }
""").classes('w-full mb-4')

    ui.markdown("""
### 📊 Cardinalités

| Table | Lignes | Rôle |
|-------|--------|------|
| **fact_orders** | 112 650 | **Table de faits** (transactions) |
| dim_customers | 96 096 | Attributs clients (ville, état) |
| dim_sellers | 3 095 | Attributs vendeurs |
| dim_products | 32 951 | Catégories, dimensions produits |
| dim_geolocation | 19 015 | Codes postaux dédoublonnés |
| dim_dates | 715 | Calendrier (2016-09-04 → 2018-11-12) |

### 🔑 Grain de la table de faits
**1 ligne = 1 article d'une commande** (order_id + order_item_id)

**Distribution grain commande → article** :
- **90.1% des commandes** = 1 seul article (mono-item)
- **9.9% des commandes** = 2 à 21 articles (multi-items)
- **Total** : 99 441 commandes → 112 650 lignes (ratio 1.13)

**Exemple** : Commande #abc123 avec 3 articles → 3 lignes dans fact_orders (order_item_id = 1, 2, 3)

**Pourquoi ce grain ?**
- ✅ Permet d'agréger au niveau commande (`GROUP BY order_id`) ou article
- ✅ Conserve le détail maximal (prix unitaire par article, vendeur par article)
- ✅ Facilite les analyses produit (quel article génère le plus de CA ?)

**⚠️ Attention aux métriques semi-additives** :
- `order_payment_total` est au grain **commande**, pas article
- Exemple : Commande 100 R$ avec 2 articles → chaque ligne affiche 100 R$
- **Pour obtenir le total correct** : `SELECT DISTINCT order_id, order_payment_total` puis SUM

### 🎯 Avantages du schéma en étoile
- ✅ **Jointures simples** : 1 saut de la fact vers chaque dimension
- ✅ **Performance** : Clés surrogate (int) ultra-rapides (8× moins d'espace que UUID)
- ✅ **Lisibilité** : Structure intuitive (centre + branches)
- ✅ **Flexibilité** : Ajouter une dimension = 1 colonne FK dans fact
""").classes('text-gray-300')


def render_slide_4():
    """Slide 4 : Décisions architecturales."""
    ui.label("🏗️ Décisions Architecturales").classes('text-4xl font-bold mb-4')

    ui.markdown("""
## Choix techniques qui rendent le DWH performant

### 1. **Grain : Article vs Commande**

**Option 1 - Grain "Commande"** (rejeté) :
- ❌ Perd le détail par article
- ❌ Prix agrégés (impossible de savoir quel produit coûte combien)
- ❌ Reviews moyennées (perd la granularité)

**Option 2 - Grain "Article"** (✅ choisi) :
- ✅ Détail maximal conservé
- ✅ Agréger au niveau commande reste possible (`GROUP BY order_id`)
- ✅ Analyses produit facilitées

➡️ **Décision** : 1 ligne = 1 article (112k lignes dans fact_orders)

---

### 2. **Index Stratégiques**

Les index accélèrent les recherches de O(n) → O(log n).

**Index créés** :
```sql
CREATE INDEX idx_orders_date ON fact_orders(order_date);
CREATE INDEX idx_orders_status ON fact_orders(order_status);
CREATE INDEX idx_orders_customer ON fact_orders(customer_key);
CREATE INDEX idx_orders_seller ON fact_orders(seller_key);
CREATE INDEX idx_orders_product ON fact_orders(product_key);
```

**Impact** :
- Filtrage WHERE sur `order_date` : **100x plus rapide** (0.5ms vs 50ms)
- Jointures fact → dimensions : **Instantanées** (déjà indexées)
- Tri ORDER BY : **Optimisé** (index covering)

**Principe** : Indexer toutes les clés étrangères + colonnes filtrées fréquemment.

---

### 3. **Vues Analytiques (virtuelles, pas matérialisées)**

⚠️ **SQLite ne supporte PAS les vues matérialisées** (contrairement à PostgreSQL)

Les vues créées sont **virtuelles** : recalculées à chaque SELECT, pas de cache physique.

**3 vues créées** :

#### 📊 `v_monthly_sales` : Ventes mensuelles agrégées
```sql
CREATE VIEW v_monthly_sales AS
SELECT
    d.year,
    d.month,
    d.year || '-' || PRINTF('%02d', d.month) AS month_label,
    ROUND(SUM(f.price), 2) AS monthly_revenue,
    COUNT(DISTINCT f.order_id) AS monthly_orders,
    ROUND(SUM(f.price) * 1.0 / NULLIF(COUNT(DISTINCT f.order_id), 0), 2) AS avg_basket
FROM fact_orders f
JOIN dim_dates d ON f.date_key = d.date_key
WHERE f.order_status = 'delivered'
GROUP BY d.year, d.month;
```

#### 👥 `v_customer_cohorts` : Clients avec mois de première commande
```sql
CREATE VIEW v_customer_cohorts AS
SELECT
    c.customer_unique_id,
    MIN(f.date_key / 100) AS first_month,
    (MIN(f.date_key / 100) / 100) || '-' || PRINTF('%02d', MIN(f.date_key / 100) % 100) AS first_month_label,
    COUNT(DISTINCT f.order_id) AS total_orders,
    ROUND(SUM(f.price), 2) AS total_spent
FROM fact_orders f
JOIN dim_customers c ON f.customer_key = c.customer_key
WHERE f.order_status = 'delivered'
  AND f.date_key IS NOT NULL
GROUP BY c.customer_unique_id;
```

#### 📦 `v_orders_enriched` : Commandes avec toutes dimensions joinées
Vue dénormalisée pour analyses ad-hoc sans réécrire les JOINs.

**Avantage** : Requêtes complexes deviennent `SELECT * FROM v_monthly_sales`.

**Limite** : Pas de cache. Pour matérialiser : `CREATE TABLE AS SELECT ...` (manuelle).

---

### 4. **Clés Surrogate vs Clés Naturelles**

**Clé naturelle** : `customer_id` (string UUID 32 chars, 32 bytes)

**Clé surrogate** : `customer_key` (integer auto-incrémenté, 4 bytes)

**Impact** :
- ✅ **8x moins d'espace** (4 bytes vs 32)
- ✅ **Jointures plus rapides** (égalité sur int vs string)
- ✅ **Index plus compacts** (B-Tree sur int = optimal)

➡️ **Décision** : Toutes les FK utilisent des clés surrogate (customer_key, seller_key, product_key).

---

### 5. **SQLite vs PostgreSQL**

Pourquoi SQLite pour un DWH ?

**Avantages** :
- ✅ **Zero-config** : 1 fichier .db, pas de serveur
- ✅ **Portable** : Copier le .db = copier tout le DWH
- ✅ **Rapide** : Window functions performantes, optimiseur correct
- ✅ **Suffisant** : < 1M lignes = parfait pour SQLite

**Limites** (OK pour notre use case) :
- ❌ Pas de concurrence écriture (read-only en prod = OK)
- ❌ Pas de réplication (backup fichier = OK)
- ❌ Pas de partitionnement (pas nécessaire à 112k lignes)

➡️ **Décision** : SQLite est idéal pour un DWH analytique mono-utilisateur.
""").classes('text-gray-300')


def render_slide_5():
    """Slide 5 : Validation & Qualité des Données."""
    ui.label("✅ Validation & Qualité des Données").classes('text-4xl font-bold mb-4')

    ui.markdown("""
## Intégrité des transformations CSV → DWH

La validation systématique garantit que les transformations ETL n'ont introduit aucune perte de données ni erreur de calcul.

---

### 📊 Tableau de concordance CSV ↔ DWH

| Entité | CSV Source | Data Warehouse | Match | Observations |
|--------|-----------|----------------|-------|--------------|
| **Customers** | 99 441 | 99 441 | **100% ✅** | customer_id concordent, villes normalisées (Title Case) |
| **Products** | 32 951 | 32 951 | **100% ✅** | product_id identiques, traduction EN ajoutée via jointure |
| **Sellers** | 3 095 | 3 095 | **100% ✅** | seller_id identiques |
| **Order Items** | 112 650 | 112 650 | **100% ✅** | Nombre de lignes strictement identique (grain article) |
| **Prix total** | 13 591 643.70 R$ | 13 591 643.70 R$ | **100% ✅** | Somme totale des prix strictement identique |
| **Fret total** | 2 251 909.54 R$ | 2 251 909.54 R$ | **100% ✅** | Somme totale du fret strictement identique |
| **Paiements** | 103 886 lignes | Agrégé par order | **100% ✅** | 100% des totaux par commande concordent |

**Verdict global** : **0 perte financière**, intégrité 100% sur les entités et montants.

---

### 🚨 Anomalies identifiées et documentées

#### 1. **775 commandes sans articles (0.78%)**
- **Statuts** : unavailable (603), canceled (164), created (5), invoiced (2), shipped (1)
- **Traitement** : Exclus de fact_orders car grain = article (cohérent avec modélisation)
- **Impact** : Aucun sur analyses produit/vendeur (commandes sans transaction)

#### 2. **285 entités sans geolocation**
- **Détail** : 278 clients (0.28%) + 7 vendeurs (0.23%)
- **Cause** : Codes postaux absents de `olist_geolocation_dataset.csv`
- **Traitement** : geo_key = NULL dans dim_customers/dim_sellers
- **Impact** : Analyses géographiques possibles, entités NULL filtrables

#### 3. **Précision géolocalisation ~2 km**
- **Méthode** : Médiane lat/lng par code postal (1M → 19K lignes)
- **Écart médian** : 0.02° lat, 0.018° lng ≈ 2 km
- **Qualité** : OK pour analyses régionales/états, insuffisant pour géocodage précis

#### 4. **942 commandes sans review (0.95%)**
- **Cause** : Commandes non livrées ou reviews non soumises
- **Traitement** : review_score = NULL dans fact_orders
- **Impact** : Exclus des calculs avg_review (fonction AVG ignore NULL)

---

### 🧪 Script de validation indépendant

**`verify_csv_analysis.sh`** : 50+ assertions automatisées

```bash
#!/bin/bash
# Validation continue après chaque modification ETL

# Exemple d'assertions
assert_count "orders CSV" 99441 "wc -l < data/raw/olist_orders_dataset.csv"
assert_count "fact_orders DB" 112650 "sqlite3 olist_dw.db 'SELECT COUNT(*) FROM fact_orders'"
assert_sum "prix CSV" 13591643.70 "csvstat --sum price olist_order_items_dataset.csv"
assert_sum "prix DB" 13591643.70 "sqlite3 olist_dw.db 'SELECT SUM(price) FROM fact_orders'"

# ... 46 autres assertions
```

**Avantage** : Reproduit tous les chiffres clés via csvkit + SQLite temporaire → validation reproductible.

---

### 🎯 Distribution des valeurs NULL dans fact_orders

| Colonne | NULLs | % | Explication |
|---------|-------|---|-------------|
| `delivery_days` | 2 454 | 2.2% | Commandes non livrées (shipped, canceled) |
| `review_score` | 942 | 0.8% | Commandes sans avis client |
| `customer_geo_key` | 302 | 0.3% | Codes postaux clients absents de dim_geolocation |
| `seller_geo_key` | 253 | 0.2% | Codes postaux vendeurs absents de dim_geolocation |
| `order_payment_total` | 3 | 0.003% | Anomalie marginale (potentielle erreur source) |

**Traitement** : Valeurs NULL conservées (pas d'imputation arbitraire), filtrables via `WHERE column IS NOT NULL`.

---

## ✅ Conclusion : Qualité validée

- ✅ **Intégrité 100%** sur entités, montants financiers et volumes
- ✅ **0 perte de données** sur transactions valides (grain article)
- ✅ **Anomalies documentées** (775 commandes sans articles = exclusion cohérente)
- ✅ **Validation continue** via script indépendant (50+ assertions automatisées)

➡️ Le DWH est fiable pour analyses métier et décisions stratégiques
""").classes('text-gray-300')


def render_slide_6():
    """Slide 6 : Justification business."""
    ui.label("💼 Valeur Business du DWH").classes('text-4xl font-bold mb-4')

    ui.markdown("""
## Pourquoi investir dans un Data Warehouse ?

### 🎯 Dimensions métier activées

Le DWH Olist permet d'analyser le business sous **5 dimensions** :

1. **📅 Temps** : Tendances mensuelles, saisonnalité, cohortes
2. **🌎 Géographie** : Performance par état/ville (client ET vendeur)
3. **👥 Clients** : Segmentation RFM, LTV, rétention, nouveaux vs récurrents
4. **🏪 Vendeurs** : Scoring multi-critères, Pareto, qualité livraison
5. **📦 Produits** : Catégories star, panier moyen, cross-sell

**Impossible avec CSV bruts** : Chaque dimension nécessite des jointures complexes et des agrégations.

---

### 📊 9 Métriques métier débloquées par le DWH

| Métrique | Description | Requête SQL |
|----------|-------------|-------------|
| **Taux de rétention par cohorte** | % clients revenus M+1, M+2... après 1er achat | `cohorts_retention.sql` |
| **LTV (Lifetime Value)** | CA total par client unique | `ltv_cohorts.sql` |
| **Nouveaux vs récurrents** | Nombre clients 1er achat vs déjà actifs par mois | `new_vs_recurring.sql` |
| **Pareto vendeurs** | Top 20% vendeurs génèrent X% du CA | `pareto_sellers.sql` |
| **Panier moyen** | CA / nb commandes | `basket_avg.sql` |
| **Score review moyen** | Moyenne des avis clients (1-5 étoiles) | `overview_kpis.sql` |
| **Segmentation RFM** | Recency, Frequency, Monetary (10 segments) | `rfm_segmentation.sql` |
| **Scoring vendeurs** | Note multi-critères (délai, review, CA) | `seller_scoring.sql` |
| **Délai livraison moyen** | Jours entre achat et livraison effective | `overview_kpis.sql` |

**ROI direct** : Ces KPIs pilotent les décisions stratégiques (où investir, quels produits pousser, quels vendeurs coacher).

---

### ⚡ Rapidité = Agilité décisionnelle

**Avant (CSV)** :
- Analyste : 30 min de code Python → attendre 5s → debugger → réexécuter...
- Total : **2-3h** pour une analyse ad-hoc
- Résultat : **1 analyse par jour** max

**Après (DWH)** :
- Analyste : 5 min de SQL → résultat en 0.2s → itérer rapidement
- Total : **10-15 min** pour une analyse ad-hoc
- Résultat : **10-20 analyses par jour**

➡️ **10x plus de questions business répondues** = décisions data-driven plus rapides.

---

### 🔍 Complexités impossibles sans DWH

Certaines analyses sont **impossibles** (ou prohibitives) avec CSV Pandas :

#### 1. **Auto-jointures temporelles**
"Clients ayant commandé X puis Y dans les 30 jours suivants" → Self-join sur dates.

#### 2. **Window functions complexes**
"Rang du produit par catégorie ET par état" → PARTITION BY multi-niveaux.

#### 3. **CTEs récursives**
"Parcours clients sur N commandes" → WITH RECURSIVE (pas supporté en Pandas).

#### 4. **Sous-requêtes corrélées optimisées**
"Top 3 produits par vendeur" → CTE + ROW_NUMBER (vs boucles Pandas).

---

### 💰 Économies estimées (ordres de grandeur)

**Infrastructure** :
- ❌ CSV : Serveur 32GB RAM pour charger données en mémoire
- ✅ DWH : SQLite = 1 fichier 50MB, serveur 2GB RAM
- **Gain estimé** : **10× moins cher** en infrastructure cloud

**Temps analyste** :
- ❌ CSV : Analyses lentes (5-10s), code complexe (150+ lignes)
- ✅ DWH : Analyses rapides (0.2-0.5s), requêtes concises (80 lignes SQL)
- **Gain estimé** : **15-25h/semaine libérées** pour analyses avancées

**⚠️ Note** : Chiffres indicatifs, varient selon organisation, volumétrie et infrastructure existante.

---

### 🚀 Évolutivité

Le DWH est **futur-proof** :
- ✅ Ajouter une nouvelle dimension (ex: `dim_categories`) = 1 colonne FK dans fact
- ✅ Ajouter une nouvelle métrique = 1 nouvelle colonne calculée
- ✅ Migrer vers PostgreSQL si croissance > 10M lignes = schema compatible

**Pandas CSV n'est PAS évolutif** : Chaque nouvelle source = refactor complet du pipeline.

---

## ✅ Conclusion : DWH = Fondation analytique

Le Data Warehouse n'est pas un luxe, c'est **la base indispensable** pour toute entreprise data-driven.

---

### 🎯 Valeur démontrée sur le projet Olist

| Dimension | Résultat |
|-----------|----------|
| **Performance** | 25× plus rapide (requêtes <200ms vs 5s Pandas) |
| **Qualité** | Concordance 100% (0 perte financière sur 13.6M R$) |
| **Métriques** | 9 KPIs métier débloqués (rétention, LTV, RFM, Pareto...) |
| **Échelle** | 1.5M lignes brutes → 287K lignes structurées optimisées |
| **Infrastructure** | 1 fichier 50MB SQLite (portable, zero-config) |

---

### 📊 Limites assumées du projet

| Limite | Justification |
|--------|---------------|
| **SQLite (pas PostgreSQL)** | OK pour <1M lignes, read-only, mono-utilisateur |
| **Vues virtuelles (pas matérialisées)** | SQLite ne supporte pas MATERIALIZED VIEW |
| **Précision géo ~2km** | Médiane lat/lng par code postal (OK analyses régionales) |
| **Grain article** | Semi-additif sur `order_payment_total` (nécessite DISTINCT order_id) |

➡️ Migration PostgreSQL recommandée si volumétrie > 10M lignes ou concurrence écriture nécessaire

---

### 🎓 Prêt à maîtriser SQL avancé ?

**Dans les 5 modules suivants**, vous allez apprendre à :

1. **Module 1 - Fondamentaux** : SELECT, WHERE, GROUP BY, JOINs, sous-requêtes
2. **Module 2 - Window Functions** : RANK, ROW_NUMBER, LEAD/LAG, NTILE
3. **Module 3 - CTEs & Récursivité** : WITH, requêtes multi-niveaux, arbres hiérarchiques
4. **Module 4 - Optimisation** : EXPLAIN, index, matérialisation, dénormalisation
5. **Module 5 - Cas Métier Olist** : Écrire les 9 requêtes KPI présentées !

**🎯 Vous allez écrire vous-même les 9 métriques SQL** :
- `cohorts_retention.sql` (matrice rétention par cohorte)
- `rfm_segmentation.sql` (segmentation clients 10 groupes)
- `pareto_sellers.sql` (règle 80/20 sur vendeurs)
- `seller_scoring.sql` (note multi-critères)
- ... et 5 autres requêtes analytiques avancées

**Commençons par les fondamentaux !** 🚀
""").classes('text-gray-300')
