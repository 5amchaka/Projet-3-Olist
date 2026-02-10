# Analyse exploratoire des donnees brutes

Synthese des observations issues du notebook [`notebooks/exploration_csv.ipynb`](../notebooks/exploration_csv.ipynb). Ce document fournit les **constats empiriques** qui justifient les choix de modelisation decrits dans [`csv_to_star_schema.md`](csv_to_star_schema.md).

---

## Vue d'ensemble des 9 CSV

| Dataset | Lignes | Colonnes | Doublons exacts | Memoire |
|---------|-------:|:--------:|:---------------:|--------:|
| customers | 99 441 | 5 | 0 | 8.4 MB |
| geolocation | 1 000 163 | 5 | 261 831 | 65.5 MB |
| orders | 99 441 | 8 | 0 | 8.4 MB |
| order_items | 112 650 | 7 | 0 | 7.7 MB |
| order_payments | 103 886 | 5 | 0 | 4.9 MB |
| order_reviews | 99 224 | 7 | 0 | 14.7 MB |
| products | 32 951 | 9 | 0 | 3.0 MB |
| sellers | 3 095 | 4 | 0 | 0.3 MB |
| category_translation | 71 | 2 | 0 | 0.01 MB |

**Constat** : `geolocation` represente 77% du volume total pour seulement 19k codes postaux utiles — c'est la transformation la plus radicale du pipeline (ratio 53:1). Aucun doublon exact sur les 8 autres datasets.

---

## Integrite referentielle

**Zero orphelin** sur toutes les FK verifiees :

| FK enfant → parent | Orphelins |
|---------------------|:---------:|
| orders.customer_id → customers | 0 |
| order_items.order_id → orders | 0 |
| order_items.product_id → products | 0 |
| order_items.seller_id → sellers | 0 |
| order_payments.order_id → orders | 0 |
| order_reviews.order_id → orders | 0 |

C'est remarquable pour un dataset reel. Les jointures sont fiables a 100%, le pipeline n'a pas a gerer de FK manquantes.

---

## Cardinalites observees

| Relation | Moy. enfants/parent | Max | Distribution |
|----------|:-------------------:|:---:|-------------|
| order_items / order | 1.14 | 21 | 90.1% mono-item |
| order_payments / order | 1.04 | 29 | 97.0% mono-paiement |
| order_reviews / order | 1.01 | 3 | 99.45% mono-review, 547 exceptions |

Le dataset est **massivement mono-transactionnel**. Les cas multi existent et doivent etre geres, mais restent marginaux. Le grain `order_item` pour la fact table ne gonfle les donnees que de 14% par rapport au grain `order` (112k vs 99k) tout en preservant le detail produit/vendeur.

---

## Observations par dataset

### geolocation — le defi principal

- **1 000 163 lignes** pour **19 015 zip_code_prefix** uniques (ratio 53:1).
- Coordonnees par zip : ecart-type median ~0.004° (~400m), mais des outliers massifs (max 42° — erreurs GPS evidentes).
- **8 556 zips (45%)** ont plusieurs variantes de nom de ville (casse, accents, abreviations : "Sao Paulo" / "SAO PAULO" / "sao paulo").
- Seulement **8 zips** ont des etats differents (frontiere entre etats).

**Choix valide** : mediane pour les coordonnees (robuste aux outliers GPS), mode pour ville/etat (prend la variante majoritaire). Voir [`csv_to_star_schema.md` §2](csv_to_star_schema.md#2-dim_geolocation--depuis-geolocation).

### customers — quasi pas de recurrence

- 99 441 `customer_id` pour 96 096 `customer_unique_id` → seulement **3.1% de clients recurrents** (max 17 commandes).
- C'est un marketplace one-shot : `customer_id` (unique par commande) est le bon choix de cle.
- `customer_unique_id` est conserve pour d'eventuelles analyses de fidelite, mais ne concerne que 2 997 clients.
- Couverture zip → geolocation : ~100%.

### sellers — grain propre

- **3 095 lignes, 3 095 seller_id uniques** : unicite verifiee, pas de nettoyage necessaire.
- Couverture zip → geolocation : ~100%.
- Forte concentration geographique : Sao Paulo domine largement.

### orders — temporalite coherente

- **97% des commandes sont delivered**, 1.1% shipped, 0.6% canceled, le reste est marginal.
- Plage temporelle : **sept. 2016 → oct. 2018**, avec une croissance visible mois par mois.
- Les timestamps NULL suivent la logique metier :
  - `delivered_customer_date` NULL → commande non livree (shipped, canceled, etc.)
  - `order_approved_at` NULL → 141 canceled + 14 delivered (cas limites)
  - 8 commandes "delivered" sans date de livraison — anomalie marginale negligeable.

Les metriques derivees (`delivery_days`, `estimated_days`, `delivery_delta_days`) seront NULL quand les timestamps source le sont.

### order_items — le bon grain pour la fact

- **90.1% mono-item**, moyenne 1.14 item/commande, max 21.
- Prix : 0.85 → 6 735 BRL (distribution long-tail, valeurs legitimes du marketplace).
- Freight : 0 → 409.68 BRL.
- Zero orphelin vers products et sellers.

### order_payments — les multi-paiements justifient l'agregation

- **97% mono-paiement**, mais 2 246 commandes (2.3%) mixent plusieurs types.
- Carte de credit domine largement, suivi de boleto.
- 9 paiements a valeur 0 (6 vouchers, 3 "not_defined") — cas marginal, pas de traitement special necessaire.

**Choix valide** : `sum(payment_value)` + `mode(payment_type)` par commande avant jointure a la fact. Voir [`csv_to_star_schema.md` §6](csv_to_star_schema.md#6-fact_orders--fusion-de-order_items--orders--order_payments--order_reviews).

### order_reviews — textes vides, scores exploitables

- **547 commandes** avec >1 review (0.55%), max 3 reviews par commande.
- **58.7%** des commentaires vides, **88.3%** des titres vides.
- Distribution des scores bimodale : polarisee entre 1 et 5.

**Choix valide** : review la plus recente par commande, seul `review_score` retenu dans la fact. Les textes sont trop lacunaires et inadaptes a un schema analytique. Voir [`csv_to_star_schema.md` §6](csv_to_star_schema.md#6-fact_orders--fusion-de-order_items--orders--order_payments--order_reviews).

### products + category_translation — fusion necessaire

- **610 produits (1.85%)** sans categorie, sans name/description length, sans photos_qty — bloc homogene de NULL.
- 73 categories PT dans products, 71 dans translation → **2 non traduites** : `pc_gamer` et `portateis_cozinha_e_preparadores_de_alimentos`.
- Attributs physiques (poids, dimensions) presents avec outliers visibles mais seulement 2 NULL.
- `product_name_lenght` (moy 48 car.) et `product_description_lenght` (moy 771 car.) : metadonnees derivees sans valeur analytique.

**Choix valide** : fusion avec translation (denormalisation), imputation mediane pour attributs physiques, fallback "unknown" pour categories manquantes, exclusion des colonnes *_lenght. Voir [`csv_to_star_schema.md` §5](csv_to_star_schema.md#5-dim_products--fusion-de-products--category_translation).

---

## Synthese

Le dataset Olist est **remarquablement propre** pour des donnees reelles : zero orphelin, logique metier coherente dans les NULL, pas de corruption visible. Les deux vrais defis de modelisation sont :

1. **La deduplication geolocation** (ratio 53:1, variabilite des noms sur 45% des zips, outliers GPS)
2. **La gestion des multi-lignes** (paiements multiples sur 3% des commandes, multi-reviews sur 0.55%)

Les choix du star schema — mediane, mode, agregation sum, review la plus recente — sont tous empiriquement justifies par les distributions observees dans cette analyse.
