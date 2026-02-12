"""Smoke tests d'intégration des requêtes SQL du dashboard."""

from pathlib import Path

import pandas as pd
import pytest

from src.config import DATABASE_PATH
from src.dashboard import db as dashboard_db
from src.dashboard.course.content import COURSE_MODULES

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module", autouse=True)
def require_database():
    """Skip si la base n'est pas présente."""
    if not DATABASE_PATH.exists():
        pytest.skip("Base absente — lancer le pipeline ETL avant ces tests")


@pytest.fixture(scope="module", autouse=True)
def reset_dashboard_connection():
    """Réinitialise la connexion singleton dashboard avant/après les tests."""
    if dashboard_db._conn is not None:
        dashboard_db._conn.close()
        dashboard_db._conn = None
    yield
    if dashboard_db._conn is not None:
        dashboard_db._conn.close()
        dashboard_db._conn = None


@pytest.mark.parametrize(
    "sql_file",
    [
        "overview_kpis.sql",
        "overview_monthly_mini.sql",
        "trends_monthly.sql",
        "rfm_segmentation.sql",
        "seller_scoring.sql",
        "cohorts_retention.sql",
        "new_vs_recurring.sql",
        "ltv_cohorts.sql",
        "pareto_sellers.sql",
        "top_products.sql",
        "ca_yoy.sql",
        "basket_avg.sql",
    ],
)
def test_dashboard_sql_executes(sql_file):
    """Chaque requête dashboard doit s'exécuter sans erreur."""
    sql = dashboard_db.load_sql(sql_file)
    df = dashboard_db.query(sql)

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns)
    assert not df.empty, f"{sql_file} retourne 0 ligne"


def test_required_dashboard_sql_are_covered():
    """Le test paramétré couvre toutes les requêtes utilisées par les pages."""
    expected = {
        "overview_kpis.sql",
        "overview_monthly_mini.sql",
        "trends_monthly.sql",
        "rfm_segmentation.sql",
        "seller_scoring.sql",
        "cohorts_retention.sql",
        "new_vs_recurring.sql",
        "ltv_cohorts.sql",
        "pareto_sellers.sql",
        "top_products.sql",
        "ca_yoy.sql",
        "basket_avg.sql",
    }
    actual = {p.name for p in (Path("sql/dashboard")).glob("*.sql")}
    missing = expected - actual
    assert not missing, (
        "Ajouter le nouveau fichier SQL à la liste paramétrée du test "
        "test_dashboard_sql_executes."
    )


@pytest.mark.parametrize(
    ("module_id", "expects_exercises"),
    [
        ("module_1_fundamentals", True),
        ("module_2_window_functions", True),
        ("module_3_ctes_advanced", True),
        ("module_4_complex_cases", True),
        ("module_5_optimization", False),
    ],
)
def test_course_exercise_solutions_execute(module_id, expects_exercises):
    """Toutes les solution_sql des modules 1->5 doivent rester exécutables."""
    module = next(m for m in COURSE_MODULES if m.id == module_id)
    lessons_with_exercise = [lesson for lesson in module.lessons if lesson.exercise is not None]

    if not expects_exercises:
        assert not lessons_with_exercise, (
            f"{module_id} ne devrait pas contenir d'exercice SQL exécutable à ce stade"
        )
        return

    assert lessons_with_exercise, f"{module_id} doit contenir au moins un exercice"

    for lesson in lessons_with_exercise:
        df = dashboard_db.query(lesson.exercise.solution_sql)
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns), f"{lesson.exercise.id} retourne 0 colonne"
        assert not df.empty, f"{lesson.exercise.id} retourne 0 ligne"
