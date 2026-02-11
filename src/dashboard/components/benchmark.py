"""Moteur de benchmark SQL — mesure les performances avant/apres optimisation."""

import sqlite3
import statistics
import time
from dataclasses import dataclass

from src.dashboard import db


@dataclass
class BenchmarkResult:
    """Resultat d'un benchmark comparatif avant/apres."""

    label: str
    time_before_ms: float
    time_after_ms: float
    std_before_ms: float
    std_after_ms: float
    speedup: float
    rows_before: int
    rows_after: int
    iterations: int
    explain_before: list[str]
    explain_after: list[str]


def run_benchmark(
    before_sql: str,
    after_sql: str,
    label: str,
    iterations: int = 30,
    warmup: int = 5,
    time_budget_s: float = 3.0,
) -> BenchmarkResult:
    """Execute un benchmark comparatif entre deux requetes SQL.

    - Phase de warm-up pour remplir le page cache SQLite
    - Mesure via time.perf_counter() (haute resolution)
    - Adapte le nombre d'iterations au budget temps (requetes lentes = moins d'iterations)
    - Retourne moyennes, ecarts-types et speedup
    """
    conn = db.get_connection()

    # -- Calibrage : 1 run pour estimer le temps et remplir le cache ------
    start = time.perf_counter()
    conn.execute(before_sql).fetchall()
    single_ms = (time.perf_counter() - start) * 1000

    # Adapter warmup et iterations au temps de la requete
    actual_warmup = min(warmup, max(1, int(1000 / max(single_ms, 0.01))))
    actual_iterations = max(3, min(iterations, int(time_budget_s * 1000 / max(single_ms, 0.01))))

    # -- Warm-up : remplir le cache SQLite ---------------------------------
    for _ in range(actual_warmup):
        conn.execute(before_sql).fetchall()
        conn.execute(after_sql).fetchall()

    # -- Mesure BEFORE -----------------------------------------------------
    times_before: list[float] = []
    rows_before = 0
    for _ in range(actual_iterations):
        start = time.perf_counter()
        cursor = conn.execute(before_sql)
        rows = cursor.fetchall()
        elapsed = (time.perf_counter() - start) * 1000  # ms
        times_before.append(elapsed)
        rows_before = len(rows)

    # -- Mesure AFTER ------------------------------------------------------
    times_after: list[float] = []
    rows_after = 0
    for _ in range(actual_iterations):
        start = time.perf_counter()
        cursor = conn.execute(after_sql)
        rows = cursor.fetchall()
        elapsed = (time.perf_counter() - start) * 1000  # ms
        times_after.append(elapsed)
        rows_after = len(rows)

    # -- Statistiques ------------------------------------------------------
    mean_before = statistics.mean(times_before)
    mean_after = statistics.mean(times_after)
    std_before = statistics.stdev(times_before) if len(times_before) > 1 else 0.0
    std_after = statistics.stdev(times_after) if len(times_after) > 1 else 0.0
    speedup = mean_before / mean_after if mean_after > 0 else float("inf")

    # -- EXPLAIN QUERY PLAN ------------------------------------------------
    explain_before = _run_explain(conn, before_sql)
    explain_after = _run_explain(conn, after_sql)

    return BenchmarkResult(
        label=label,
        time_before_ms=round(mean_before, 2),
        time_after_ms=round(mean_after, 2),
        std_before_ms=round(std_before, 2),
        std_after_ms=round(std_after, 2),
        speedup=round(speedup, 1),
        rows_before=rows_before,
        rows_after=rows_after,
        iterations=actual_iterations,
        explain_before=explain_before,
        explain_after=explain_after,
    )


_cache: list[BenchmarkResult] = []


def get_cache() -> list[BenchmarkResult]:
    return list(_cache)


def clear_cache() -> None:
    global _cache
    _cache = []


def run_all_benchmarks(comparisons: list[dict], **kwargs) -> list[BenchmarkResult]:
    """Execute tous les benchmarks et met a jour le cache."""
    global _cache
    results = []
    for comp in comparisons:
        r = run_benchmark(
            before_sql=comp["before_sql"],
            after_sql=comp["after_sql"],
            label=comp["title"],
            **kwargs,
        )
        results.append(r)
    _cache = results
    return results


def _run_explain(conn, sql: str) -> list[str]:
    """Execute EXPLAIN QUERY PLAN et retourne les lignes detail."""
    try:
        rows = conn.execute(f"EXPLAIN QUERY PLAN {sql}").fetchall()
        if rows:
            return [row[-1] for row in rows]
        return ["(aucun plan)"]
    except sqlite3.Error as e:
        return [f"Erreur : {e}"]
