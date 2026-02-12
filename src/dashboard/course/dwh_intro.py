"""
Introduction détaillée du Data Warehouse Olist.

7 slides :
1. Contexte Olist (dataset, volumétrie exacte)
2. Processus ETL (5 transformations clés avec justifications empiriques)
3. Schéma en étoile (cardinalités exactes, grain article explicité)
4. Décisions architecturales (1/3) : Grain & Index
5. Décisions architecturales (2/3) : Vues & Clés
6. Décisions architecturales (3/3) : Choix SQLite
7. Validation & Qualité (concordance 100%, anomalies documentées, transition cours)
"""

from nicegui import ui


def render_intro_carousel(initial_index: int = 0):
    """Affiche l'introduction DWH avec navigation manuelle entre slides."""

    total_slides = 7
    clamped_index = max(0, min(total_slides - 1, initial_index))
    current_slide = {'index': clamped_index}
    post_nav_js = '''
        (...args) => {
            const beforeIndex =
                document.getElementById('intro-slide-marker')?.dataset?.slideIndex ?? null;
            const startedAt = Date.now();
            const slideHost = document.getElementById('intro-slide-host');
            const pageShell = document.querySelector('.intro-home-shell');

            const hideDuringTransition = () => {
                if (pageShell) {
                    pageShell.style.pointerEvents = 'none';
                }
                if (slideHost) {
                    slideHost.style.opacity = '0';
                }
            };

            const showAfterTransition = (delay = 200) => {
                setTimeout(() => {
                    if (slideHost) {
                        slideHost.style.opacity = '1';
                    }
                    if (pageShell) {
                        pageShell.style.pointerEvents = '';
                    }
                }, delay);
            };

            const resetScrollTop = () => {
                const anchor = document.getElementById('intro-top');
                const targets = new Set([
                    document.scrollingElement,
                    document.documentElement,
                    document.body,
                ]);
                const active = document.activeElement;

                document
                    .querySelectorAll(
                        '.q-page, .q-page-container, .nicegui-content, .overflow-y-auto, .q-scrollarea__container'
                    )
                    .forEach((el) => targets.add(el));

                if (active && typeof active.blur === 'function') {
                    active.blur();
                }

                targets.forEach((el) => {
                    if (!el) return;
                    try {
                        el.style.overflowAnchor = 'none';
                    } catch (_) {}
                    try {
                        if (typeof el.scrollTo === 'function') {
                            el.scrollTo({top: 0, left: 0, behavior: 'auto'});
                        }
                    } catch (_) {}
                    try {
                        el.scrollTop = 0;
                        el.scrollLeft = 0;
                    } catch (_) {}
                });

                if (anchor) {
                    anchor.scrollIntoView({block: 'start', behavior: 'auto'});
                }
                window.scrollTo({top: 0, left: 0, behavior: 'auto'});
            };

            hideDuringTransition();
            // Garde-fou pour éviter de laisser l'UI masquée en cas d'imprévu.
            showAfterTransition(1800);

            const waitForSlideUpdate = () => {
                const currentIndex =
                    document.getElementById('intro-slide-marker')?.dataset?.slideIndex ?? null;
                const changed = currentIndex !== beforeIndex;
                const timedOut = Date.now() - startedAt > 1400;

                if (changed || timedOut) {
                    requestAnimationFrame(() => {
                        resetScrollTop();
                        setTimeout(resetScrollTop, 140);
                        // Slide 3 (index 2) contient un gros Mermaid qui se stabilise plus tard.
                        if (currentIndex === '2') {
                            setTimeout(resetScrollTop, 360);
                            setTimeout(resetScrollTop, 720);
                            showAfterTransition(780);
                        } else {
                            showAfterTransition(220);
                        }
                    });
                    return;
                }
                setTimeout(waitForSlideUpdate, 35);
            };

            setTimeout(waitForSlideUpdate, 30);
        }
    '''

    # Container principal
    slide_container = (
        ui.column()
        .props('id=intro-slide-host')
        .classes('w-full')
        .style('overflow-anchor: none; opacity: 1; transition: opacity 0.14s ease;')
    )

    def go_to_slide(index: int):
        """Navigue vers un slide précis sans recharger la page."""
        target_index = max(0, min(total_slides - 1, index))
        if target_index == current_slide['index']:
            return
        current_slide['index'] = target_index
        render_slide(target_index)

    def go_prev():
        """Navigue vers le slide précédent."""
        go_to_slide(current_slide['index'] - 1)

    def go_next():
        """Navigue vers le slide suivant."""
        go_to_slide(current_slide['index'] + 1)

    def render_slide(index: int):
        """Affiche le slide à l'index donné."""
        slide_container.clear()

        with slide_container:
            ui.element('div').props('id=intro-slide-marker').props(
                f'data-slide-index={index}'
            ).classes('hidden')

            # Progress indicator
            with ui.column().classes('w-full items-center mb-6'):
                # Dots
                with ui.row().classes('gap-2'):
                    for i in range(total_slides):
                        if i == index:
                            ui.label('●').classes('text-green-500 text-3xl min-w-0 px-1')
                        else:
                            ui.button('○', on_click=lambda target=i: go_to_slide(target)).props(
                                'flat dense'
                            ).classes(
                                'text-gray-600 hover:text-gray-400 text-3xl min-w-0 px-1'
                            ).on('click', js_handler=post_nav_js)

                # Indicateur textuel
                slide_titles = [
                    "Le Dataset Olist",
                    "Le Processus ETL",
                    "Schéma en Étoile",
                    "Décisions Architecturales (1/3)",
                    "Décisions Architecturales (2/3)",
                    "Décisions Architecturales (3/3)",
                    "Validation & Qualité"
                ]
                ui.label(f"{index + 1}/7 — {slide_titles[index]}").classes('text-xs text-gray-500 mt-1')

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
                elif index == 6:
                    render_slide_7()

            # Navigation
            with ui.row().classes('w-full justify-between mt-4 intro-nav-footer'):
                if index > 0:
                    ui.button('← Précédent', on_click=go_prev).props('outline color=primary').on(
                        'click', js_handler=post_nav_js
                    )
                else:
                    ui.label('')  # Spacer

                if index < total_slides - 1:
                    ui.button('Suivant →', on_click=go_next).props('color=primary').on(
                        'click', js_handler=post_nav_js
                    )
                else:
                    ui.button('Commencer le cours 🚀', on_click=start_course).props('color=positive')

    def start_course():
        """Redirige vers la première leçon."""
        ui.navigate.to('/presentation/module_1_fundamentals/0')

    # Afficher premier slide
    render_slide(current_slide['index'])


def render_slide_1():
    """Slide 1 : Contexte Olist."""
    ui.label("🎯 Le Dataset Olist").classes('text-4xl font-bold mb-2')
    ui.label("E-commerce brésilien : 1.5M lignes brutes sur 99k commandes").classes('text-2xl text-gray-400 mb-8')

    ui.markdown("""
## Dataset E-commerce Brésilien (2016-2018)

**Olist** est une plateforme e-commerce brésilienne qui connecte des milliers de vendeurs indépendants avec les plus grandes marketplaces du pays.
""").classes('text-gray-300 mb-6')

    ui.markdown("""
### Les chiffres clés
- 🛒 **99 441 commandes** sur 24 mois (septembre 2016 - octobre 2018)
- 👥 **96 096 clients** uniques (`customer_unique_id`)
- 🏪 **3 095 vendeurs** actifs
- 📦 **32 951 produits** différents
- 📍 **19 015 codes postaux** uniques (couvrant 27 états brésiliens)
- 🌎 **27 états** brésiliens couverts
""").classes('text-gray-300 mb-6')

    ui.markdown("""
### Volumétrie totale des données sources
**1 550 871 lignes brutes** réparties dans **9 fichiers CSV**, dont :
- 77% (1M lignes) = geolocation à dédupliquer
- 23% = données transactionnelles et référentielles
""").classes('text-gray-300 mb-6')

    ui.markdown("""
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
""").classes('text-gray-300')

    # Encadré de conclusion
    with ui.card().classes('w-full bg-green-900/20 border-l-4 border-green-500 p-4 rounded mt-8'):
        ui.markdown("""
➡️ **À retenir** : Le dataset Olist contient 1.5M lignes brutes (9 CSV) couvrant 99k commandes, 96k clients et 3k vendeurs sur 24 mois de e-commerce brésilien.
""").classes('text-gray-300')


def render_slide_2():
    """Slide 2 : Processus ETL."""
    ui.label("⚙️ Le Processus ETL").classes('text-4xl font-bold mb-2')
    ui.label("De 1.5M lignes brutes à un DWH optimisé en 4 phases").classes('text-2xl text-gray-400 mb-8')

    ui.markdown("""
Notre pipeline suit les **4 phases** définies dans `src/etl/pipeline.py`.
""").classes('text-gray-300 mb-6')

    # Diagramme Mermaid dans une card avec fond
    with ui.card().classes('w-full bg-gray-900/50 p-6 mb-8'):
        ui.mermaid("""
graph LR
    A[9 CSV Sources<br/>1.5M lignes] -->|Phase 1: EXTRACT| B[9 DataFrames bruts]
    B -->|Phase 2: TRANSFORM| C[9 DataFrames nettoyés]
    C -->|Phase 3: BUILD| D[5 Dimensions + 1 Fait]
    D -->|Phase 4: LOAD| E[(SQLite DWH<br/>267k lignes)]

    style A fill:#e74c3c
    style B fill:#f39c12
    style C fill:#3498db
    style D fill:#9b59b6
    style E fill:#27ae60
""").classes('w-full')

    # ── PHASE 1: EXTRACT ──
    ui.label("Phase 1 : EXTRACT — load_all_raw()").classes('text-2xl font-bold mb-4 mt-8')
    ui.markdown("""
**Fichier** : `src/etl/extract.py`

Chargement des **9 fichiers CSV** bruts dans un dictionnaire de DataFrames Pandas.
""").classes('text-gray-300 mb-4')

    ui.label("🐍 Python").classes('text-sm font-semibold mb-2')
    with ui.card().classes('w-full bg-gray-900 p-4 mb-4'):
        ui.code("""def load_all_raw() -> dict[str, pd.DataFrame]:
    dfs = {}
    for name in CSV_FILES:  # 9 datasets
        dfs[name] = pd.read_csv(RAW_DIR / CSV_FILES[name])
    return dfs""", language='python').classes('text-sm')

    ui.markdown("""
**Résultat** : 1 550 871 lignes brutes chargées en mémoire (9 DataFrames).
""").classes('text-gray-300 mb-8')

    # ── PHASE 2: TRANSFORM ──
    ui.label("Phase 2 : TRANSFORM — clean_all()").classes('text-2xl font-bold mb-4 mt-8')
    ui.markdown("""
**Fichier** : `src/etl/transform.py`

Nettoyage et normalisation de chaque dataset via **9 fonctions de nettoyage** :
- `clean_customers()`, `clean_geolocation()`, `clean_orders()`, `clean_order_items()`
- `clean_order_payments()`, `clean_order_reviews()`, `clean_products()`, `clean_sellers()`
- `clean_category_translation()`

**Opérations communes** : déduplication, parsing dates, normalisation texte, validation métier.
""").classes('text-gray-300 mb-6')

    # Focus sur clean_geolocation (la plus impactante)
    with ui.card().classes('w-full bg-blue-900/20 border-l-4 border-blue-500 p-6 mb-6'):
        ui.label("🔹 Focus : clean_geolocation()").classes('text-xl font-bold mb-3')
        ui.markdown("""
**Problème** : 1 000 163 lignes pour seulement 19K codes postaux uniques (53 entrées/zip en moyenne)

**Solution** : Déduplication par `zip_code_prefix` avec médiane lat/lng (robuste aux outliers)

**Résultat** : 1M → **19 015 lignes** (réduction 98%), précision ~2km
""").classes('text-gray-300 mb-4')

        ui.label("🐍 Python").classes('text-sm font-semibold mb-2')
        with ui.card().classes('w-full bg-gray-900 p-4'):
            ui.code("""def clean_geolocation(df):
    agg = df.groupby('geolocation_zip_code_prefix').agg(
        geolocation_lat=('geolocation_lat', 'median'),
        geolocation_lng=('geolocation_lng', 'median'),
        geolocation_city=('geolocation_city', safe_mode),
        geolocation_state=('geolocation_state', safe_mode),
    ).reset_index()
    return agg  # 1M → 19K lignes""", language='python').classes('text-xs')

    ui.markdown("""
**Résultat global Phase 2** : 9 DataFrames nettoyés prêts pour la modélisation dimensionnelle.
""").classes('text-gray-300 mb-8')

    # ── PHASE 3: BUILD DIMENSIONS ──
    ui.label("Phase 3 : BUILD — Modélisation dimensionnelle").classes('text-2xl font-bold mb-4 mt-8')
    ui.markdown("""
**Fichier** : `src/etl/load.py`

Construction des **5 dimensions** + **1 table de faits** avec feature engineering avancé.
""").classes('text-gray-300 mb-6')

    # Étape 3.1 : Dimensions avec clés surrogate
    with ui.card().classes('w-full bg-blue-900/20 border-l-4 border-blue-500 p-6 mb-6'):
        ui.label("🔹 Étape 1 : Construire les 5 dimensions").classes('text-xl font-bold mb-3')
        ui.markdown("""
**Fonctions** : `build_dim_dates()`, `build_dim_geolocation()`, `build_dim_customers()`, `build_dim_sellers()`, `build_dim_products()`

**Clés surrogate** : Chaque dimension reçoit une clé `INTEGER` auto-incrémentée (1, 2, 3...) via `_add_surrogate_key()`
- `customer_key`, `seller_key`, `product_key`, `geo_key`, `date_key`
- **Impact** : 8× plus compact que UUID (4 bytes vs 32), jointures ultra-rapides
""").classes('text-gray-300')

    # Étape 3.2 : Table de faits avec 4 transformations
    with ui.card().classes('w-full bg-blue-900/20 border-l-4 border-blue-500 p-6 mb-6'):
        ui.label("🔹 Étape 2 : build_fact_orders() — 4 transformations clés").classes('text-xl font-bold mb-3')

        ui.markdown("""
**1. Agrégation paiements** (lignes 179-182)
- **Problème** : 103 886 lignes paiements pour 99 441 commandes
- **Solution** : `groupby('order_id').agg(order_payment_total=sum, payment_type=mode)`
- **Résultat** : 1 ligne par commande avec montant total + type dominant

**2. Sélection review plus récent** (lignes 185-189)
- **Problème** : 547 commandes avec reviews multiples (0.5%)
- **Solution** : `sort_values('review_creation_date').drop_duplicates('order_id', keep='first')`
- **Résultat** : 1 review par commande (la plus récente)

**3. Résolution clés surrogate** (lignes 196-205)
- **Méthode** : Mapping `customer_id → customer_key` via lookup dict
- **Résultat** : Toutes les FK en INTEGER, plus de UUID dans la fact

**4. Métriques de livraison** (lignes 221-229)
- **Calculs** : `delivery_days`, `estimated_days`, `delivery_delta_days`
- **Résultat** : KPIs temporels précalculés pour analyses logistiques
""").classes('text-gray-300')

    ui.markdown("""
**Résultat Phase 3** : 6 tables prêtes pour le chargement (267 867 lignes au total).
""").classes('text-gray-300 mb-8')

    # ── PHASE 4: LOAD ──
    ui.label("Phase 4 : LOAD — load_to_sqlite()").classes('text-2xl font-bold mb-4 mt-8')
    ui.markdown("""
**Fichier** : `src/etl/load.py` (lignes 246-309)

Chargement atomique dans SQLite avec transaction garantie via fichier temporaire.
""").classes('text-gray-300 mb-6')

    with ui.card().classes('w-full bg-blue-900/20 border-l-4 border-blue-500 p-6 mb-6'):
        ui.label("🔹 Étape 1 : Création du schéma").classes('text-xl font-bold mb-3')
        ui.markdown("""
**Script DDL** : `sql/create_star_schema.sql`
- CREATE TABLE pour les 6 tables (5 dims + 1 fact)
- Définition des FK (FOREIGN KEY vers dimensions)
- Création de **8 index stratégiques** sur fact_orders
""").classes('text-gray-300')

    with ui.card().classes('w-full bg-blue-900/20 border-l-4 border-blue-500 p-6 mb-6'):
        ui.label("🔹 Étape 2 : Insertion des données").classes('text-xl font-bold mb-3')
        ui.label("🐍 Python").classes('text-sm font-semibold mb-2')
        with ui.card().classes('w-full bg-gray-900 p-4 mb-4'):
            ui.code("""# Chargement par batch de 5000 lignes
for name, df in tables:
    df.to_sql(name, conn, if_exists='append',
              index=False, chunksize=5000)""", language='python').classes('text-sm')
        ui.markdown("""
**Ordre** : dim_dates → dim_geolocation → dim_customers → dim_sellers → dim_products → fact_orders
""").classes('text-gray-300')

    with ui.card().classes('w-full bg-blue-900/20 border-l-4 border-blue-500 p-6 mb-6'):
        ui.label("🔹 Étape 3 : Création des vues analytiques").classes('text-xl font-bold mb-3')
        ui.markdown("""
**Script** : `sql/views.sql`
- `v_monthly_sales` : Ventes mensuelles agrégées
- `v_customer_cohorts` : Cohortes clients
- `v_orders_enriched` : Fait dénormalisé avec toutes dimensions
""").classes('text-gray-300')

    # Encadré de conclusion
    with ui.card().classes('w-full bg-green-900/20 border-l-4 border-green-500 p-4 rounded mt-8'):
        ui.markdown("""
➡️ **À retenir** : Le pipeline suit 4 phases (`src/etl/pipeline.py`) : **EXTRACT** (9 CSV → DataFrames), **TRANSFORM** (9 cleaners dont geolocation 1M→19k), **BUILD** (5 dimensions + 1 fait avec 4 feature engineering), **LOAD** (SQLite avec 8 index + 3 vues). Résultat : 1.5M lignes brutes → 268k lignes modélisées.
""").classes('text-gray-300')


def render_slide_3():
    """Slide 3 : Schéma en étoile."""
    ui.label("⭐ Schéma en Étoile").classes('text-4xl font-bold mb-2')
    ui.label("1 table de faits + 5 dimensions, grain article").classes('text-2xl text-gray-400 mb-8')

    ui.markdown("""
## Modélisation dimensionnelle : Le cœur du DWH

Le schéma en étoile est le standard pour les Data Warehouses analytiques.
""").classes('text-gray-300 mb-6')

    # Schéma ERD avec Mermaid
    ui.mermaid("""
erDiagram
    dim_customers ||--o{ fact_orders : "customer_key"
    dim_sellers ||--o{ fact_orders : "seller_key"
    dim_products ||--o{ fact_orders : "product_key"
    dim_dates ||--o{ fact_orders : "date_key"
    dim_geolocation ||--o{ fact_orders : "customer_geo_key / seller_geo_key"

    fact_orders {
        int fact_key PK
        string order_id
        int order_item_id
        int date_key FK
        int customer_key FK
        int seller_key FK
        int product_key FK
        int customer_geo_key FK
        int seller_geo_key FK
        string order_status
        decimal price
        decimal freight_value
        decimal order_payment_total
        string payment_type
        int review_score
        decimal delivery_days
    }

    dim_customers {
        int customer_key PK
        string customer_id
        string customer_unique_id
        int geo_key FK
        string city
        string state
    }

    dim_sellers {
        int seller_key PK
        string seller_id
        int geo_key FK
        string city
        string state
    }

    dim_products {
        int product_key PK
        string product_id
        string category_name_pt
        string category_name_en
        decimal weight_g
        decimal length_cm
        decimal height_cm
        decimal width_cm
    }

    dim_geolocation {
        int geo_key PK
        string zip_code_prefix
        string city
        string state
        float lat
        float lng
    }

    dim_dates {
        int date_key PK
        date full_date
        int year
        int quarter
        int month
        int day
        int day_of_week
        int is_weekend
    }
""").classes('w-full mb-8')

    ui.markdown("""
### 📊 Cardinalités

| Table | Lignes | Rôle |
|-------|--------|------|
| **fact_orders** | 112 650 | **Table de faits** (transactions) |
| dim_customers | 99 441 | Attributs clients (1 ligne par `customer_id`) |
| dim_sellers | 3 095 | Attributs vendeurs |
| dim_products | 32 951 | Catégories, dimensions produits |
| dim_geolocation | 19 015 | Codes postaux dédoublonnés |
| dim_dates | 715 | Calendrier (2016-09-04 → 2018-11-12) |
""").classes('text-gray-300 mb-6')

    ui.markdown("""
### 🔑 Grain de la table de faits
**1 ligne = 1 article d'une commande** (order_id + order_item_id)

**Distribution grain commande → article** :
- **90.1% des commandes** = 1 seul article (mono-item)
- **9.9% des commandes** = 2 à 21 articles (multi-items)
- **Dans la fact** : 98 666 commandes avec articles → 112 650 lignes (ratio 1.14)
- **Source orders** : 99 441 commandes au total, dont 775 sans article (exclues du grain)

**Exemple** : Commande #abc123 avec 3 articles → 3 lignes dans fact_orders (order_item_id = 1, 2, 3)

**Pourquoi ce grain ?**
- ✅ Permet d'agréger au niveau commande (`GROUP BY order_id`) ou article
- ✅ Conserve le détail maximal (prix unitaire par article, vendeur par article)
- ✅ Facilite les analyses produit (quel article génère le plus de CA ?)
""").classes('text-gray-300 mb-6')

    ui.markdown("""
**⚠️ Attention aux métriques semi-additives** :
- `order_payment_total` est au grain **commande**, pas article
- Exemple : Commande 100 R$ avec 2 articles → chaque ligne affiche 100 R$
- **Pour obtenir le total correct** : `SELECT DISTINCT order_id, order_payment_total` puis SUM
""").classes('text-gray-300 mb-6')

    ui.markdown("""
### 🎯 Avantages du schéma en étoile
- ✅ **Jointures simples** : 1 saut de la fact vers chaque dimension
- ✅ **Performance** : Clés surrogate (int) ultra-rapides (8× moins d'espace que UUID)
- ✅ **Lisibilité** : Structure intuitive (centre + branches)
- ✅ **Flexibilité** : Ajouter une dimension = 1 colonne FK dans fact
""").classes('text-gray-300')

    # Encadré de conclusion
    with ui.card().classes('w-full bg-green-900/20 border-l-4 border-green-500 p-4 rounded mt-8'):
        ui.markdown("""
➡️ **À retenir** : Le schéma en étoile (1 fait + 5 dimensions) permet des jointures simples, des clés surrogate ultra-rapides (int vs UUID) et une flexibilité analytique maximale. Grain = 1 article par ligne (112k lignes).
""").classes('text-gray-300')


def render_slide_4():
    """Slide 4 : Décisions architecturales (1/3) - Grain & Index."""
    ui.label("🏗️ Décisions Architecturales (1/3)").classes('text-4xl font-bold mb-2')
    ui.label("Choix de granularité et optimisation des accès").classes('text-2xl text-gray-400 mb-8')

    # Section 1 : Grain
    with ui.card().classes('w-full bg-blue-900/20 border-l-4 border-blue-500 p-6 mb-6'):
        ui.label("1. Grain : Article vs Commande").classes('text-xl font-bold mb-3')
        ui.markdown("""
**Option 1 - Grain "Commande"** (rejeté) :
- ❌ Perd le détail par article
- ❌ Prix agrégés (impossible de savoir quel produit coûte combien)
- ❌ Reviews moyennées (perd la granularité)

**Option 2 - Grain "Article"** (✅ choisi) :
- ✅ Détail maximal conservé
- ✅ Agréger au niveau commande reste possible (`GROUP BY order_id`)
- ✅ Analyses produit facilitées

➡️ **Décision** : 1 ligne = 1 article (112k lignes dans fact_orders)
""").classes('text-gray-300')

    # Section 2 : Index
    with ui.card().classes('w-full bg-blue-900/20 border-l-4 border-blue-500 p-6 mb-6'):
        ui.label("2. Index Stratégiques").classes('text-xl font-bold mb-3')
        ui.markdown("""
Les index accélèrent les recherches de O(n) → O(log n).

**Impact** :
- Filtres sur `date_key` et `order_status` accélérés
- Jointures fact → dimensions soutenues par index sur clés étrangères
- Gains variables selon machine, cache SQLite et complexité de la requête

**Principe** : Indexer les clés de jointure + colonnes de filtrage fréquentes.
""").classes('text-gray-300 mb-4')

        ui.label("💻 SQL").classes('text-sm font-semibold mb-2')
        with ui.card().classes('w-full bg-gray-900 p-4'):
            ui.code("""CREATE INDEX idx_fact_order_id ON fact_orders(order_id);
CREATE INDEX idx_fact_date_key ON fact_orders(date_key);
CREATE INDEX idx_fact_customer_key ON fact_orders(customer_key);
CREATE INDEX idx_fact_seller_key ON fact_orders(seller_key);
CREATE INDEX idx_fact_product_key ON fact_orders(product_key);
CREATE INDEX idx_fact_order_status ON fact_orders(order_status);
CREATE INDEX idx_fact_customer_geo ON fact_orders(customer_geo_key);
CREATE INDEX idx_fact_seller_geo ON fact_orders(seller_geo_key);""", language='sql').classes('text-xs')

    # Encadré de conclusion
    with ui.card().classes('w-full bg-green-900/20 border-l-4 border-green-500 p-4 rounded mt-8'):
        ui.markdown("""
➡️ **À retenir** : Le grain article conserve le détail maximal tout en permettant l'agrégation au niveau commande. Les 8 index stratégiques accélèrent les jointures et les filtres fréquents.
""").classes('text-gray-300')

def render_slide_5():
    """Slide 5 : Décisions architecturales (2/3) - Vues & Clés."""
    ui.label("🏗️ Décisions Architecturales (2/3)").classes('text-4xl font-bold mb-2')
    ui.label("Abstraction analytique et optimisation du stockage").classes('text-2xl text-gray-400 mb-8')

    # Section 3 : Vues
    ui.markdown("""
### Vues Analytiques (virtuelles, pas matérialisées)

⚠️ **SQLite ne supporte PAS les vues matérialisées** (contrairement à PostgreSQL)

Les vues créées sont **virtuelles** : recalculées à chaque SELECT, pas de cache physique.
""").classes('text-gray-300 mb-6')

    # Vue 1 : v_monthly_sales
    with ui.card().classes('w-full bg-blue-900/20 border-l-4 border-blue-500 p-6 mb-6'):
        ui.label("📊 v_monthly_sales : Ventes mensuelles agrégées").classes('text-xl font-bold mb-3')
        ui.label("💻 SQL").classes('text-sm font-semibold mb-2')
        with ui.card().classes('w-full bg-gray-900 p-4'):
            ui.code("""CREATE VIEW v_monthly_sales AS
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
GROUP BY d.year, d.month;""", language='sql').classes('text-xs')

    # Vue 2 : v_customer_cohorts
    with ui.card().classes('w-full bg-blue-900/20 border-l-4 border-blue-500 p-6 mb-6'):
        ui.label("👥 v_customer_cohorts : Clients avec mois de première commande").classes('text-xl font-bold mb-3')
        ui.label("💻 SQL").classes('text-sm font-semibold mb-2')
        with ui.card().classes('w-full bg-gray-900 p-4'):
            ui.code("""CREATE VIEW v_customer_cohorts AS
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
GROUP BY c.customer_unique_id;""", language='sql').classes('text-xs')

    # Vue 3 : v_orders_enriched
    with ui.card().classes('w-full bg-blue-900/20 border-l-4 border-blue-500 p-6 mb-6'):
        ui.label("📦 v_orders_enriched : Commandes avec toutes dimensions joinées").classes('text-xl font-bold mb-3')
        ui.markdown("""
Vue dénormalisée pour analyses ad-hoc sans réécrire les JOINs.

**Avantage** : Requêtes complexes deviennent `SELECT * FROM v_monthly_sales`.

**Limite** : Pas de cache. Pour matérialiser : `CREATE TABLE AS SELECT ...` (manuelle).
""").classes('text-gray-300')

    # Section 4 : Clés Surrogate
    with ui.card().classes('w-full bg-blue-900/20 border-l-4 border-blue-500 p-6 mb-6'):
        ui.label("4. Clés Surrogate vs Clés Naturelles").classes('text-xl font-bold mb-3')
        ui.markdown("""
**Clé naturelle** : `customer_id` (string UUID 32 chars, 32 bytes)

**Clé surrogate** : `customer_key` (integer auto-incrémenté, 4 bytes)

**Impact** :
- ✅ **8x moins d'espace** (4 bytes vs 32)
- ✅ **Jointures plus rapides** (égalité sur int vs string)
- ✅ **Index plus compacts** (B-Tree sur int = optimal)

➡️ **Décision** : Toutes les FK utilisent des clés surrogate (customer_key, seller_key, product_key).
""").classes('text-gray-300')

    # Encadré de conclusion
    with ui.card().classes('w-full bg-green-900/20 border-l-4 border-green-500 p-4 rounded mt-8'):
        ui.markdown("""
➡️ **À retenir** : Les 3 vues virtuelles (v_monthly_sales, v_customer_cohorts, v_orders_enriched) simplifient les requêtes complexes. Les clés surrogate (int 4 bytes) sont 8× plus efficaces que les UUID (32 bytes).
""").classes('text-gray-300')

def render_slide_6():
    """Slide 6 : Décisions architecturales (3/3) - Choix SQLite."""
    ui.label("🏗️ Décisions Architecturales (3/3)").classes('text-4xl font-bold mb-2')
    ui.label("Pourquoi SQLite pour un DWH analytique mono-utilisateur").classes('text-2xl text-gray-400 mb-8')

    ui.markdown("""
### SQLite vs PostgreSQL

Pourquoi SQLite pour un DWH ?
""").classes('text-gray-300 mb-6')

    # Avantages SQLite
    with ui.card().classes('w-full bg-green-900/20 border-l-4 border-green-500 p-6 mb-6'):
        ui.label("✅ Avantages SQLite").classes('text-xl font-bold mb-3')
        ui.markdown("""
- ✅ **Zero-config** : 1 fichier .db, pas de serveur
- ✅ **Portable** : Copier le .db = copier tout le DWH
- ✅ **Rapide** : Window functions performantes, optimiseur correct
- ✅ **Suffisant** : volume actuel du DWH = ~268k lignes (dont 112k dans fact_orders)
""").classes('text-gray-300')

    # Limites SQLite
    with ui.card().classes('w-full bg-orange-900/20 border-l-4 border-orange-500 p-6 mb-6'):
        ui.label("⚠️ Limites SQLite (OK pour notre use case)").classes('text-xl font-bold mb-3')
        ui.markdown("""
- ❌ Pas de concurrence écriture (read-only en prod = OK)
- ❌ Pas de réplication (backup fichier = OK)
- ❌ Pas de partitionnement (pas nécessaire à 112k lignes)
""").classes('text-gray-300')

    # Décision finale
    with ui.card().classes('w-full bg-green-900/20 border-l-4 border-green-500 p-6 mb-6'):
        ui.label("📌 Décision").classes('text-xl font-bold mb-3')
        ui.markdown("""
SQLite est idéal pour un DWH analytique mono-utilisateur de notre volumétrie (268k lignes).
""").classes('text-gray-300')

    # Encadré de conclusion
    with ui.card().classes('w-full bg-green-900/20 border-l-4 border-green-500 p-4 rounded mt-8'):
        ui.markdown("""
➡️ **À retenir** : SQLite est idéal pour notre DWH analytique de 268k lignes : zero-config, portable, performant, et suffisant pour un usage mono-utilisateur en lecture.
""").classes('text-gray-300')


def render_slide_7():
    """Slide 7 : Validation & Qualité des Données."""
    ui.label("✅ Validation & Qualité").classes('text-4xl font-bold mb-2')
    ui.label("Concordance 100% sur 267k lignes modélisées").classes('text-2xl text-gray-400 mb-8')

    ui.markdown("""
## Intégrité des transformations CSV → DWH

La validation systématique garantit que les transformations ETL n'ont introduit aucune perte de données ni erreur de calcul.
""").classes('text-gray-300 mb-8')

    ui.markdown("""
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
""").classes('text-gray-300 mb-8')

    ui.markdown("""
### 🚨 Anomalies identifiées et documentées
""").classes('text-gray-300 mb-6')

    # Anomalie 1
    with ui.card().classes('w-full bg-orange-900/20 border-l-4 border-orange-500 p-6 mb-6'):
        ui.label("1. 775 commandes sans articles (0.78%)").classes('text-xl font-bold mb-3')
        ui.markdown("""
- **Statuts** : unavailable (603), canceled (164), created (5), invoiced (2), shipped (1)
- **Traitement** : Exclus de fact_orders car grain = article (cohérent avec modélisation)
- **Impact** : Aucun sur analyses produit/vendeur (commandes sans transaction)
""").classes('text-gray-300')

    # Anomalie 2
    with ui.card().classes('w-full bg-orange-900/20 border-l-4 border-orange-500 p-6 mb-6'):
        ui.label("2. 285 entités sans geolocation").classes('text-xl font-bold mb-3')
        ui.markdown("""
- **Détail** : 278 clients (0.28%) + 7 vendeurs (0.23%)
- **Cause** : Codes postaux absents de `olist_geolocation_dataset.csv`
- **Traitement** : geo_key = NULL dans dim_customers/dim_sellers
- **Impact** : Analyses géographiques possibles, entités NULL filtrables
""").classes('text-gray-300')

    # Anomalie 3
    with ui.card().classes('w-full bg-orange-900/20 border-l-4 border-orange-500 p-6 mb-6'):
        ui.label("3. Précision géolocalisation ~2 km").classes('text-xl font-bold mb-3')
        ui.markdown("""
- **Méthode** : Médiane lat/lng par code postal (1M → 19K lignes)
- **Écart médian** : 0.02° lat, 0.018° lng ≈ 2 km
- **Qualité** : OK pour analyses régionales/états, insuffisant pour géocodage précis
""").classes('text-gray-300')

    # Anomalie 4
    with ui.card().classes('w-full bg-orange-900/20 border-l-4 border-orange-500 p-6 mb-8'):
        ui.label("4. Reviews manquantes dans fact_orders").classes('text-xl font-bold mb-3')
        ui.markdown("""
- **Constat** : 942 lignes avec `review_score` NULL (0.84%), soit 749 commandes distinctes
- **Cause** : Commandes non livrées ou reviews non soumises
- **Traitement** : `review_score` conservé à NULL dans fact_orders
- **Impact** : Exclues des calculs avg_review (`AVG` ignore les NULL)
""").classes('text-gray-300')

    ui.markdown("""
### 🧪 Script de validation indépendant

**`verify_csv_analysis.sh`** : plusieurs dizaines d'assertions automatisées
""").classes('text-gray-300 mb-4')

    ui.label("🖥️ Bash").classes('text-sm font-semibold mb-2')
    with ui.card().classes('w-full bg-gray-900 p-4 mb-4'):
        ui.code("""#!/bin/bash
# Validation indépendante (CSV bruts -> SQLite temporaire)
sum_price=$(query_db "
  SELECT PRINTF('%.2f', SUM(CAST(price AS REAL)))
  FROM olist_order_items_dataset;
")
check_value "SUM(price)" "13591643.70" "$sum_price"

no_items_total=$(query_db "
  SELECT COUNT(*) FROM olist_orders_dataset
  WHERE order_id NOT IN (SELECT DISTINCT order_id FROM olist_order_items_dataset);
")
check_value "Commandes sans articles (total)" "775" "$no_items_total\"""", language='bash').classes('text-xs')

    ui.markdown("""
**Avantage** : Reproduit tous les chiffres clés via csvkit + SQLite temporaire → validation reproductible.
""").classes('text-gray-300 mb-8')

    ui.markdown("""
### 🎯 Distribution des valeurs NULL dans fact_orders

| Colonne | NULLs | % | Explication |
|---------|-------|---|-------------|
| `delivery_days` | 2 454 | 2.18% | Commandes non livrées (shipped, canceled, unavailable...) |
| `review_score` | 942 | 0.84% | Lignes fact sans avis (749 commandes distinctes) |
| `customer_geo_key` | 302 | 0.27% | Codes postaux clients absents de dim_geolocation |
| `seller_geo_key` | 253 | 0.23% | Codes postaux vendeurs absents de dim_geolocation |
| `order_payment_total` | 3 | 0.003% | Anomalie marginale (potentielle erreur source) |

**Traitement** : Valeurs NULL conservées (pas d'imputation arbitraire), filtrables via `WHERE column IS NOT NULL`.
""").classes('text-gray-300 mb-8')

    # Encadré de conclusion
    with ui.card().classes('w-full bg-green-900/20 border-l-4 border-green-500 p-4 rounded mt-8'):
        ui.markdown("""
➡️ **À retenir** : Intégrité 100% sur entités et montants financiers (13.6M R$ prix + 2.3M R$ fret). 0 perte de données sur transactions valides. Anomalies documentées (775 commandes sans articles = exclusion cohérente). Le DWH est fiable pour analyses métier et décisions stratégiques.
""").classes('text-gray-300')

    ui.markdown("")  # Spacer

    ui.markdown("""
---

## 🎓 Prêt à maîtriser SQL avancé ?

Vous allez maintenant apprendre à exploiter ce Data Warehouse avec **SQL avancé** :

**5 modules progressifs** :
1. **Fondamentaux** : SELECT, WHERE, GROUP BY, JOINs, sous-requêtes
2. **Window Functions** : RANK, ROW_NUMBER, LEAD/LAG, NTILE
3. **CTEs & Récursivité** : WITH, requêtes multi-niveaux
4. **Optimisation** : EXPLAIN, index, matérialisation
5. **Cas Métier Olist** : Cohortes, RFM, Pareto, Scoring vendeurs

**🎯 Objectif** : Écrire vous-même les 9 métriques KPI du DWH Olist

**Commençons ! 🚀**
""").classes('text-gray-300')
