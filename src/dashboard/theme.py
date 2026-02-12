"""Thème — palette, CSS custom, templates graphiques."""

# ── Palette Olist (vert/or sur fond sombre) ──────────────────────────────
PRIMARY = "#00C853"       # vert vif
SECONDARY = "#FFD600"     # or
ACCENT = "#00E5FF"        # cyan accent
DANGER = "#FF5252"        # rouge alerte
BG_DARK = "#121212"
BG_CARD = "#1E1E1E"
TEXT_PRIMARY = "#E0E0E0"
TEXT_SECONDARY = "#9E9E9E"

# Couleurs séries graphiques
CHART_COLORS = [PRIMARY, SECONDARY, ACCENT, "#FF6D00", "#AA00FF", "#FF1744"]

# ── Templates graphiques ─────────────────────────────────────────────────
PLOTLY_TEMPLATE = "plotly_dark"
ECHARTS_THEME = "dark"

# ── CSS custom ───────────────────────────────────────────────────────────
CUSTOM_CSS = """
<style>
body {
    font-family: 'Inter', 'Roboto', sans-serif;
}
.sql-block {
    background: #1a1a2e;
    border-left: 3px solid #00C853;
    border-radius: 8px;
    font-size: 0.85rem;
}
.kpi-card {
    background: #1E1E1E;
    border-radius: 12px;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    border-left: 4px solid #00C853;
}
.kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 20px rgba(0, 200, 83, 0.15);
}
.kpi-value {
    font-size: 2rem;
    font-weight: 700;
    color: #00C853;
}
.kpi-label {
    font-size: 0.85rem;
    color: #9E9E9E;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.page-title {
    font-size: 1.5rem;
    font-weight: 600;
    color: #E0E0E0;
    margin-bottom: 0.5rem;
}
.sql-concepts {
    background: rgba(0, 200, 83, 0.08);
    border-radius: 8px;
    padding: 12px 16px;
    color: #9E9E9E;
    font-size: 0.85rem;
}
.narrative-block {
    background: rgba(255, 214, 0, 0.06);
    border-left: 3px solid #FFD600;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 16px;
    color: #E0E0E0;
    font-size: 0.9rem;
}
.insight-block {
    background: rgba(0, 229, 255, 0.06);
    border-left: 3px solid #00E5FF;
    border-radius: 8px;
    padding: 16px;
    margin-top: 12px;
    margin-bottom: 16px;
    color: #E0E0E0;
    font-size: 0.9rem;
    line-height: 1.6;
}

/* ── Styles spécifiques au cours SQL ────────────────────────────────── */

/* Éditeur SQL */
.sql-editor-container {
    background: #1a1a2e;
    border: 1px solid #333;
    border-radius: 12px;
    padding: 16px;
}

/* Annotations hover */
.sql-keyword-annotated {
    color: #00C853;
    text-decoration: underline dotted;
    cursor: help;
}

.sql-keyword-annotated:hover {
    background: rgba(0, 200, 83, 0.1);
    transition: background 0.2s ease;
}

/* Panel détails concept */
.concept-detail-panel {
    background: #1E1E1E;
    border-left: 3px solid #00E5FF;
    border-radius: 8px;
    padding: 16px;
}

/* Transitions chapitres */
.chapter-enter {
    animation: slideInRight 0.4s ease-out;
}

@keyframes slideInRight {
    from {
        transform: translateX(100px);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}

/* Code blocks gradient */
pre.sql-demo-block {
    background: linear-gradient(135deg, #1a1a2e, #16213e);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    border-radius: 8px;
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
}

/* Sidebar navigation */
.course-sidebar {
    background: #1E1E1E;
    border-right: 1px solid #333;
    overflow-y: auto;
}

.course-sidebar .lesson-item {
    padding: 8px 16px;
    cursor: pointer;
    transition: background 0.2s ease;
}

.course-sidebar .lesson-item:hover {
    background: rgba(0, 200, 83, 0.05);
}

.course-sidebar .lesson-item.active {
    background: #00C853;
    color: #000;
    font-weight: 600;
}

/* Progress bar */
.course-progress {
    height: 4px;
    background: #00C853;
    transition: width 0.3s ease;
}
</style>
"""
