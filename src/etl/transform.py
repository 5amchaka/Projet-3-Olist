"""Transformation : nettoyer et normaliser chaque dataset."""

import logging

import pandas as pd

from src.etl.utils import safe_mode

logger = logging.getLogger(__name__)


# ── Utilitaires partagés ─────────────────────────────────────────────────

def drop_full_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Supprimer les lignes exactement dupliquées."""
    n_before = len(df)
    df = df.drop_duplicates()
    n_dropped = n_before - len(df)
    if n_dropped:
        logger.info("    Dropped %s duplicate rows", f"{n_dropped:,}")
    return df


def parse_dates(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Analyser les colonnes date/datetime."""
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df


def strip_strings(df: pd.DataFrame) -> pd.DataFrame:
    """Supprimer les espaces en début/fin des colonnes texte."""
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].str.strip()
    return df


def _normalize_geo_columns(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    """Normaliser ville (casse titre), état (majuscules), code postal (5 chiffres) pour un préfixe donné."""
    df[f"{prefix}_city"] = df[f"{prefix}_city"].str.title()
    df[f"{prefix}_state"] = df[f"{prefix}_state"].str.upper()
    df[f"{prefix}_zip_code_prefix"] = (
        df[f"{prefix}_zip_code_prefix"].astype(str).str.zfill(5)
    )
    return df


# ── Nettoyage par dataset ───────────────────────────────────────────────

def clean_customers(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliser ville (casse titre), état (majuscules), compléter code postal avec zéros."""
    df = drop_full_duplicates(df)
    df = strip_strings(df)
    return _normalize_geo_columns(df, "customer")


def clean_geolocation(df: pd.DataFrame) -> pd.DataFrame:
    """Dédupliquer par zip_code_prefix en utilisant les coordonnées médianes."""
    df = strip_strings(df)
    df = _normalize_geo_columns(df, "geolocation")

    agg = df.groupby("geolocation_zip_code_prefix").agg(
        geolocation_lat=("geolocation_lat", "median"),
        geolocation_lng=("geolocation_lng", "median"),
        geolocation_city=("geolocation_city", safe_mode),
        geolocation_state=("geolocation_state", safe_mode),
    ).reset_index()

    logger.info("    Geolocation deduplicated: %s -> %s rows",
                f"{len(df):,}", f"{len(agg):,}")
    return agg


def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    """Analyser les horodatages, valider le statut."""
    df = drop_full_duplicates(df)
    df = strip_strings(df)
    ts_cols = [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ]
    df = parse_dates(df, ts_cols)

    valid_statuses = {
        "delivered", "shipped", "canceled", "unavailable",
        "invoiced", "processing", "created", "approved",
    }
    invalid = ~df["order_status"].isin(valid_statuses)
    if invalid.any():
        logger.warning("%d orders with invalid status dropped", invalid.sum())
        df = df[~invalid]
    return df


def clean_order_items(df: pd.DataFrame) -> pd.DataFrame:
    """Analyser shipping_limit_date, valider prix >= 0."""
    df = drop_full_duplicates(df)
    df = strip_strings(df)
    df = parse_dates(df, ["shipping_limit_date"])
    df["price"] = df["price"].clip(lower=0)
    df["freight_value"] = df["freight_value"].clip(lower=0)
    return df


def clean_order_payments(df: pd.DataFrame) -> pd.DataFrame:
    """Valider payment_type et payment_value >= 0."""
    df = drop_full_duplicates(df)
    df = strip_strings(df)
    valid_types = {"credit_card", "boleto", "voucher", "debit_card", "not_defined"}
    invalid = ~df["payment_type"].isin(valid_types)
    if invalid.any():
        logger.warning("%d payments with unknown type dropped", invalid.sum())
        df = df[~invalid]
    df["payment_value"] = df["payment_value"].clip(lower=0)
    return df


def clean_order_reviews(df: pd.DataFrame) -> pd.DataFrame:
    """Limiter le score entre 1-5, remplacer les commentaires null par une chaîne vide."""
    df = drop_full_duplicates(df)
    df = strip_strings(df)
    df["review_score"] = df["review_score"].clip(1, 5)
    df["review_comment_title"] = df["review_comment_title"].fillna("")
    df["review_comment_message"] = df["review_comment_message"].fillna("")
    df = parse_dates(df, ["review_creation_date", "review_answer_timestamp"])
    return df


def clean_products(df: pd.DataFrame, translation_df: pd.DataFrame) -> pd.DataFrame:
    """Fusionner la traduction anglaise, imputer les valeurs manquantes (médiane / 'unknown')."""
    df = drop_full_duplicates(df)
    df = strip_strings(df)

    translation_df = strip_strings(translation_df)
    df = df.merge(translation_df, on="product_category_name", how="left")

    df["product_category_name"] = df["product_category_name"].fillna("unknown")
    df["product_category_name_english"] = df["product_category_name_english"].fillna("unknown")

    numeric_cols = [
        "product_name_lenght", "product_description_lenght",
        "product_photos_qty", "product_weight_g",
        "product_length_cm", "product_height_cm", "product_width_cm",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())

    return df


def clean_sellers(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliser ville (casse titre), état (majuscules), compléter code postal avec zéros."""
    df = drop_full_duplicates(df)
    df = strip_strings(df)
    return _normalize_geo_columns(df, "seller")


def clean_category_translation(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoyage basique de la table de traduction."""
    df = drop_full_duplicates(df)
    df = strip_strings(df)
    return df


# ── Registry déclarative des cleaners ─────────────────────────────────────
#
# Chaque entrée : (nom_dataset, fonction_cleaner, liste de dépendances).
# Les dépendances font référence à d'autres datasets déjà nettoyés, passés
# comme arguments supplémentaires à la fonction de nettoyage.

_CLEANERS: list[tuple[str, callable, list[str]]] = [
    ("customers",            clean_customers,            []),
    ("geolocation",          clean_geolocation,          []),
    ("orders",               clean_orders,               []),
    ("order_items",          clean_order_items,           []),
    ("order_payments",       clean_order_payments,        []),
    ("order_reviews",        clean_order_reviews,         []),
    ("category_translation", clean_category_translation,  []),
    ("sellers",              clean_sellers,               []),
    ("products",             clean_products,              ["category_translation"]),
]


def clean_all(dfs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Exécuter toutes les fonctions de nettoyage et retourner les DataFrames nettoyés."""
    cleaned: dict[str, pd.DataFrame] = {}

    for name, cleaner, deps in _CLEANERS:
        logger.info("Cleaning %s...", name)
        args = [dfs[name].copy()] + [cleaned[dep] for dep in deps]
        cleaned[name] = cleaner(*args)

    return cleaned
