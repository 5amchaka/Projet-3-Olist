"""Configuration centralisée pour le pipeline ETL Olist."""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Chemins ──────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
STAGING_DIR = DATA_DIR / "staging"
PROCESSED_DIR = DATA_DIR / "processed"
DATABASE_DIR = DATA_DIR / "database"

DATABASE_PATH = DATABASE_DIR / "olist_dw.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# ── Correspondance des fichiers CSV ─────────────────────────────────────
CSV_FILES = {
    "customers": "olist_customers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

# ── Identifiant du dataset Kaggle ──────────────────────────────────────
KAGGLE_DATASET = "olistbr/brazilian-ecommerce"
