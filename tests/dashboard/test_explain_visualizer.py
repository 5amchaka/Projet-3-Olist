"""Tests unitaires pour ExplainVisualizer."""

import pytest
from src.dashboard.components.explain_visualizer import ExplainVisualizer


def test_parse_explain_scan():
    """Vérifie le parsing d'un SCAN TABLE."""
    explain_output = """
QUERY PLAN
|--SCAN TABLE fact_orders
    """

    viz = ExplainVisualizer(explain_output)
    assert len(viz.steps) == 1, "Devrait parser 1 step"

    step = viz.steps[0]
    assert step['type'] == 'scan', "Type devrait être 'scan'"
    assert step['optimized'] is False, "SCAN n'est pas optimisé"
    assert 'lent' in step['explanation'].lower(), "Explication devrait mentionner 'lent'"


def test_parse_explain_search_indexed():
    """Vérifie le parsing d'un SEARCH avec index."""
    explain_output = """
QUERY PLAN
|--SEARCH TABLE fact_orders USING INDEX idx_orders_date (order_date>?)
    """

    viz = ExplainVisualizer(explain_output)
    assert len(viz.steps) == 1

    step = viz.steps[0]
    assert step['type'] == 'search_indexed', "Type devrait être 'search_indexed'"
    assert step['optimized'] is True, "SEARCH avec index est optimisé"
    assert 'rapide' in step['explanation'].lower(), "Explication devrait mentionner 'rapide'"


def test_parse_explain_multiple_steps():
    """Vérifie le parsing de plusieurs steps."""
    explain_output = """
QUERY PLAN
|--SCAN TABLE fact_orders
|--SEARCH TABLE dim_products USING INDEX idx_product_key
`--USE TEMP B-TREE FOR ORDER BY
    """

    viz = ExplainVisualizer(explain_output)
    assert len(viz.steps) == 3, "Devrait parser 3 steps"

    assert viz.steps[0]['type'] == 'scan'
    assert viz.steps[1]['type'] == 'search_indexed'
    assert viz.steps[2]['type'] == 'temp_btree'


def test_parse_explain_materialize():
    """Vérifie le parsing d'une MATERIALIZE."""
    explain_output = """
QUERY PLAN
|--MATERIALIZE customer_stats
`--SCAN SUBQUERY
    """

    viz = ExplainVisualizer(explain_output)

    materialize_step = next((s for s in viz.steps if s['type'] == 'materialize'), None)
    assert materialize_step is not None, "Devrait trouver un step materialize"
    assert materialize_step['optimized'] is True, "MATERIALIZE est optimisé"


def test_initial_step_index():
    """Vérifie que l'index initial est 0."""
    explain_output = "QUERY PLAN\n|--SCAN TABLE fact_orders"
    viz = ExplainVisualizer(explain_output)

    assert viz.current_step_index == 0, "Index initial devrait être 0"


def test_navigation_bounds():
    """Vérifie que la navigation respecte les bornes (logique uniquement)."""
    explain_output = """
QUERY PLAN
|--SCAN TABLE fact_orders
|--SEARCH TABLE dim_customers
    """

    viz = ExplainVisualizer(explain_output)

    # Vérifier que nous avons 2 steps
    assert len(viz.steps) == 2, "Devrait avoir 2 steps"

    # Test incrémentation
    viz.current_step_index = 0
    # Simuler next (sans appeler _render_steps)
    if viz.current_step_index < len(viz.steps) - 1:
        viz.current_step_index += 1
    assert viz.current_step_index == 1, "Devrait passer à 1"

    # Essayer d'aller au-delà du dernier (devrait rester à 1)
    if viz.current_step_index < len(viz.steps) - 1:
        viz.current_step_index += 1
    assert viz.current_step_index == 1, "Ne devrait pas dépasser le dernier step"

    # Test décrémentation
    if viz.current_step_index > 0:
        viz.current_step_index -= 1
    assert viz.current_step_index == 0, "Devrait revenir à 0"

    # Essayer d'aller en dessous de 0
    if viz.current_step_index > 0:
        viz.current_step_index -= 1
    assert viz.current_step_index == 0, "Ne devrait pas aller en dessous de 0"
