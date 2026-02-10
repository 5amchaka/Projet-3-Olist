"""Transformation : nettoyer et normaliser chaque dataset."""

import pandas as pd


# ── Utilitaires partagés ─────────────────────────────────────────────────

def drop_full_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """Supprimer les lignes exactement dupliquées."""
    n_before = len(df)
    df = df.drop_duplicates()
    n_dropped = n_before - len(df)
    if n_dropped:
        print(f"    Dropped {n_dropped:,} duplicate rows")
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


# ── Nettoyage par dataset ───────────────────────────────────────────────

def clean_customers(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliser ville (casse titre), état (majuscules), compléter code postal avec zéros."""
    df = drop_full_duplicates(df)
    df = strip_strings(df)
    df["customer_city"] = df["customer_city"].str.title()
    df["customer_state"] = df["customer_state"].str.upper()
    df["customer_zip_code_prefix"] = (
        df["customer_zip_code_prefix"].astype(str).str.zfill(5)
    )
    return df


def clean_geolocation(df: pd.DataFrame) -> pd.DataFrame:
    """Dédupliquer par zip_code_prefix en utilisant les coordonnées médianes."""
    df = strip_strings(df)
    df["geolocation_zip_code_prefix"] = (
        df["geolocation_zip_code_prefix"].astype(str).str.zfill(5)
    )
    df["geolocation_city"] = df["geolocation_city"].str.title()
    df["geolocation_state"] = df["geolocation_state"].str.upper()

    def _safe_mode(x):
        m = x.mode()
        return m.iloc[0] if len(m) > 0 else "unknown"

    agg = df.groupby("geolocation_zip_code_prefix").agg(
        geolocation_lat=("geolocation_lat", "median"),
        geolocation_lng=("geolocation_lng", "median"),
        geolocation_city=("geolocation_city", _safe_mode),
        geolocation_state=("geolocation_state", _safe_mode),
    ).reset_index()

    print(f"    Geolocation deduplicated: {len(df):,} -> {len(agg):,} rows")
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
        print(f"    WARNING: {invalid.sum()} orders with invalid status")
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
        print(f"    WARNING: {invalid.sum()} payments with unknown type")
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
    """Fusionner la traduction, remplir les valeurs numériques manquantes par la médiane, catégorie manquante par 'unknown'."""
    df = drop_full_duplicates(df)
    df = strip_strings(df)

    # Fusionner la traduction anglaise
    translation_df = strip_strings(translation_df)
    df = df.merge(translation_df, on="product_category_name", how="left")

    # Remplir les catégories manquantes
    df["product_category_name"] = df["product_category_name"].fillna("unknown")
    df["product_category_name_english"] = df["product_category_name_english"].fillna("unknown")

    # Remplir les colonnes numériques avec la médiane
    numeric_cols = [
        "product_name_lenght", "product_description_lenght",
        "product_photos_qty", "product_weight_g",
        "product_length_cm", "product_height_cm", "product_width_cm",
    ]
    for col in numeric_cols:
        if col in df.columns:
            median_val = df[col].median()
            df[col] = df[col].fillna(median_val)

    return df


def clean_sellers(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliser ville (casse titre), état (majuscules), compléter code postal avec zéros."""
    df = drop_full_duplicates(df)
    df = strip_strings(df)
    df["seller_city"] = df["seller_city"].str.title()
    df["seller_state"] = df["seller_state"].str.upper()
    df["seller_zip_code_prefix"] = (
        df["seller_zip_code_prefix"].astype(str).str.zfill(5)
    )
    return df


def clean_category_translation(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoyage basique de la table de traduction."""
    df = drop_full_duplicates(df)
    df = strip_strings(df)
    return df


# ── Orchestrateur ────────────────────────────────────────────────────────

def clean_all(dfs: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Exécuter toutes les fonctions de nettoyage et retourner les DataFrames nettoyés."""
    cleaned = {}

    print("Cleaning customers...")
    cleaned["customers"] = clean_customers(dfs["customers"].copy())

    print("Cleaning geolocation...")
    cleaned["geolocation"] = clean_geolocation(dfs["geolocation"].copy())

    print("Cleaning orders...")
    cleaned["orders"] = clean_orders(dfs["orders"].copy())

    print("Cleaning order_items...")
    cleaned["order_items"] = clean_order_items(dfs["order_items"].copy())

    print("Cleaning order_payments...")
    cleaned["order_payments"] = clean_order_payments(dfs["order_payments"].copy())

    print("Cleaning order_reviews...")
    cleaned["order_reviews"] = clean_order_reviews(dfs["order_reviews"].copy())

    print("Cleaning category_translation...")
    cleaned["category_translation"] = clean_category_translation(
        dfs["category_translation"].copy()
    )

    print("Cleaning products (with translation merge)...")
    cleaned["products"] = clean_products(
        dfs["products"].copy(), cleaned["category_translation"]
    )

    print("Cleaning sellers...")
    cleaned["sellers"] = clean_sellers(dfs["sellers"].copy())

    return cleaned
