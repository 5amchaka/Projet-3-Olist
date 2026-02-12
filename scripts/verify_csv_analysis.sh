#!/usr/bin/env bash
# ────────────────────────────────────────────────────────────────────────────
# Verification independante de l'analyse Olist via csvkit + SQLite temporaire.
# Reproduit les chiffres cles de docs/Analyse_Transformations_Olist_DW.md
# en utilisant uniquement les 9 CSV bruts (sans pipeline Python ni DW).
# ────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RAW_DIR="$PROJECT_ROOT/data/raw"
VENV_BIN="$PROJECT_ROOT/.venv/bin"

# Ajouter le venv au PATH pour acceder a csvsql, csvstat, etc.
if [[ -d "$VENV_BIN" ]]; then
    export PATH="$VENV_BIN:$PATH"
fi

# ── Couleurs ANSI ──────────────────────────────────────────────────────────
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
BOLD='\033[1m'
NC='\033[0m'

# ── Compteurs ──────────────────────────────────────────────────────────────
PASS=0
FAIL=0
TOTAL=0

# ── DB temporaire ──────────────────────────────────────────────────────────
TEMP_DB=$(mktemp /tmp/olist_verify_XXXXXX.db)

cleanup() {
    rm -f "$TEMP_DB"
    echo -e "\n${CYAN}[CLEANUP] DB temporaire supprimee${NC}"
}
trap cleanup EXIT

# ── Fonctions helper ───────────────────────────────────────────────────────
query_db() {
    sqlite3 "$TEMP_DB" "$1"
}

check_value() {
    local label="$1"
    local expected="$2"
    local actual
    actual="$(echo "$3" | xargs)"  # trim whitespace
    TOTAL=$((TOTAL + 1))
    if [[ "$expected" == "$actual" ]]; then
        echo -e "  ${GREEN}[PASS]${NC} $label : $actual"
        PASS=$((PASS + 1))
    else
        echo -e "  ${RED}[FAIL]${NC} $label : attendu=$expected, obtenu=$actual"
        FAIL=$((FAIL + 1))
    fi
}

info_value() {
    echo -e "  ${YELLOW}[INFO]${NC} $1 : $2"
}

section_header() {
    echo ""
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}${BOLD}  $1${NC}"
    echo -e "${CYAN}${BOLD}══════════════════════════════════════════════════════════════${NC}"
}

subsection() {
    echo ""
    echo -e "${BOLD}── $1 ──${NC}"
}

# ══════════════════════════════════════════════════════════════════════════
#  0. PREREQUIS
# ══════════════════════════════════════════════════════════════════════════
section_header "0. Prerequisites"

if ! command -v sqlite3 &>/dev/null; then
    echo -e "${RED}[ERROR] sqlite3 non disponible${NC}"
    exit 1
fi

if ! command -v csvsql &>/dev/null; then
    echo -e "${YELLOW}csvkit non trouve, installation via uv...${NC}"
    uv pip install csvkit
fi

for cmd in csvsql csvstat csvcut csvgrep; do
    if ! command -v "$cmd" &>/dev/null; then
        echo -e "${RED}[ERROR] $cmd non disponible apres installation${NC}"
        exit 1
    fi
done
echo -e "${GREEN}[OK] Outils disponibles (sqlite3, csvsql, csvstat, csvcut, csvgrep)${NC}"

# ══════════════════════════════════════════════════════════════════════════
#  1. CHARGEMENT DES CSV
# ══════════════════════════════════════════════════════════════════════════
section_header "1. Chargement des CSV dans SQLite temporaire"
echo -e "  ${YELLOW}(geolocation ~1M lignes : peut prendre quelques minutes)${NC}"

CSV_FILES=(
    "product_category_name_translation.csv"
    "olist_sellers_dataset.csv"
    "olist_customers_dataset.csv"
    "olist_products_dataset.csv"
    "olist_orders_dataset.csv"
    "olist_order_items_dataset.csv"
    "olist_order_payments_dataset.csv"
    "olist_order_reviews_dataset.csv"
    "olist_geolocation_dataset.csv"
)

for csv in "${CSV_FILES[@]}"; do
    filepath="$RAW_DIR/$csv"
    if [[ ! -f "$filepath" ]]; then
        echo -e "  ${RED}[ERROR] Fichier manquant : $csv${NC}"
        exit 1
    fi
    echo -ne "  Chargement $csv... "
    START=$(date +%s)
    csvsql --db "sqlite:///$TEMP_DB" --insert --no-inference "$filepath" 2>/dev/null
    END=$(date +%s)
    echo -e "${GREEN}OK${NC} ($((END - START))s)"
done
echo -e "\n${GREEN}[OK] 9 CSV charges dans la DB temporaire${NC}"

# ══════════════════════════════════════════════════════════════════════════
#  2. SCHEMA DES DONNEES SOURCES (doc §2)
# ══════════════════════════════════════════════════════════════════════════
section_header "2. Schema des donnees sources (§2)"

TABLES=(
    olist_customers_dataset
    olist_orders_dataset
    olist_order_items_dataset
    olist_order_payments_dataset
    olist_order_reviews_dataset
    olist_products_dataset
    olist_sellers_dataset
    olist_geolocation_dataset
    product_category_name_translation
)
EXP_ROWS=(99441 99441 112650 103886 99224 32951 3095 1000163 71)
EXP_COLS=(5 8 7 5 7 9 4 5 2)

for i in "${!TABLES[@]}"; do
    table="${TABLES[$i]}"
    rows=$(query_db "SELECT COUNT(*) FROM \"$table\";")
    cols=$(query_db "SELECT COUNT(*) FROM pragma_table_info('$table');")
    check_value "$table lignes" "${EXP_ROWS[$i]}" "$rows"
    check_value "$table colonnes" "${EXP_COLS[$i]}" "$cols"
done

# ══════════════════════════════════════════════════════════════════════════
#  3. TRANSFORMATIONS ETL (doc §4)
# ══════════════════════════════════════════════════════════════════════════
section_header "3. Transformations ETL (§4)"

subsection "4.1 Deduplication geolocalisation"
unique_zips=$(query_db "SELECT COUNT(DISTINCT geolocation_zip_code_prefix) FROM olist_geolocation_dataset;")
check_value "Codes postaux uniques" "19015" "$unique_zips"

avg_per_zip=$(query_db "
    SELECT CAST(ROUND(CAST(COUNT(*) AS REAL) / COUNT(DISTINCT geolocation_zip_code_prefix)) AS INTEGER)
    FROM olist_geolocation_dataset;")
check_value "Entrees moyennes par zip (~53)" "53" "$avg_per_zip"

subsection "4.2 Produits sans categorie"
no_cat=$(query_db "
    SELECT COUNT(*) FROM olist_products_dataset
    WHERE product_category_name IS NULL OR TRIM(product_category_name) = '';")
check_value "Produits sans categorie" "610" "$no_cat"

subsection "4.3 Codes postaux non resolus"
cust_no_geo=$(query_db "
    SELECT COUNT(*) FROM olist_customers_dataset
    WHERE customer_zip_code_prefix NOT IN
        (SELECT DISTINCT geolocation_zip_code_prefix FROM olist_geolocation_dataset);")
check_value "Clients sans geolocalisation" "278" "$cust_no_geo"

sell_no_geo=$(query_db "
    SELECT COUNT(*) FROM olist_sellers_dataset
    WHERE seller_zip_code_prefix NOT IN
        (SELECT DISTINCT geolocation_zip_code_prefix FROM olist_geolocation_dataset);")
check_value "Vendeurs sans geolocalisation" "7" "$sell_no_geo"

subsection "4.5 Commandes sans articles"
no_items_total=$(query_db "
    SELECT COUNT(*) FROM olist_orders_dataset
    WHERE order_id NOT IN (SELECT DISTINCT order_id FROM olist_order_items_dataset);")
check_value "Commandes sans articles (total)" "775" "$no_items_total"

for pair in "unavailable:603" "canceled:164" "created:5" "invoiced:2" "shipped:1"; do
    status="${pair%%:*}"
    expected="${pair##*:}"
    actual=$(query_db "
        SELECT COUNT(*) FROM olist_orders_dataset
        WHERE order_id NOT IN (SELECT DISTINCT order_id FROM olist_order_items_dataset)
          AND order_status = '$status';")
    check_value "  Sans articles ($status)" "$expected" "$actual"
done

# ══════════════════════════════════════════════════════════════════════════
#  4. ANALYSE DE CONCORDANCE (doc §5)
# ══════════════════════════════════════════════════════════════════════════
section_header "4. Analyse de concordance (§5)"

subsection "Sommes financieres"
sum_price=$(query_db "
    SELECT PRINTF('%.2f', SUM(CAST(price AS REAL)))
    FROM olist_order_items_dataset;")
check_value "SUM(price)" "13591643.70" "$sum_price"

sum_freight=$(query_db "
    SELECT PRINTF('%.2f', SUM(CAST(freight_value AS REAL)))
    FROM olist_order_items_dataset;")
check_value "SUM(freight_value)" "2251909.54" "$sum_freight"

subsection "Integrite FK items -> orders"
orphans=$(query_db "
    SELECT COUNT(*) FROM olist_order_items_dataset
    WHERE order_id NOT IN (SELECT DISTINCT order_id FROM olist_orders_dataset);")
check_value "Items orphelins (FK items->orders)" "0" "$orphans"

distinct_orders=$(query_db "SELECT COUNT(DISTINCT order_id) FROM olist_order_items_dataset;")
info_value "Commandes distinctes dans items" "$distinct_orders"

# ══════════════════════════════════════════════════════════════════════════
#  5. DISTRIBUTION DES STATUTS (doc §6.5)
# ══════════════════════════════════════════════════════════════════════════
section_header "5. Distribution des statuts (§6.5)"

for pair in "delivered:96478" "shipped:1107" "canceled:625" "unavailable:609" \
            "invoiced:314" "processing:301" "created:5" "approved:2"; do
    status="${pair%%:*}"
    expected="${pair##*:}"
    actual=$(query_db "SELECT COUNT(*) FROM olist_orders_dataset WHERE order_status = '$status';")
    check_value "Statut $status" "$expected" "$actual"
done

# ══════════════════════════════════════════════════════════════════════════
#  6. ECARTS DE PAIEMENT (doc §7)
# ══════════════════════════════════════════════════════════════════════════
section_header "6. Ecarts de paiement (§7)"

# Creer des vues reutilisables pour eviter de repeter les CTEs
# Note : pas de ROUND intermediaire sur invoiced/paid pour eviter
# que l'arrondi n'absorbe des ecarts proches de 0.01
query_db "
CREATE VIEW v_order_gaps AS
WITH invoiced AS (
    SELECT order_id,
           SUM(CAST(price AS REAL)) + SUM(CAST(freight_value AS REAL)) AS total_invoiced
    FROM olist_order_items_dataset
    GROUP BY order_id
),
paid AS (
    SELECT order_id,
           SUM(CAST(payment_value AS REAL)) AS total_paid
    FROM olist_order_payments_dataset
    GROUP BY order_id
)
SELECT i.order_id,
       i.total_invoiced,
       p.total_paid,
       ROUND(p.total_paid - i.total_invoiced, 2) AS delta
FROM invoiced i
INNER JOIN paid p ON i.order_id = p.order_id;
"

# Type de paiement dominant par commande = mode (type le plus frequent),
# avec tiebreak alphabetique (reproduit le comportement de pandas mode())
query_db "
CREATE VIEW v_dominant_type AS
WITH type_mode AS (
    SELECT order_id, payment_type,
           COUNT(*) AS type_count,
           ROW_NUMBER() OVER (
               PARTITION BY order_id
               ORDER BY COUNT(*) DESC, payment_type ASC
           ) AS rn
    FROM olist_order_payments_dataset
    GROUP BY order_id, payment_type
)
SELECT order_id, payment_type FROM type_mode WHERE rn = 1;
"

subsection "Nombre de commandes avec ecart"
gap_count=$(query_db "SELECT COUNT(*) FROM v_order_gaps WHERE ABS(delta) > 0.01;")
check_value "Commandes avec ecart (>0.01 R$)" "303" "$gap_count"

subsection "Statistiques des ecarts"
avg_delta=$(query_db "SELECT PRINTF('%.2f', AVG(delta)) FROM v_order_gaps WHERE ABS(delta) > 0.01;")
check_value "Delta moyen" "9.48" "$avg_delta"

min_delta=$(query_db "SELECT PRINTF('%.2f', MIN(delta)) FROM v_order_gaps WHERE ABS(delta) > 0.01;")
check_value "Delta min" "-51.62" "$min_delta"

max_delta=$(query_db "SELECT PRINTF('%.2f', MAX(delta)) FROM v_order_gaps WHERE ABS(delta) > 0.01;")
check_value "Delta max" "182.81" "$max_delta"

sum_delta=$(query_db "SELECT PRINTF('%.2f', SUM(delta)) FROM v_order_gaps WHERE ABS(delta) > 0.01;")
check_value "Somme nette des ecarts" "2871.06" "$sum_delta"

subsection "Surpayees / sous-payees"
overpaid_count=$(query_db "SELECT COUNT(*) FROM v_order_gaps WHERE delta > 0.01;")
check_value "Commandes surpayees" "264" "$overpaid_count"

underpaid_count=$(query_db "SELECT COUNT(*) FROM v_order_gaps WHERE delta < -0.01;")
check_value "Commandes sous-payees" "39" "$underpaid_count"

overpaid_sum=$(query_db "SELECT PRINTF('%.2f', SUM(delta)) FROM v_order_gaps WHERE delta > 0.01;")
check_value "Somme surpayees" "3070.14" "$overpaid_sum"

underpaid_sum=$(query_db "SELECT PRINTF('%.2f', SUM(delta)) FROM v_order_gaps WHERE delta < -0.01;")
check_value "Somme sous-payees" "-199.08" "$underpaid_sum"

subsection "Repartition par type de paiement dominant"
for triple in "credit_card:75623:282" "boleto:19614:14" "debit_card:1520:7" "voucher:1908:0"; do
    IFS=':' read -r ptype exp_total exp_gap <<< "$triple"

    actual_total=$(query_db "
        SELECT COUNT(*) FROM v_order_gaps g
        JOIN v_dominant_type d ON g.order_id = d.order_id
        WHERE d.payment_type = '$ptype';")
    check_value "$ptype (total)" "$exp_total" "$actual_total"

    actual_gap=$(query_db "
        SELECT COUNT(*) FROM v_order_gaps g
        JOIN v_dominant_type d ON g.order_id = d.order_id
        WHERE d.payment_type = '$ptype' AND ABS(g.delta) > 0.01;")
    check_value "$ptype (avec ecart)" "$exp_gap" "$actual_gap"
done

# ══════════════════════════════════════════════════════════════════════════
#  7. ANALYSE INTERETS PARCELAMENTO (doc §8)
# ══════════════════════════════════════════════════════════════════════════
section_header "7. Analyse interets parcelamento (§8)"

query_db "
CREATE VIEW v_max_installments AS
SELECT order_id,
       MAX(CAST(payment_installments AS INTEGER)) AS max_installments
FROM olist_order_payments_dataset
GROUP BY order_id;
"

subsection "Installments moyens : ecart vs sans ecart"
avg_gap_inst=$(query_db "
    SELECT PRINTF('%.2f', AVG(inst.max_installments))
    FROM v_order_gaps g
    JOIN v_max_installments inst ON g.order_id = inst.order_id
    WHERE ABS(g.delta) > 0.01;")
check_value "Installments moyens (avec ecart)" "5.86" "$avg_gap_inst"

avg_nogap_inst=$(query_db "
    SELECT PRINTF('%.2f', AVG(inst.max_installments))
    FROM v_order_gaps g
    JOIN v_max_installments inst ON g.order_id = inst.order_id
    WHERE ABS(g.delta) <= 0.01;")
check_value "Installments moyens (sans ecart)" "2.92" "$avg_nogap_inst"

# ══════════════════════════════════════════════════════════════════════════
#  RESUME FINAL
# ══════════════════════════════════════════════════════════════════════════
section_header "RESUME"
echo ""
echo -e "  Total checks : $TOTAL"
echo -e "  ${GREEN}PASS${NC}  : $PASS"
echo -e "  ${RED}FAIL${NC}  : $FAIL"
echo ""
if [[ $FAIL -eq 0 ]]; then
    echo -e "  ${GREEN}${BOLD}Tous les checks sont passes — analyse verifiee !${NC}"
else
    echo -e "  ${RED}${BOLD}$FAIL check(s) en echec — verifier les ecarts ci-dessus${NC}"
fi

exit $((FAIL > 0 ? 1 : 0))
