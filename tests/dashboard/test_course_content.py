"""Tests unitaires pour la structure du cours (content.py)."""

import pytest
from src.dashboard.course.content import (
    COURSE_MODULES,
    CONCEPTS_INDEX,
    Module,
    Lesson,
    SQLConcept,
)


def test_course_modules_structure():
    """Vérifie que COURSE_MODULES contient 5 modules."""
    assert len(COURSE_MODULES) == 5, "Le cours doit contenir 5 modules"

    # Vérifier IDs uniques
    module_ids = [m.id for m in COURSE_MODULES]
    assert len(module_ids) == len(set(module_ids)), "Les IDs modules doivent être uniques"


def test_course_total_lessons():
    """Vérifie que le cours contient 15 leçons au total."""
    total_lessons = sum(len(m.lessons) for m in COURSE_MODULES)
    assert total_lessons == 15, f"Le cours doit contenir 15 leçons (trouvé {total_lessons})"


def test_each_module_has_3_lessons():
    """Vérifie que chaque module a exactement 3 leçons."""
    for module in COURSE_MODULES:
        assert len(module.lessons) == 3, f"Module {module.id} doit avoir 3 leçons"


def test_module_attributes():
    """Vérifie que tous les modules ont les attributs requis."""
    for module in COURSE_MODULES:
        assert isinstance(module, Module)
        assert module.id, "Module doit avoir un ID"
        assert module.icon, "Module doit avoir une icône"
        assert module.title, "Module doit avoir un titre"
        assert module.subtitle, "Module doit avoir un sous-titre"
        assert module.estimated_duration_min > 0, "Durée estimée doit être > 0"


def test_lesson_attributes():
    """Vérifie que toutes les leçons ont les attributs requis."""
    for module in COURSE_MODULES:
        for lesson in module.lessons:
            assert isinstance(lesson, Lesson)
            assert lesson.title, "Leçon doit avoir un titre"
            assert lesson.theory, "Leçon doit avoir de la théorie"
            assert len(lesson.theory) > 100, "Théorie doit contenir au moins 100 caractères"
            assert lesson.demo_sql_file, "Leçon doit référencer un fichier SQL"
            assert lesson.demo_sql_file.endswith('.sql'), "Fichier démo doit être .sql"


def test_concepts_index():
    """Vérifie que CONCEPTS_INDEX contient au moins 15 concepts."""
    assert len(CONCEPTS_INDEX) >= 15, f"Au moins 15 concepts attendus (trouvé {len(CONCEPTS_INDEX)})"

    # Vérifier quelques concepts clés
    required_concepts = ['SELECT', 'WHERE', 'JOIN', 'GROUP BY', 'LAG', 'NTILE', 'WITH']
    for concept_key in required_concepts:
        assert concept_key in CONCEPTS_INDEX, f"Concept {concept_key} doit être présent"


def test_concept_structure():
    """Vérifie la structure des concepts SQL."""
    for keyword, concept in CONCEPTS_INDEX.items():
        assert isinstance(concept, SQLConcept)
        assert concept.keyword == keyword, "Keyword doit correspondre à la clé"
        assert concept.name, "Concept doit avoir un nom"
        assert concept.short_desc, "Concept doit avoir une description courte"
        assert concept.detailed_desc, "Concept doit avoir une description détaillée"
        assert concept.example_sql, "Concept doit avoir un exemple SQL"
        assert concept.category in ['aggregate', 'window', 'cte', 'join', 'index', 'function']


def test_exercises_present():
    """Vérifie que certaines leçons ont des exercices."""
    exercises_count = sum(
        1 for m in COURSE_MODULES for l in m.lessons if l.exercise is not None
    )
    assert exercises_count >= 6, f"Au moins 6 exercices attendus (trouvé {exercises_count})"


def test_exploration_links_present():
    """Vérifie que certaines leçons ont des liens exploration."""
    links_count = sum(
        1 for m in COURSE_MODULES for l in m.lessons if l.exploration_link is not None
    )
    assert links_count >= 5, f"Au moins 5 liens exploration attendus (trouvé {links_count})"
