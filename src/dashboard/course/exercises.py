"""
Validateurs d'exercices SQL et exercices prédéfinis.

Ce module fournit :
- 3 types de validateurs (exact_match, structure, custom)
- 9 exercices SQL prédéfinis (beginner, intermediate, advanced)
"""

from typing import Callable
import pandas as pd
import numpy as np


# ============================================================================
# VALIDATEURS GÉNÉRIQUES
# ============================================================================

def validator_exact_match(expected_df: pd.DataFrame) -> Callable[[pd.DataFrame], tuple[bool, str]]:
    """
    Validateur strict : structure + valeurs identiques.

    Tolère 1% de différence sur les floats (arrondi).

    Args:
        expected_df: DataFrame de référence

    Returns:
        Fonction validatrice (df) -> (success, message)
    """
    def validate(result_df: pd.DataFrame) -> tuple[bool, str]:
        # Vérifier colonnes
        if list(result_df.columns) != list(expected_df.columns):
            return False, f"❌ Colonnes incorrectes.\nAttendu: {list(expected_df.columns)}\nReçu: {list(result_df.columns)}"

        # Vérifier nombre de lignes
        if len(result_df) != len(expected_df):
            return False, f"❌ Nombre de lignes incorrect. Attendu: {len(expected_df)}, reçu: {len(result_df)}"

        # Comparer valeurs (tolère 1% différence floats)
        try:
            pd.testing.assert_frame_equal(
                result_df.reset_index(drop=True),
                expected_df.reset_index(drop=True),
                check_dtype=False,
                rtol=0.01,  # 1% tolérance relative
                atol=0.01   # 0.01 tolérance absolue
            )
            return True, "✅ Parfait ! Votre requête retourne exactement le résultat attendu."
        except AssertionError as e:
            return False, f"❌ Les valeurs ne correspondent pas.\n\n{str(e)[:500]}"

    return validate


def validator_structure(
    expected_columns: list[str],
    min_rows: int = 1,
    max_rows: int | None = None
) -> Callable[[pd.DataFrame], tuple[bool, str]]:
    """
    Validateur souple : vérifie structure (colonnes + nb lignes).

    Ne vérifie PAS les valeurs. Utile pour exercices exploratoires.

    Args:
        expected_columns: Liste des colonnes attendues (ordre important)
        min_rows: Nombre minimum de lignes
        max_rows: Nombre maximum de lignes (None = pas de limite)

    Returns:
        Fonction validatrice
    """
    def validate(result_df: pd.DataFrame) -> tuple[bool, str]:
        # Vérifier colonnes
        if list(result_df.columns) != expected_columns:
            return False, f"❌ Colonnes incorrectes.\nAttendu: {expected_columns}\nReçu: {list(result_df.columns)}"

        # Vérifier nombre de lignes
        if len(result_df) < min_rows:
            return False, f"❌ Pas assez de lignes. Minimum: {min_rows}, reçu: {len(result_df)}"

        if max_rows and len(result_df) > max_rows:
            return False, f"❌ Trop de lignes. Maximum: {max_rows}, reçu: {len(result_df)}"

        return True, f"✅ Bonne structure ! {len(result_df)} lignes avec les colonnes correctes."

    return validate


def validator_custom(
    check_fn: Callable[[pd.DataFrame], bool],
    success_msg: str = "✅ Exercice validé !",
    error_msg: str = "❌ La logique de votre requête n'est pas correcte."
) -> Callable[[pd.DataFrame], tuple[bool, str]]:
    """
    Validateur personnalisé avec logique arbitraire.

    Args:
        check_fn: Fonction (df) -> bool qui vérifie la logique métier
        success_msg: Message en cas de succès
        error_msg: Message en cas d'échec

    Returns:
        Fonction validatrice
    """
    def validate(result_df: pd.DataFrame) -> tuple[bool, str]:
        try:
            if check_fn(result_df):
                return True, success_msg
            else:
                return False, error_msg
        except Exception as e:
            return False, f"❌ Erreur lors de la validation: {str(e)}"

    return validate


# ============================================================================
# EXERCICES PRÉDÉFINIS - BEGINNER
# ============================================================================

# Note: Les solutions SQL sont stockées dans sql/exercises/
# Ici on définit uniquement les métadonnées et validateurs

def get_beginner_ex1_validator() -> Callable:
    """Filtrer commandes 2017 livrées, tri prix DESC."""
    return validator_structure(
        expected_columns=['order_id', 'order_date', 'price'],
        min_rows=50  # Au moins 50 commandes en 2017
    )


def get_beginner_ex2_validator() -> Callable:
    """Top 5 catégories par CA."""
    def check(df: pd.DataFrame) -> bool:
        # Vérifier structure
        if list(df.columns) != ['category', 'total_revenue']:
            return False
        # Vérifier nombre de lignes (exactement 5)
        if len(df) != 5:
            return False
        # Vérifier tri décroissant
        if not df['total_revenue'].is_monotonic_decreasing:
            return False
        return True

    return validator_custom(
        check,
        success_msg="✅ Excellent ! Top 5 catégories correctement triées.",
        error_msg="❌ Vérifiez : 1) Colonnes (category, total_revenue), 2) Exactement 5 lignes, 3) Tri DESC"
    )


def get_beginner_ex3_validator() -> Callable:
    """CA par état client."""
    return validator_structure(
        expected_columns=['state', 'total_revenue', 'nb_orders'],
        min_rows=20  # Au moins 20 états
    )


# ============================================================================
# EXERCICES PRÉDÉFINIS - INTERMEDIATE
# ============================================================================

def get_intermediate_ex1_validator() -> Callable:
    """Variation YoY du CA mensuel avec LAG."""
    def check(df: pd.DataFrame) -> bool:
        required_cols = ['year', 'month', 'revenue', 'revenue_previous_year', 'yoy_growth_pct']
        if list(df.columns) != required_cols:
            return False
        # Vérifier que LAG a bien créé des NULL pour la première année
        if df['revenue_previous_year'].isna().sum() < 6:  # Au moins 6 mois sans année précédente
            return False
        return True

    return validator_custom(
        check,
        success_msg="✅ Parfait ! LAG correctement utilisé pour calculer la croissance YoY.",
        error_msg="❌ Vérifiez : 1) Colonnes attendues, 2) LAG avec offset 12 mois, 3) Calcul % croissance"
    )


def get_intermediate_ex2_validator() -> Callable:
    """Quintiles clients par montant total."""
    def check(df: pd.DataFrame) -> bool:
        if list(df.columns) != ['customer_id', 'total_spent', 'quintile']:
            return False
        # Vérifier quintiles 1-5
        unique_quintiles = sorted(df['quintile'].unique())
        if unique_quintiles != [1, 2, 3, 4, 5]:
            return False
        # Vérifier répartition équitable (~20% par quintile)
        for q in range(1, 6):
            pct = (df['quintile'] == q).sum() / len(df)
            if not (0.15 < pct < 0.25):  # Tolérance 15-25%
                return False
        return True

    return validator_custom(
        check,
        success_msg="✅ Excellent ! Quintiles correctement calculés avec NTILE(5).",
        error_msg="❌ Vérifiez : 1) NTILE(5) sur total_spent, 2) Quintiles 1-5, 3) Répartition équitable"
    )


def get_intermediate_ex3_validator() -> Callable:
    """Running total mensuel du CA."""
    def check(df: pd.DataFrame) -> bool:
        if list(df.columns) != ['month', 'monthly_revenue', 'cumulative_revenue']:
            return False
        # Vérifier que cumul est croissant
        if not df['cumulative_revenue'].is_monotonic_increasing:
            return False
        # Vérifier que dernier cumul = somme de tous les monthly
        expected_final = df['monthly_revenue'].sum()
        actual_final = df['cumulative_revenue'].iloc[-1]
        if not np.isclose(expected_final, actual_final, rtol=0.01):
            return False
        return True

    return validator_custom(
        check,
        success_msg="✅ Parfait ! Running total calculé avec SUM() OVER (ORDER BY ...).",
        error_msg="❌ Vérifiez : 1) SUM() OVER (ORDER BY month ROWS UNBOUNDED PRECEDING), 2) Cumul croissant"
    )


# ============================================================================
# EXERCICES PRÉDÉFINIS - ADVANCED
# ============================================================================

def get_advanced_ex1_validator() -> Callable:
    """Top 10 produits → calcul % du total (2 CTEs)."""
    def check(df: pd.DataFrame) -> bool:
        if list(df.columns) != ['product_id', 'revenue', 'pct_of_total']:
            return False
        # Vérifier exactement 10 lignes
        if len(df) != 10:
            return False
        # Vérifier que somme % ≈ % réel du top 10
        pct_sum = df['pct_of_total'].sum()
        if not (5 < pct_sum < 100):  # Top 10 doit être entre 5% et 100%
            return False
        return True

    return validator_custom(
        check,
        success_msg="✅ Excellent ! CTEs multi-niveaux correctement chaînées.",
        error_msg="❌ Vérifiez : 1) 2 CTEs (total + products), 2) Exactement 10 lignes, 3) Calcul % correct"
    )


def get_advanced_ex2_validator() -> Callable:
    """Clients avec 2+ commandes."""
    return validator_structure(
        expected_columns=['customer_id', 'nb_orders'],
        min_rows=10  # Au moins 10 clients récurrents
    )


def get_advanced_ex3_validator() -> Callable:
    """Top 3 vendeurs par état (PARTITION BY)."""
    def check(df: pd.DataFrame) -> bool:
        required_cols = ['state', 'seller_id', 'revenue', 'rank_in_state']
        if list(df.columns) != required_cols:
            return False
        # Vérifier que chaque état a max 3 vendeurs
        state_counts = df.groupby('state').size()
        if (state_counts > 3).any():
            return False
        # Vérifier que ranks sont 1, 2, 3
        unique_ranks = sorted(df['rank_in_state'].unique())
        if not all(r in [1, 2, 3] for r in unique_ranks):
            return False
        return True

    return validator_custom(
        check,
        success_msg="✅ Parfait ! PARTITION BY state + filtre rank <= 3.",
        error_msg="❌ Vérifiez : 1) ROW_NUMBER() OVER (PARTITION BY state ...), 2) WHERE rank <= 3"
    )


# ============================================================================
# EXERCICES DE MODULE 5 (OPTIMISATION)
# ============================================================================

def get_optimization_ex1_validator() -> Callable:
    """Analyser EXPLAIN et proposer index."""
    # Cet exercice est vérifié manuellement (pas de validateur auto)
    return validator_custom(
        lambda df: True,  # Toujours succès
        success_msg="✅ Requête exécutée. Analysez le plan EXPLAIN pour proposer des optimisations.",
        error_msg=""
    )


def get_optimization_ex2_validator() -> Callable:
    """Optimiser SELECT * → projection minimale."""
    return validator_structure(
        expected_columns=['order_id', 'price', 'order_status'],  # Colonnes minimales
        min_rows=100
    )


def get_optimization_ex3_validator() -> Callable:
    """Transformer sous-requête corrélée en MATERIALIZED."""
    def check(df: pd.DataFrame) -> bool:
        # Vérifier que la requête contient MATERIALIZED (checker via le code SQL plutôt)
        # Pour l'instant, on valide juste la structure
        return len(df) > 0

    return validator_custom(
        check,
        success_msg="✅ Bonne transformation ! Vérifiez les gains de performance avec EXPLAIN.",
        error_msg="❌ Assurez-vous d'utiliser WITH ... AS MATERIALIZED."
    )
