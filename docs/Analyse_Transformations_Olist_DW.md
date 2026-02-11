# Analyse des Transformations : CSV Sources vers Data Warehouse

**Projet Olist - E-commerce Bresilien**
Auteur : Sam | Date : 11 fevrier 2026 | Projet 3 - Simplon

---

## Sommaire

1. [Contexte et objectifs](#1-contexte-et-objectifs)
2. [Schema des donnees sources (CSV)](#2-schema-des-donnees-sources-csv)
3. [Schema du Data Warehouse](#3-schema-du-data-warehouse-modele-en-etoile)
4. [Detail des transformations ETL](#4-detail-des-transformations-etl)
5. [Analyse de concordance](#5-analyse-de-concordance)
6. [Anomalies et points d'attention](#6-anomalies-et-points-dattention)
7. [Analyse des ecarts de paiement](#7-analyse-des-ecarts-de-paiement)
8. [Taux d'interet implicite du parcelamento](#8-taux-dinteret-implicite-du-parcelamento)
9. [Vues analytiques](#9-vues-analytiques)
10. [Conclusion](#10-conclusion)

---

## 1. Contexte et objectifs

Ce document analyse les transformations appliquees aux donnees brutes de la marketplace bresilienne Olist pour construire un Data Warehouse analytique. L'objectif est de documenter chaque etape de transformation, de valider la coherence des donnees entre les CSV sources et la base SQLite resultante, et d'identifier les eventuelles anomalies.

**Perimetre des donnees :** 9 fichiers CSV contenant plus de 100 000 commandes Olist entre septembre 2016 et octobre 2018, transformes en un modele en etoile compose de 5 dimensions et 1 table de faits, plus 3 vues analytiques precalculees.

**Architecture cible :** Modele dimensionnel en etoile (star schema) dans SQLite, optimise pour l'analyse des performances commerciales, la satisfaction client et la logistique de livraison.

---

## 2. Schema des donnees sources (CSV)

Les donnees sources sont composees de 9 fichiers CSV issus de la plateforme Olist. Elles suivent un modele operationnel normalise, avec des identifiants textuels (hash UUID) comme cles primaires.

| Fichier CSV | Lignes | Col. | Cle primaire | Description |
|---|---|---|---|---|
| **olist_customers_dataset** | 99 441 | 5 | customer_id | Clients uniques par commande |
| **olist_orders_dataset** | 99 441 | 8 | order_id | Commandes avec statuts et timestamps |
| **olist_order_items_dataset** | 112 650 | 7 | order_id + order_item_id | Articles par commande (grain le plus fin) |
| **olist_order_payments_dataset** | 103 886 | 5 | order_id + payment_sequential | Paiements multiples par commande |
| **olist_order_reviews_dataset** | 99 224 | 7 | review_id | Avis clients (score + commentaires) |
| **olist_products_dataset** | 32 951 | 9 | product_id | Catalogue produits avec dimensions |
| **olist_sellers_dataset** | 3 095 | 4 | seller_id | Vendeurs marketplace |
| **olist_geolocation_dataset** | 1 000 163 | 5 | aucune (multi-entrees par zip) | Coordonnees GPS par code postal |
| **product_category_name_translation** | 71 | 2 | product_category_name | Traduction PT -> EN des categories |

### Points cles du modele source

- Les identifiants (customer_id, order_id, etc.) sont des hash UUID de 32 caracteres, pas des entiers sequentiels.
- La table geolocation contient plusieurs entrees par code postal (1M de lignes pour 19K zips uniques).
- Les paiements peuvent etre multiples par commande (credit + voucher par exemple), d'ou les 103 886 lignes pour 99 440 commandes.
- Les noms de categories sont en portugais dans le fichier produits ; une table de traduction separee fournit les equivalents anglais.
- 775 commandes dans olist_orders n'ont aucun article associe dans olist_order_items (statuts : unavailable, canceled, created).

---

## 3. Schema du Data Warehouse (modele en etoile)

Le Data Warehouse adopte un modele en etoile classique avec des cles de substitution (surrogate keys) entiers auto-incrementes, des contraintes d'integrite referentielle et des contraintes CHECK.

### Schema global CSV vs Data Warehouse

![Schema CSV vs Data Warehouse](schema_csv_vs_dw.png)

### Tables du Data Warehouse

| Table | Lignes | Col. | Cle primaire | Cles etrangeres | Description |
|---|---|---|---|---|---|
| **dim_geolocation** | 19 015 | 6 | geo_key (AUTO) | Aucune | 1 entree par zip_code_prefix (deduplication) |
| **dim_dates** | 715 | 9 | date_key (AAAAMMJJ) | Aucune | Dimension temporelle generee (2016-2018) |
| **dim_customers** | 99 441 | 6 | customer_key (AUTO) | geo_key -> dim_geolocation | Clients avec lien geolocalisation |
| **dim_products** | 32 951 | 9 | product_key (AUTO) | Aucune | Produits avec categorie traduite EN |
| **dim_sellers** | 3 095 | 5 | seller_key (AUTO) | geo_key -> dim_geolocation | Vendeurs avec lien geolocalisation |
| **fact_orders** | 112 650 | 18 | fact_key (AUTO) | 6 FKs vers dims | Table de faits (grain = article) |

### Conception du modele

- **Grain de la table de faits :** un article par commande (order_id + order_item_id). C'est le grain le plus fin disponible, permettant l'analyse par produit, vendeur et commande.
- **Surrogate keys :** chaque dimension utilise un INTEGER AUTOINCREMENT comme cle primaire, tout en conservant l'identifiant naturel (TEXT UNIQUE) pour la tracabilite.
- **Dimension date :** generee a partir de la plage temporelle des commandes (2016-09-04 au 2018-11-12), decomposee en annee, trimestre, mois, jour, jour de la semaine et indicateur weekend.
- **Geolocalisation partagee :** dim_geolocation est referencee par dim_customers, dim_sellers ET fact_orders (via customer_geo_key et seller_geo_key), permettant des analyses geospatiales.
- **Contraintes :** `CHECK(review_score BETWEEN 1 AND 5 OR review_score IS NULL)`, `CHECK(price >= 0)`, `CHECK(freight_value >= 0)`, `UNIQUE(order_id, order_item_id)`.

### DDL des tables

```sql
CREATE TABLE dim_geolocation (
    geo_key          INTEGER PRIMARY KEY AUTOINCREMENT,
    zip_code_prefix  TEXT    NOT NULL UNIQUE,
    lat              REAL,
    lng              REAL,
    city             TEXT,
    state            TEXT
);

CREATE TABLE dim_dates (
    date_key     INTEGER PRIMARY KEY,   -- AAAAMMJJ
    full_date    DATE    NOT NULL,
    year         INTEGER NOT NULL,
    quarter      INTEGER NOT NULL,
    month        INTEGER NOT NULL,
    day          INTEGER NOT NULL,
    day_of_week  INTEGER NOT NULL,      -- 0=Lundi
    day_name     TEXT    NOT NULL,
    is_weekend   INTEGER NOT NULL       -- 0 ou 1
);

CREATE TABLE dim_customers (
    customer_key       INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id        TEXT    NOT NULL UNIQUE,
    customer_unique_id TEXT,
    geo_key            INTEGER,
    city               TEXT,
    state              TEXT,
    FOREIGN KEY (geo_key) REFERENCES dim_geolocation(geo_key)
);

CREATE TABLE dim_products (
    product_key      INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id       TEXT    NOT NULL UNIQUE,
    category_name_pt TEXT,
    category_name_en TEXT,
    weight_g         REAL,
    length_cm        REAL,
    height_cm        REAL,
    width_cm         REAL,
    photos_qty       INTEGER
);

CREATE TABLE dim_sellers (
    seller_key  INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id   TEXT    NOT NULL UNIQUE,
    geo_key     INTEGER,
    city        TEXT,
    state       TEXT,
    FOREIGN KEY (geo_key) REFERENCES dim_geolocation(geo_key)
);

CREATE TABLE fact_orders (
    fact_key             INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id             TEXT    NOT NULL,
    order_item_id        INTEGER NOT NULL,
    date_key             INTEGER,
    customer_key         INTEGER,
    seller_key           INTEGER,
    product_key          INTEGER,
    customer_geo_key     INTEGER,
    seller_geo_key       INTEGER,
    order_status         TEXT,
    price                REAL,
    freight_value        REAL,
    order_payment_total  REAL,
    payment_type         TEXT,
    review_score         INTEGER,
    delivery_days        REAL,
    estimated_days       REAL,
    delivery_delta_days  REAL,
    UNIQUE(order_id, order_item_id),
    CHECK(review_score BETWEEN 1 AND 5 OR review_score IS NULL),
    CHECK(price >= 0),
    CHECK(freight_value >= 0),
    FOREIGN KEY (date_key)         REFERENCES dim_dates(date_key),
    FOREIGN KEY (customer_key)     REFERENCES dim_customers(customer_key),
    FOREIGN KEY (seller_key)       REFERENCES dim_sellers(seller_key),
    FOREIGN KEY (product_key)      REFERENCES dim_products(product_key),
    FOREIGN KEY (customer_geo_key) REFERENCES dim_geolocation(geo_key),
    FOREIGN KEY (seller_geo_key)   REFERENCES dim_geolocation(geo_key)
);
```

---

## 4. Detail des transformations ETL

Le diagramme suivant illustre les transformations appliquees a chaque table source pour obtenir le modele dimensionnel cible :

![Flux de transformations ETL](flux_transformations_etl.png)

### 4.1 Geolocalisation (1 000 163 -> 19 015 lignes)

1. **Deduplication :** le CSV contient en moyenne 53 entrees par code postal. La transformation ne conserve qu'une seule entree par zip_code_prefix.
2. **Agregation des coordonnees :** les latitudes et longitudes multiples sont agregees par **mediane**. Ecart median constate : 0.02 degre en latitude, 0.018 en longitude (precision d'environ 2 km).
3. **Normalisation des villes :** les noms de villes sont convertis en Title Case (ex: `sao paulo` -> `Sao Paulo`).
4. **Typage :** zip_code_prefix passe de INTEGER a TEXT (pour conserver les zeros initiaux potentiels).

### 4.2 Produits (jointure traduction)

1. **Jointure de traduction :** LEFT JOIN avec product_category_name_translation pour ajouter category_name_en. Les 610 produits sans categorie dans le CSV sont remplaces par `unknown` (32 951 produits avec category_name_en renseignee).
2. **Renommage des colonnes :** product_weight_g -> weight_g, product_length_cm -> length_cm, etc.
3. **Suppression de colonnes :** product_name_lenght et product_description_lenght ne sont pas conservees dans la dimension (jugees non analytiques).

### 4.3 Clients et Vendeurs

1. **Liaison geographique :** jointure sur zip_code_prefix pour obtenir le geo_key correspondant. 278 clients et 7 vendeurs n'ont pas de correspondance (codes postaux absents de dim_geolocation).
2. **Normalisation des villes :** passage en Title Case. Les villes dans dim_customers proviennent de `customers` (normalisees), avec un `geo_key` resolu via `dim_geolocation`.
3. **Cles de substitution :** remplacement des UUID textuels par des INTEGER AUTOINCREMENT pour les performances de jointure.

### 4.4 Dimension temporelle (generee)

1. **Generation :** creation de 715 dates couvrant du 2016-09-04 au 2018-11-12, englobant toute la plage des commandes CSV (2016-09-04 au 2018-10-17) avec une marge.
2. **Format de la cle :** date_key au format AAAAMMJJ (ex: 20170315 pour le 15 mars 2017), permettant des tris et filtres naturels.
3. **Attributs derives :** year, quarter, month, day, day_of_week (0=Lundi), day_name, is_weekend.

### 4.5 Table de faits (fusion de 4 sources)

1. **Jointure order_items <-> orders :** grain = 1 ligne par article. Les 775 commandes sans articles sont exclues de fact_orders.
2. **Agregation des paiements :** les lignes multiples de olist_order_payments sont agregees (SUM) en order_payment_total et le type de paiement principal est conserve.
3. **Integration des reviews :** jointure LEFT sur order_id pour recuperer le review_score. 942 faits n'ont pas de review (commandes non livrees).
4. **Calcul des metriques de livraison :**
   - `delivery_days` = (delivered_customer_date - purchase_timestamp) en jours
   - `estimated_days` = (estimated_delivery_date - purchase_timestamp) en jours
   - `delivery_delta_days` = delivery_days - estimated_days
5. **Resolution des cles :** remplacement de tous les identifiants textuels par leurs surrogate keys via lookup dans les dimensions.

---

## 5. Analyse de concordance

La comparaison systematique entre les donnees CSV sources et la base de donnees Data Warehouse permet de valider l'integrite des transformations.

![Graphiques de concordance](concordance_donnees.png)

### Tableau de concordance detaille

| Entite | CSV | DB | Match | Observations |
|---|---|---|---|---|
| **Customers** | 99 441 | 99 441 | **100%** | Tous les IDs concordent. Villes normalisees (Title Case) |
| **Products** | 32 951 | 32 951 | **100%** | IDs identiques. Traduction EN ajoutee via jointure |
| **Sellers** | 3 095 | 3 095 | **100%** | IDs identiques. 7 geo_key NULL (zips absents de geolocation) |
| **Geolocation** | 1 000 163 | 19 015 | N/A | Deduplication par zip. Lat/Lng = mediane. Ecart median <0.02 degre |
| **Order Items / Fact** | 112 650 | 112 650 | **100%** | Nombre identique. Grain = article par commande |
| **Prix (SUM)** | 13 591 643.70 R$ | 13 591 643.70 R$ | **100%** | Somme totale des prix strictement identique |
| **Freight (SUM)** | 2 251 909.54 R$ | 2 251 909.54 R$ | **100%** | Somme totale du fret strictement identique |
| **Paiements** | 103 886 lignes | Agrege par order | **100%** | 100% des totaux par commande concordent |
| **Review scores** | 99 224 | Dans fact_orders | **99.9%** | 104 ecarts (0.1%) : ordres avec reviews multiples |
| **Dates** | Timestamps | 715 dates | **100%** | Dimension generee couvrant toute la plage CSV |

### Verdict global

La concordance est excellente : les volumes, sommes financieres et identifiants sont conserves a 100%. Le seul ecart mineur (0.1% sur les review scores) s'explique par le traitement des commandes ayant plusieurs reviews, ou seul le plus recent est retenu.

---

## 6. Anomalies et points d'attention

### 6.1 Commandes sans articles (775 ordres)

775 commandes presentes dans olist_orders n'ont aucune correspondance dans olist_order_items :

| Statut | Nombre |
|---|---|
| unavailable | 603 |
| canceled | 164 |
| created | 5 |
| invoiced | 2 |
| shipped | 1 |

Ces commandes sont exclues de fact_orders car la table de faits est basee sur le grain article. C'est un choix de conception coherent : une commande sans article ne peut pas etre analysee au niveau produit/vendeur.

### 6.2 Codes postaux non resolus

278 clients (0.28%) et 7 vendeurs (0.23%) ont un code postal absent de dim_geolocation, entrainant des geo_key NULL. Ces codes postaux existaient probablement dans les donnees reelles mais ne figuraient pas dans le fichier olist_geolocation_dataset.csv.

### 6.3 Valeurs NULL dans la table de faits

| Colonne | NULLs | Explication |
|---|---|---|
| delivery_days / delivery_delta_days | 2 454 | Commandes non livrees (shipped, canceled, etc.) |
| review_score | 942 | Commandes sans avis client |
| order_payment_total | 3 | Marginal, potentielle anomalie source |
| customer_geo_key | 302 | Codes postaux clients absents de dim_geolocation |
| seller_geo_key | 253 | Codes postaux vendeurs absents de dim_geolocation |

### 6.4 Precision de la geolocalisation

La mediane des coordonnees GPS par code postal introduit une imprecision d'environ 0.02 degre (environ 2 km). C'est acceptable pour des analyses au niveau ville/region mais insuffisant pour du geocodage precis.

### 6.5 Ecart sur les statuts de commandes

La distribution des statuts differe entre CSV et DB :

| Statut | CSV (total) | DB fact_orders | Ecart | Explication |
|---|---|---|---|---|
| delivered | 96 478 | 96 478 | 0 | - |
| canceled | 625 | 461 | -164 | 164 sans articles |
| shipped | 1 107 | 1 106 | -1 | 1 sans articles |
| unavailable | 609 | 6 | -603 | 603 sans articles |
| invoiced | 314 | 312 | -2 | 2 sans articles |
| processing | 301 | 301 | 0 | - |
| created | 5 | 0 | -5 | 5 sans articles |
| approved | 2 | 2 | 0 | - |

Les ecarts correspondent exactement aux 775 commandes sans articles. Ce n'est pas une anomalie mais la consequence logique de la granularite choisie.

---

## 7. Analyse des ecarts de paiement

### Contexte

Dans le Data Warehouse, chaque commande possede deux montants : un montant **facture** (`SUM(price) + SUM(freight_value)` dans fact_orders) et un montant **paye** (`order_payment_total`, provenant de `SUM(payment_value)` agrege depuis le CSV brut). En theorie, ces deux montants devraient etre identiques. L'investigation revele 387 commandes (0.39%) presentant un ecart superieur a 0.01 R$.

### Statistiques globales

| Indicateur | Valeur |
|---|---|
| Commandes avec ecart | 387 / 98 666 (0.39%) |
| Delta moyen | +7.42 R$ |
| Delta min | -51.62 R$ |
| Delta max | +182.81 R$ |
| Somme nette des ecarts | +2 870.82 R$ |
| Commandes surpayees | 294 (somme : +3 070.44 R$) |
| Commandes sous-payees | 93 (somme : -199.62 R$) |

### Repartition par type de paiement

| Type paiement | Commandes | Avec ecart | % ecart | Delta moyen |
|---|---|---|---|---|
| **credit_card** | 75 623 | 349 | 0.46% | +8.37 R$ |
| **boleto** | 19 614 | 26 | 0.13% | ~0.00 R$ |
| **debit_card** | 1 520 | 10 | 0.66% | -5.20 R$ |
| **voucher** | 1 908 | 2 | 0.10% | -0.01 R$ |

### Distribution des ecarts par tranche

| Tranche (R$) | Commandes |
|---|---|
| < -10 | 7 |
| -10 a -1 | 10 |
| -1 a -0.01 | 76 |
| **exact (+-0.01)** | **98 278** |
| 0.01 a 1 | 62 |
| 1 a 10 | 141 |
| 10 a 50 | 84 |
| > 50 | 8 |

### Causes identifiees

**1. Interets de financement (juros) — 264 commandes (68% des ecarts)**

Au Bresil, les paiements par carte de credit en plusieurs fois (*parcelamento*) incluent des interets dans `payment_value`. Le champ `payment_installments` du CSV brut (non charge dans le DW) confirme cette hypothese : les commandes avec ecart ont en moyenne 5.24 parcelas contre 2.85 pour celles sans ecart. Les 264 commandes credit_card surpayees avec plus d'une parcela representent a elles seules +3 063.84 R$ d'ecart, soit l'essentiel de l'impact net.

**2. Arrondis boleto — 26 commandes**

Ecarts negligeables (±0.04 R$ maximum), lies aux arrondis de centimes lors de la generation du boleto bancaire. Somme nette : +0.08 R$.

**3. Sous-paiements debit_card — 9 commandes**

Le client paye MOINS que le facture (-1.60 a -16.50 R$). Toutes ces commandes sont en statut "delivered" avec 1 a 2 articles, ce qui elimine l'hypothese d'annulation partielle. Cause probable : cashback ou remise appliquee par le processeur de paiement.

**4. Paiements mixtes — 4 commandes**

L'ETL agrege `SUM(payment_value)` tous types confondus et ne garde que le `payment_type` dominant. Quand une commande combine voucher + carte, le delta peut provenir de l'interaction entre la remise voucher et les interets carte.

### Synthese des causes

| Cause | Nb commandes | Delta moyen | Impact total |
|---|---|---|---|
| **Interets financement (juros)** | 264 | +11.61 R$ | +3 063.84 R$ |
| Sous-paye autre | 74 | -1.99 R$ | -147.47 R$ |
| Arrondi boleto | 26 | ~0 R$ | +0.08 R$ |
| Sous-paye debit (cashback?) | 9 | -5.77 R$ | -51.97 R$ |
| Surpaye 1x (cause inconnue) | 9 | +0.25 R$ | +2.24 R$ |
| Paiement mixte | 4 | +1.02 R$ | +4.09 R$ |
| Autre | 1 | +0.01 R$ | +0.01 R$ |
| **TOTAL** | **387** | **+7.42 R$** | **+2 870.82 R$** |

---

## 8. Taux d'interet implicite du parcelamento

L'axe le plus riche revele par l'analyse des ecarts concerne les interets de financement. En croisant les donnees du CSV brut (`payment_installments`) avec les montants factures du DW, on peut calculer le taux d'interet implicite applique aux paiements en plusieurs fois.

### Methodologie

Pour chaque commande surpayee par credit_card avec plus d'une parcela :

- **Taux total** = `(paye - facture) / facture`
- **Taux mensuel compose** = `(paye / facture)^(1/n) - 1` ou `n` = nombre de parcelas
- **Taux annuel equivalent** = `(1 + taux_mensuel)^12 - 1`

### Resultats par nombre de parcelas

| Parcelas | Nb commandes | Delta moyen (R$) | Taux total moyen | Taux median |
|---|---|---|---|---|
| 2 | 16 | +0.87 | 2.58% | 3.45% |
| 3 | 39 | +2.75 | 5.79% | 4.62% |
| 4 | 39 | +3.53 | 6.99% | 5.79% |
| 5 | 29 | +6.76 | 9.56% | 6.99% |
| 6 | 32 | +8.86 | 8.89% | 8.17% |
| 7 | 18 | +10.05 | 12.11% | 13.03% |
| 8 | 18 | +13.35 | 11.60% | 11.81% |
| 10 | 42 | +25.07 | 11.29% | 13.02% |
| 12 | 14 | +24.83 | 15.50% | 15.50% |
| 20-24 | 3 | +78.20 | 26.04% | 25.21% |

La tendance est claire : le taux d'interet total augmente avec le nombre de parcelas, de ~3% pour 2 parcelas a ~25% pour 20+ parcelas.

### Taux mensuel implicite

| Parcelas | Taux mensuel moyen | Taux mensuel median |
|---|---|---|
| 2 | 1.277% | 1.709% |
| 3 | 1.876% | 1.518% |
| 4 | 1.687% | 1.418% |
| 5 | 1.837% | 1.360% |
| 6 | 1.419% | 1.318% |
| 8 | 1.357% | 1.404% |
| 10 | 1.058% | 1.232% |
| 12 | 1.208% | 1.208% |

**Taux mensuel median global : 1.361%, soit un taux annuel compose equivalent de 17.6%.**

A titre de comparaison, le taux SELIC (taux directeur bresilien) oscillait entre 6.5% et 14.25% sur la periode 2017-2018. Le taux implicite de 17.6% est coherent avec les pratiques du marche bresilien du credit a la consommation, ou les taux de parcelamento sont generalement superieurs au taux directeur.

### Interpretation et limites

L'analyse ne porte que sur les 264 commandes ou l'ecart est mesurable (surpaye > 0.01 R$). En realite, une large partie des paiements en plusieurs fois au Bresil sont "sem juros" (sans interets) — les interets sont absorbes par le vendeur ou la plateforme. Cela explique pourquoi seules 2% des commandes multi-parcelas presentent un ecart visible : les 98% restantes beneficient probablement du parcelamento sans interets, une pratique commerciale tres courante au Bresil.

### Recommandation pour le DW

L'ajout de `payment_installments` dans fact_orders (ou dans une dimension dediee) permettrait de segmenter les clients par comportement de financement et d'analyser plus finement l'impact des interets sur le panier moyen. Requete d'investigation suggeree :

```sql
-- Commandes avec ecart et leurs installments (necessite CSV brut)
SELECT
    f.order_id,
    ROUND(SUM(f.price) + SUM(f.freight_value), 2) AS invoiced,
    ROUND(MAX(f.order_payment_total), 2)           AS paid,
    ROUND(MAX(f.order_payment_total) - (SUM(f.price) + SUM(f.freight_value)), 2) AS delta
FROM fact_orders f
GROUP BY f.order_id
HAVING ABS(delta) > 0.01
ORDER BY ABS(delta) DESC
LIMIT 20;
```

---

## 9. Vues analytiques

Le Data Warehouse inclut 3 vues precalculees qui facilitent les analyses recurrentes.

### 7.1 v_monthly_sales

Agregation mensuelle du chiffre d'affaires pour les commandes livrees.

```sql
CREATE VIEW v_monthly_sales AS
SELECT
    d.year,
    d.month,
    d.year || '-' || PRINTF('%02d', d.month) AS month_label,
    ROUND(SUM(f.price), 2)                   AS monthly_revenue,
    COUNT(DISTINCT f.order_id)                AS monthly_orders,
    ROUND(SUM(f.price) * 1.0 / NULLIF(COUNT(DISTINCT f.order_id), 0), 2) AS avg_basket
FROM fact_orders f
JOIN dim_dates d ON f.date_key = d.date_key
WHERE f.order_status = 'delivered'
GROUP BY d.year, d.month;
```

**Usage :** suivi du CA mensuel, nombre de commandes et panier moyen.

### 7.2 v_customer_cohorts

Analyse de cohorte par client unique : identifie le premier mois d'achat, le nombre total de commandes et le montant total depense.

```sql
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
```

**Usage :** analyse de retention, valeur vie client (LTV), segmentation.

### 7.3 v_orders_enriched

Vue denormalisee joignant fact_orders avec toutes les dimensions, fournissant directement les libelles sans jointures manuelles.

```sql
CREATE VIEW v_orders_enriched AS
SELECT
    f.order_id, f.order_item_id, f.order_status,
    d.full_date AS order_date, d.year, d.month, d.day_name, d.is_weekend,
    c.customer_unique_id, c.city AS customer_city, c.state AS customer_state,
    COALESCE(p.category_name_en, p.category_name_pt, 'Unknown') AS product_category,
    f.price, f.freight_value, f.review_score,
    f.delivery_days, f.delivery_delta_days
FROM fact_orders f
LEFT JOIN dim_dates     d ON f.date_key     = d.date_key
LEFT JOIN dim_customers c ON f.customer_key = c.customer_key
LEFT JOIN dim_products  p ON f.product_key  = p.product_key;
```

**Usage :** requetes ad-hoc sans jointures, exploration des donnees, export pour visualisation.

---

## 10. Conclusion

Le processus de transformation des 9 fichiers CSV Olist vers le Data Warehouse en etoile est globalement tres bien realise :

- **Integrite des donnees preservee :** 100% de concordance sur les volumes, identifiants et montants financiers. Aucune perte de donnee significative.
- **Modele dimensionnel coherent :** le schema en etoile avec surrogate keys, contraintes FK et CHECK offre une base solide pour l'analyse.
- **Enrichissement pertinent :** traduction des categories, calcul des metriques de livraison, dimension temporelle, et geolocalisation partagee.
- **Choix de conception documentes :** l'exclusion des commandes sans articles et l'agregation des paiements sont des decisions justifiees et tracables.
- **Vues analytiques utiles :** les 3 vues precalculees couvrent les cas d'usage frequents (suivi CA mensuel, cohortes clients, analyse enrichie).

Les anomalies identifiees (278 geo_key NULL, 0.1% d'ecart sur les reviews, precision geographique limitee a ~2 km) sont mineures et ne compromettent pas la fiabilite globale du Data Warehouse.

L'analyse approfondie des ecarts de paiement (section 7-8) revele un phenomene metier important : 264 commandes presentent des interets de financement (*juros*) lies au parcelamento bresilien, avec un taux mensuel median implicite de 1.36% (17.6% annuel). Ce constat ouvre des pistes d'enrichissement du DW, notamment l'ajout de `payment_installments` pour segmenter les comportements de financement.
