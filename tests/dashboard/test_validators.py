"""Tests unitaires pour les validateurs d'exercices."""

import pytest
import pandas as pd
from src.dashboard.course.exercises import (
    validator_exact_match,
    validator_structure,
    validator_custom,
)


def test_validator_exact_match_success():
    """Vérifie que validator_exact_match accepte un DataFrame identique."""
    expected_df = pd.DataFrame({
        'col1': [1, 2, 3],
        'col2': ['a', 'b', 'c'],
    })

    validator = validator_exact_match(expected_df)
    result_df = expected_df.copy()

    success, message = validator(result_df)
    assert success is True, "Validation devrait réussir pour DataFrame identique"
    assert "Parfait" in message or "✅" in message


def test_validator_exact_match_wrong_columns():
    """Vérifie que validator_exact_match rejette des colonnes différentes."""
    expected_df = pd.DataFrame({
        'col1': [1, 2, 3],
        'col2': ['a', 'b', 'c'],
    })

    validator = validator_exact_match(expected_df)
    result_df = pd.DataFrame({
        'col1': [1, 2, 3],
        'col3': ['a', 'b', 'c'],  # Colonne différente
    })

    success, message = validator(result_df)
    assert success is False, "Validation devrait échouer pour colonnes différentes"
    assert "Colonnes incorrectes" in message


def test_validator_exact_match_wrong_rows():
    """Vérifie que validator_exact_match rejette un nombre de lignes différent."""
    expected_df = pd.DataFrame({
        'col1': [1, 2, 3],
    })

    validator = validator_exact_match(expected_df)
    result_df = pd.DataFrame({
        'col1': [1, 2],  # Moins de lignes
    })

    success, message = validator(result_df)
    assert success is False, "Validation devrait échouer pour nombre lignes différent"
    assert "Nombre de lignes incorrect" in message


def test_validator_structure_success():
    """Vérifie que validator_structure accepte la bonne structure."""
    validator = validator_structure(
        expected_columns=['name', 'age', 'city'],
        min_rows=2,
        max_rows=10,
    )

    result_df = pd.DataFrame({
        'name': ['Alice', 'Bob', 'Charlie'],
        'age': [25, 30, 35],
        'city': ['Paris', 'Lyon', 'Nice'],
    })

    success, message = validator(result_df)
    assert success is True, "Validation devrait réussir pour structure correcte"
    assert "Bonne structure" in message or "✅" in message


def test_validator_structure_wrong_columns():
    """Vérifie que validator_structure rejette des colonnes incorrectes."""
    validator = validator_structure(
        expected_columns=['name', 'age'],
        min_rows=1,
    )

    result_df = pd.DataFrame({
        'name': ['Alice'],
        'city': ['Paris'],  # Colonne incorrecte
    })

    success, message = validator(result_df)
    assert success is False, "Validation devrait échouer pour colonnes incorrectes"


def test_validator_structure_too_few_rows():
    """Vérifie que validator_structure rejette si pas assez de lignes."""
    validator = validator_structure(
        expected_columns=['name'],
        min_rows=5,
    )

    result_df = pd.DataFrame({
        'name': ['Alice', 'Bob'],  # Seulement 2 lignes
    })

    success, message = validator(result_df)
    assert success is False, "Validation devrait échouer pour pas assez de lignes"
    assert "Pas assez de lignes" in message


def test_validator_custom_success():
    """Vérifie que validator_custom accepte si check_fn retourne True."""
    def check_sorted_desc(df):
        """Vérifie que la colonne 'value' est triée DESC."""
        return df['value'].is_monotonic_decreasing

    validator = validator_custom(
        check_fn=check_sorted_desc,
        success_msg="✅ Bien trié !",
        error_msg="❌ Pas trié DESC",
    )

    result_df = pd.DataFrame({
        'value': [100, 50, 10, 5, 1],
    })

    success, message = validator(result_df)
    assert success is True, "Validation devrait réussir si triée DESC"
    assert "Bien trié" in message


def test_validator_custom_failure():
    """Vérifie que validator_custom rejette si check_fn retourne False."""
    def check_sorted_desc(df):
        return df['value'].is_monotonic_decreasing

    validator = validator_custom(
        check_fn=check_sorted_desc,
        error_msg="❌ Pas trié DESC",
    )

    result_df = pd.DataFrame({
        'value': [10, 50, 100],  # ASC au lieu de DESC
    })

    success, message = validator(result_df)
    assert success is False, "Validation devrait échouer si pas triée DESC"
    assert "Pas trié" in message
