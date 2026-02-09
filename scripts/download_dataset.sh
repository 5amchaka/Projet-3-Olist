#!/usr/bin/env bash
# Télécharger et valider le dataset Olist Brazilian E-commerce depuis Kaggle.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
RAW_DIR="$PROJECT_ROOT/data/raw"
ENV_FILE="$PROJECT_ROOT/.env"

# ── Charger les identifiants depuis .env ─────────────────────────────────
if [[ -f "$ENV_FILE" ]]; then
    set -a
    source "$ENV_FILE"
    set +a
    echo "[INFO] Loaded credentials from .env"
else
    echo "[WARN] No .env file found — expecting KAGGLE_USERNAME/KAGGLE_KEY in environment"
fi

if [[ -z "${KAGGLE_USERNAME:-}" || -z "${KAGGLE_KEY:-}" ]]; then
    echo "[ERROR] KAGGLE_USERNAME and KAGGLE_KEY must be set"
    exit 1
fi

# ── Résoudre le CLI kaggle ──────────────────────────────────────────────
if command -v kaggle &>/dev/null; then
    KAGGLE_CMD="kaggle"
elif [[ -x "$PROJECT_ROOT/.venv/bin/kaggle" ]]; then
    KAGGLE_CMD="$PROJECT_ROOT/.venv/bin/kaggle"
else
    echo "[ERROR] kaggle CLI not found. Install with: uv pip install kaggle"
    exit 1
fi

echo "[INFO] Using kaggle CLI: $KAGGLE_CMD"

# ── Téléchargement + extraction ─────────────────────────────────────────
mkdir -p "$RAW_DIR"
echo "[INFO] Downloading olistbr/brazilian-ecommerce → $RAW_DIR"
$KAGGLE_CMD datasets download -d olistbr/brazilian-ecommerce -p "$RAW_DIR" --unzip --force

# ── Fichiers attendus ───────────────────────────────────────────────────
EXPECTED_FILES=(
    "olist_customers_dataset.csv"
    "olist_geolocation_dataset.csv"
    "olist_orders_dataset.csv"
    "olist_order_items_dataset.csv"
    "olist_order_payments_dataset.csv"
    "olist_order_reviews_dataset.csv"
    "olist_products_dataset.csv"
    "olist_sellers_dataset.csv"
    "product_category_name_translation.csv"
)

echo ""
echo "[INFO] Validating downloaded files..."

MISSING=0
for f in "${EXPECTED_FILES[@]}"; do
    if [[ ! -f "$RAW_DIR/$f" ]]; then
        echo "  [MISSING] $f"
        MISSING=$((MISSING + 1))
    fi
done

if [[ $MISSING -gt 0 ]]; then
    echo "[ERROR] $MISSING expected file(s) missing!"
    exit 1
fi

echo "[OK] All 9 CSV files present."

# ── Validation parallèle : en-têtes + nombre de lignes ─────────────────
# Genere un manifest.txt avec nom, nb lignes et hash MD5 de chaque CSV.
# Le MD5 sert de reference pour verifier l'integrite des fichiers lors
# d'un eventuel re-telechargement (comparaison manuelle).
validate_csv() {
    local filepath="$1"
    local filename
    filename="$(basename "$filepath")"
    local header
    header="$(head -1 "$filepath")"
    local lines
    lines="$(wc -l < "$filepath")"
    local md5
    md5="$(md5sum "$filepath" | awk '{print $1}')"
    echo "$filename | lines: $lines | md5: $md5"
    echo "$filename,$lines,$md5" >> "$RAW_DIR/manifest.txt"
}
export -f validate_csv
export RAW_DIR

# Effacer le manifeste
echo "filename,lines,md5" > "$RAW_DIR/manifest.txt"

printf '%s\n' "${EXPECTED_FILES[@]}" \
    | xargs -I{} -P 4 bash -c 'validate_csv "$RAW_DIR/{}"'

echo ""
echo "[INFO] Manifest written to $RAW_DIR/manifest.txt"
echo "[DONE] Dataset download and validation complete."
