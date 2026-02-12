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

/* Intro navigation sticky footer (presentation slides) */
.intro-nav-footer {
    position: fixed !important;
    bottom: 0;
    left: 0;
    right: 0;
    width: 100%;
    max-width: 100%;
    margin: 0;
    padding: 16px 40px;
    background: rgba(18, 18, 18, 0.85);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    z-index: 1000;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 -4px 20px rgba(0, 0, 0, 0.3);
}

.intro-home-shell {
    padding-bottom: 96px !important;
}

.intro-nav-footer .q-btn {
    border-radius: 10px !important;
    padding: 10px 24px !important;
    font-size: 15px !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px;
    min-height: 44px;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    text-transform: none !important;
}

.intro-nav-footer .q-btn--standard.bg-primary {
    background: linear-gradient(135deg, #2196F3, #1976D2) !important;
    box-shadow: 0 4px 14px rgba(33, 150, 243, 0.35);
}

.intro-nav-footer .q-btn--standard.bg-primary:hover {
    background: linear-gradient(135deg, #42A5F5, #2196F3) !important;
    box-shadow: 0 6px 20px rgba(33, 150, 243, 0.5);
    transform: translateY(-1px);
}

.intro-nav-footer .q-btn--outline {
    border: 1.5px solid rgba(255, 255, 255, 0.2) !important;
    color: rgba(255, 255, 255, 0.8) !important;
    background: rgba(255, 255, 255, 0.04) !important;
}

.intro-nav-footer .q-btn--outline:hover {
    border-color: rgba(255, 255, 255, 0.4) !important;
    background: rgba(255, 255, 255, 0.08) !important;
    transform: translateY(-1px);
}

.intro-nav-footer .q-btn--standard.bg-positive {
    background: linear-gradient(135deg, #4CAF50, #2E7D32) !important;
    box-shadow: 0 4px 14px rgba(76, 175, 80, 0.35);
}

.intro-nav-footer .q-btn--standard.bg-positive:hover {
    background: linear-gradient(135deg, #66BB6A, #4CAF50) !important;
    box-shadow: 0 6px 20px rgba(76, 175, 80, 0.5);
    transform: translateY(-1px);
}

.intro-nav-footer .q-btn .q-focus-helper {
    display: none !important;
}

@media (max-width: 640px) {
    .intro-nav-footer {
        padding: 12px 14px;
    }

    .intro-home-shell {
        padding-bottom: 104px !important;
    }

    .intro-nav-footer .q-btn {
        padding: 8px 14px !important;
        font-size: 14px !important;
    }
}
</style>
"""
