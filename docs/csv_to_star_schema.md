# De 9 CSV a 6 tables : choix de modelisation

## Vue d'ensemble

Le dataset Olist contient 9 fichiers CSV organises en schema relationnel classique (OLTP). Pour l'analyse, on les reorganise en **star schema** (OLAP) avec 5 dimensions et 1 table de faits. Ce document explique et justifie chaque transformation.

```
9 CSV bruts                              6 tables star schema
─────────────                            ────────────────────
customers ─────────────────────────────> dim_customers
sellers ───────────────────────────────> dim_sellers
geolocation ───────────────────────────> dim_geolocation
products ──────┐
               ├───────────────────────> dim_products
category_translation ──┘
(timestamps des orders) ───────────────> dim_dates
orders ────────────┐
order_items ───────┤
                   ├───────────────────> fact_orders
order_payments ────┤
order_reviews ─────┘
```

---

## 1. dim_dates — table generee (aucun CSV source)

**Choix** : Creer une dimension temporelle a partir des timestamps existants dans `orders`.

**Pourquoi** :
- Aucun CSV ne fournit de calendrier. Les dates sont dispersees dans 5 colonnes timestamp de `orders` (achat, approbation, expedition, livraison, estimation).
- Une dimension date dediee permet de filtrer et grouper facilement par annee, trimestre, mois, jour de la semaine, weekend/semaine — sans recalculer ces attributs a chaque requete.
- C'est une pratique standard en modelisation dimensionnelle (Kimball) : la dimension date est presque toujours generee.

**Ce qu'elle contient** : `date_key` (YYYYMMDD), `full_date` (DATE), `year`, `quarter`, `month`, `day`, `day_of_week`, `day_name`, `is_weekend`.

---

## 2. dim_geolocation — depuis `geolocation`

**Choix** : Deduplication par `zip_code_prefix` avec coordonnees medianes (~1M lignes → ~19k).

Dans le contexte bresilien, c'est les 5 premiers chiffres du CEP (Código de Endereçamento Postal), l'equivalent du code postal.

  Un CEP complet au Bresil fait 8 chiffres, au format XXXXX-XXX :
  - Les 5 premiers chiffres (le prefix) identifient la zone geographique (ville ou quartier d'une grande ville)
  - Les 3 derniers chiffres precisent la rue, le bloc, ou le batiment specifique

  Par exemple pour Sao Paulo :
  - 01310-100 → Avenida Paulista
  - 01310-200 → une autre section de la meme avenue
  - Le prefix 01310 couvre le meme quartier

  Dans le dataset Olist, seul le prefix a 5 chiffres est fourni (pas le CEP complet), ce qui donne une precision au niveau du quartier/ville - suffisant pour des analyses geographiques macro (revenus par region, delais de livraison par zone, etc.) sans exposer l'adresse exacte des clients.

  C'est pour ca que l'agregation par zip_code_prefix fait sens : ca correspond deja a une zone geographique cohesive, et les coordonnees medianes donnent un bon centroide representatif de cette zone.

**Pourquoi** :
- Le CSV brut contient **plusieurs lignes par code postal** (parfois des dizaines) avec des coordonnees legerement differentes. Ce n'est pas exploitable tel quel comme dimension.
- On aggrege en prenant la **mediane** des latitudes/longitudes par zip_code_prefix. La mediane est plus robuste que la moyenne face aux valeurs aberrantes (un point GPS mal place ne fausse pas le resultat).
- On garde `city` et `state` par **mode** (valeur la plus frequente) pour chaque zip, ce qui est plus robuste que `first()` face a d'eventuelles lignes mal orthographiees.
- Le resultat : **1 ligne = 1 code postal**, ce qui en fait une vraie dimension utilisable comme cle de reference pour clients et vendeurs.

---

## 3. dim_customers — depuis `customers`

**Choix** : Reprise directe avec ajout d'une cle surrogate `customer_key` et d'un lien `geo_key` vers `dim_geolocation`.

**Pourquoi** :
- Le CSV `customers` est deja au bon grain : 1 ligne par `customer_id`.
- On ajoute `geo_key` (lookup sur `zip_code_prefix`) pour pouvoir joindre la localisation du client sans stocker les coordonnees en double.
- On conserve `customer_unique_id` (qui regroupe les achats d'un meme client sous differents `customer_id`) pour des analyses de fidelite.
- On garde `city` et `state` directement dans la dimension (denormalisation). Ca evite de joindre `dim_geolocation` pour un simple filtre par ville ou etat — un cas d'usage tres frequent en analyse. Les coordonnees GPS restent dans `dim_geolocation` pour les analyses spatiales.
- La normalisation (title case villes, upper case etats, zero-padding zip) garantit la coherence avec `dim_geolocation`.

---

## 4. dim_sellers — depuis `sellers`

**Choix** : Meme logique que `dim_customers`.

**Pourquoi** :
- Le CSV est deja au bon grain : 1 ligne par `seller_id`.
- On ajoute `geo_key` vers `dim_geolocation` pour la localisation.
- Comme pour `dim_customers`, on garde `city` et `state` directement dans la dimension pour les memes raisons (filtre rapide sans jointure supplementaire).
- Meme normalisation que les clients pour assurer la coherence des jointures geographiques.

---

## 5. dim_products — fusion de `products` + `category_translation`

**Choix** : Merger les 2 CSV pour avoir les categories en portugais **et** en anglais dans une seule dimension.

**Pourquoi** :
- `products` contient les noms de categories en portugais (`product_category_name`).
- `category_translation` fournit la traduction anglaise (71 lignes, une par categorie).
- Garder `category_translation` comme table separee obligerait a faire une jointure supplementaire a chaque requete d'analyse par categorie. En fusionnant en amont, on a les deux langues directement accessibles.
- C'est une **denormalisation volontaire** typique du star schema : on privilegie la simplicite des requetes analytiques plutot que la normalisation stricte.
- Les categories manquantes sont remplies par "unknown" plutot que laissees null, ce qui evite de perdre des lignes dans les GROUP BY.

**Attributs physiques conserves** : `weight_g`, `length_cm`, `height_cm`, `width_cm`, `photos_qty`. Ces colonnes permettent des analyses logistiques (correlation poids/dimensions avec les frais de livraison, impact du nombre de photos sur les ventes). Les valeurs manquantes sont imputees par la **mediane** de chaque colonne, ce qui est plus robuste que la moyenne face aux outliers (meme logique que pour les coordonnees GPS dans `dim_geolocation`).

**Colonnes exclues** : `product_name_lenght` et `product_description_lenght` ne sont pas repris dans `dim_products`. Ce sont des metadonnees derivees (longueur en caracteres du nom/description) qui n'apportent pas de valeur analytique directe.

---

## 6. fact_orders — fusion de `order_items` + `orders` + `order_payments` + `order_reviews`

C'est la transformation la plus importante. 4 CSV sont fusionnes en une seule table de faits.

### Choix du grain : l'article commande (order item)

**Pourquoi order_item et pas order ?**
- Une commande peut contenir **plusieurs articles**, chacun d'un vendeur et produit different, avec un prix et frais de livraison propres.
- Si on prend le grain `order`, on perd le detail par produit/vendeur. On ne pourrait plus analyser "quel produit genere le plus de revenue" ou "quel vendeur livre le plus vite".
- Le grain `order_item` est le plus fin disponible, il permet toutes les agregations (par commande, par client, par produit, par vendeur).

### Fusion de `orders`

**Ce qu'on recupere** : `order_status`, les timestamps (pour calculer les metriques de livraison), `customer_id` (pour le lookup `customer_key`).

**Jointure** : `order_items.order_id = orders.order_id` (N:1 — plusieurs items par commande).

### Fusion de `order_payments`

**Probleme** : une commande peut avoir **plusieurs paiements** (ex: carte + voucher). On ne peut pas joindre directement au grain order_item sans multiplier les lignes.

**Solution** : agreger les paiements **par commande** avant la jointure :
- `order_payment_total` = somme de tous les paiements de la commande
- `payment_type` = type dominant (mode statistique — le type de paiement le plus frequent)

Chaque article de la meme commande recoit donc les memes valeurs de paiement. C'est un compromis : on perd le detail par methode de paiement, mais on evite l'explosion des lignes.

> **Attention** : `order_payment_total` est une mesure semi-additive. Elle est au grain commande, pas article. Pour obtenir le total correct, il faut d'abord dedupliquer par `order_id` (ex: `SELECT DISTINCT order_id, order_payment_total`) avant de sommer.

### Fusion de `order_reviews`

**Probleme** : une commande peut avoir **plusieurs reviews** (547 commandes concernees dans le dataset). Les reviews sont au grain commande, pas par article.

**Solution** : on garde le review le plus recent (`review_creation_date` le plus eleve) par `order_id`, puis chaque article de la commande herite du meme `review_score`. C'est coherent car le client note la commande globalement, pas chaque article individuellement.

### Metriques derivees

A partir des timestamps de `orders`, on calcule 3 metriques temporelles :
- `delivery_days` : jours entre achat et livraison reelle
- `estimated_days` : jours entre achat et date estimee
- `delivery_delta_days` : ecart entre les deux (positif = retard, negatif = avance)

Ces metriques sont pre-calculees dans la table de faits pour eviter de recalculer les differences de dates a chaque requete.

### Colonnes finales de fact_orders

| Colonne | Type | Source |
|---------|------|--------|
| `fact_key` | PK surrogate | Generee (auto-increment) |
| `order_id` | Identifiant | `orders.order_id` |
| `order_item_id` | Identifiant | `order_items.order_item_id` |
| `date_key` | FK → dim_dates | Derivee de `orders.order_purchase_timestamp` (format YYYYMMDD) |
| `customer_key` | FK → dim_customers | Lookup via `orders.customer_id` |
| `seller_key` | FK → dim_sellers | Lookup via `order_items.seller_id` |
| `product_key` | FK → dim_products | Lookup via `order_items.product_id` |
| `customer_geo_key` | FK → dim_geolocation | Lookup via le zip du client |
| `seller_geo_key` | FK → dim_geolocation | Lookup via le zip du vendeur |
| `order_status` | Attribut | `orders.order_status` |
| `price` | Metrique | `order_items.price` |
| `freight_value` | Metrique | `order_items.freight_value` |
| `order_payment_total` | Metrique (semi-additive) | Somme par `order_id` depuis `order_payments` |
| `payment_type` | Attribut | Mode statistique par `order_id` depuis `order_payments` |
| `review_score` | Metrique | Review le plus recent par `order_id` depuis `order_reviews` |
| `delivery_days` | Metrique derivee | Calculee depuis les timestamps |
| `estimated_days` | Metrique derivee | Calculee depuis les timestamps |
| `delivery_delta_days` | Metrique derivee | Calculee depuis les timestamps |

---

## Ce qui n'est PAS dans le star schema

| CSV | Raison de l'absence |
|-----|---------------------|
| `category_translation` | Fusionne dans `dim_products`, plus besoin d'une table separee |
| `order_payments` (detail) | Agrege dans `fact_orders`, le detail par methode de paiement est perdu |
| `order_reviews` (commentaires) | Seul `review_score` est garde. Les textes (`review_comment_title`, `review_comment_message`) ne sont pas dans la fact car ce sont des donnees non-structurees inutiles pour l'agregation |
| `products.product_name_lenght`, `products.product_description_lenght` | Metadonnees derivees (longueur en caracteres) sans valeur analytique directe — exclus de `dim_products` |

---

## Resume des compromis

| Compromis | Justification |
|-----------|---------------|
| Denormalisation categories dans dim_products | Evite une jointure supplementaire a chaque requete |
| Paiement agrege par commande (pas par item) | Evite la multiplication des lignes, le detail par methode de paiement est rarement necessaire au grain article |
| Review dupliquee sur chaque item de la commande | La note est donnee a la commande, pas a l'article — pas de meilleure option |
| Metriques de livraison pre-calculees | Performance : evite le calcul de differences de dates a chaque requete |
| Geolocation dedupliquee par mediane | Necessite un choix d'agregation, la mediane est robuste aux outliers |
| City/state denormalises dans dim_customers et dim_sellers | Evite une jointure avec dim_geolocation pour les filtres par ville/etat (cas frequent), au prix d'une legere redondance |
