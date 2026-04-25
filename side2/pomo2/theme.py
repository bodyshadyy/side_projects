"""Shared design system for the Pomodoro app.

Import COLORS, get_colors(), and helpers from here instead of hard-coding hex
values in individual widgets.  Call apply_theme(dark=True/False) once at
startup (before any widgets are constructed) to switch between light and dark.
"""
import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Light palette
# ---------------------------------------------------------------------------

_LIGHT = {
    # Backgrounds
    "bg":           "#f0f2f5",
    "surface":      "#ffffff",
    "surface_alt":  "#f8faff",

    # Borders / dividers
    "border":       "#e2e8f0",

    # Text
    "text":         "#1e293b",
    "text_sec":     "#64748b",
    "text_muted":   "#94a3b8",

    # Accent – indigo
    "accent":        "#6366f1",
    "accent_hover":  "#4f46e5",
    "accent_pressed":"#3730a3",
    "accent_light":  "#eef2ff",
    "accent_border": "#c7d2fe",

    # Work / Focus – red
    "work":         "#ef4444",
    "work_bg":      "#fef2f2",
    "work_border":  "#fca5a5",

    # Short break – sky blue
    "short_break":         "#0ea5e9",
    "short_break_bg":      "#f0f9ff",
    "short_break_border":  "#7dd3fc",

    # Long break – emerald
    "long_break":          "#10b981",
    "long_break_bg":       "#ecfdf5",
    "long_break_border":   "#6ee7b7",

    # Downtime – violet
    "downtime":        "#8b5cf6",
    "downtime_bg":     "#f5f3ff",
    "downtime_border": "#ddd6fe",

    # Generic status colours
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger":  "#ef4444",

    # Inputs
    "input_bg": "#f9fafb",

    # Schedule extras
    "fixed_bg":        "#fef3c7",
    "fixed_border":    "#fcd34d",
    "relative_bg":     "#ecfdf5",
    "relative_border": "#6ee7b7",
    "wake_bg":         "#ede9fe",
    "wake_border":     "#c4b5fd",
    "timeline":        "#6366f1",

    # Card shadow (used in QGraphicsDropShadowEffect via helper)
    "shadow_alpha": "25",
}

# ---------------------------------------------------------------------------
# Dark palette
# ---------------------------------------------------------------------------

_DARK = {
    "bg":           "#0f172a",
    "surface":      "#1e293b",
    "surface_alt":  "#1a2741",

    "border":       "#334155",

    "text":         "#f1f5f9",
    "text_sec":     "#94a3b8",
    "text_muted":   "#64748b",

    "accent":        "#818cf8",
    "accent_hover":  "#6366f1",
    "accent_pressed":"#4f46e5",
    "accent_light":  "#1e1b4b",
    "accent_border": "#3730a3",

    "work":         "#f87171",
    "work_bg":      "#1c0a0a",
    "work_border":  "#991b1b",

    "short_break":         "#38bdf8",
    "short_break_bg":      "#082f49",
    "short_break_border":  "#075985",

    "long_break":          "#34d399",
    "long_break_bg":       "#022c22",
    "long_break_border":   "#065f46",

    "downtime":        "#a78bfa",
    "downtime_bg":     "#1e1b4b",
    "downtime_border": "#4c1d95",

    "success": "#34d399",
    "warning": "#fbbf24",
    "danger":  "#f87171",

    "input_bg": "#1e293b",

    "fixed_bg":        "#292524",
    "fixed_border":    "#78350f",
    "relative_bg":     "#022c22",
    "relative_border": "#065f46",
    "wake_bg":         "#1e1b4b",
    "wake_border":     "#4c1d95",
    "timeline":        "#818cf8",

    "shadow_alpha": "60",
}

# ---------------------------------------------------------------------------
# Active palette (mutable – updated by apply_theme)
# ---------------------------------------------------------------------------

COLORS: dict[str, str] = dict(_LIGHT)


# ---------------------------------------------------------------------------
# Per-state bundles: (foreground, background, border)
# ---------------------------------------------------------------------------

def _build_state_colors() -> dict[str, tuple[str, str, str]]:
    return {
        "work": (COLORS["work"], COLORS["work_bg"], COLORS["work_border"]),
        "short_break": (COLORS["short_break"], COLORS["short_break_bg"], COLORS["short_break_border"]),
        "long_break": (COLORS["long_break"], COLORS["long_break_bg"], COLORS["long_break_border"]),
        "downtime": (COLORS["downtime"], COLORS["downtime_bg"], COLORS["downtime_border"]),
        "paused": (COLORS["text_sec"], COLORS["surface_alt"], COLORS["border"]),
    }


STATE_COLORS: dict[str, tuple[str, str, str]] = _build_state_colors()


def get_state_color(state_name: str) -> str:
    return STATE_COLORS.get(state_name, STATE_COLORS["paused"])[0]


def get_state_bundle(state_name: str) -> tuple[str, str, str]:
    return STATE_COLORS.get(state_name, STATE_COLORS["paused"])


# ---------------------------------------------------------------------------
# Theme management
# ---------------------------------------------------------------------------

def _pref_path() -> Path:
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir / "theme_pref.json"


def is_dark_mode() -> bool:
    try:
        p = _pref_path()
        if p.exists():
            return bool(json.loads(p.read_text()).get("dark", False))
    except Exception:
        pass
    return False


def save_theme_pref(dark: bool) -> None:
    _pref_path().write_text(json.dumps({"dark": dark}))


def apply_theme(dark: bool = False) -> None:
    """Update COLORS and STATE_COLORS in-place so all widgets pick up the theme.

    Must be called before any widget is constructed.
    """
    global STATE_COLORS
    source = _DARK if dark else _LIGHT
    COLORS.update(source)
    STATE_COLORS = _build_state_colors()


# Apply saved preference immediately when module is imported.
apply_theme(is_dark_mode())


# ---------------------------------------------------------------------------
# Shared stylesheet snippets
# ---------------------------------------------------------------------------

SCROLLBAR_STYLE = f"""
    QScrollBar:vertical {{
        width: 8px;
        background: transparent;
    }}
    QScrollBar::handle:vertical {{
        background: {COLORS['border']};
        border-radius: 4px;
        min-height: 40px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {COLORS['text_muted']};
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0;
    }}
"""

BUTTON_BASE_STYLE = f"""
    QPushButton {{
        background-color: {COLORS['accent']};
        color: white;
        border: none;
        border-radius: 8px;
        padding: 9px 18px;
        font-weight: 600;
        font-size: 13px;
    }}
    QPushButton:hover {{
        background-color: {COLORS['accent_hover']};
    }}
    QPushButton:pressed {{
        background-color: {COLORS['accent_pressed']};
    }}
    QPushButton:disabled {{
        background-color: {COLORS['border']};
        color: {COLORS['text_muted']};
    }}
"""


def build_app_stylesheet() -> str:
    """Return a top-level QApplication stylesheet covering common widgets."""
    C = COLORS
    return f"""
        QWidget {{
            background-color: {C['bg']};
            color: {C['text']};
            font-family: -apple-system, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
        }}
        QMainWindow, QDialog {{
            background-color: {C['bg']};
        }}
        QScrollArea {{
            border: none;
            background-color: {C['bg']};
        }}
        QScrollBar:vertical {{
            width: 8px;
            background: transparent;
        }}
        QScrollBar::handle:vertical {{
            background: {C['border']};
            border-radius: 4px;
            min-height: 40px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {C['text_muted']};
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{ height: 0; }}
        QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTimeEdit, QDateEdit {{
            background-color: {C['input_bg']};
            color: {C['text']};
            border: 1.5px solid {C['border']};
            border-radius: 8px;
            padding: 6px 10px;
            selection-background-color: {C['accent']};
        }}
        QLineEdit:focus, QTextEdit:focus, QSpinBox:focus,
        QDoubleSpinBox:focus, QComboBox:focus, QTimeEdit:focus, QDateEdit:focus {{
            border-color: {C['accent']};
            background-color: {C['surface']};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        QComboBox QAbstractItemView {{
            background-color: {C['surface']};
            color: {C['text']};
            border: 1px solid {C['border']};
            selection-background-color: {C['accent_light']};
            selection-color: {C['accent']};
        }}
        QCheckBox {{
            spacing: 8px;
            color: {C['text']};
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 4px;
            border: 2px solid {C['border']};
            background-color: {C['input_bg']};
        }}
        QCheckBox::indicator:checked {{
            background-color: {C['accent']};
            border-color: {C['accent']};
        }}
        QCheckBox::indicator:hover {{
            border-color: {C['accent']};
        }}
        QLabel {{
            background: transparent;
            color: {C['text']};
        }}
        QGroupBox {{
            border: 1px solid {C['border']};
            border-radius: 10px;
            margin-top: 14px;
            background-color: {C['surface']};
            font-weight: 700;
            padding-top: 10px;
            color: {C['text']};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            color: {C['text_sec']};
        }}
        QStatusBar {{
            background-color: {C['surface']};
            border-top: 1px solid {C['border']};
            color: {C['text_sec']};
            font-size: 12px;
        }}
        QMenuBar {{
            background-color: {C['surface']};
            border-bottom: 1px solid {C['border']};
            color: {C['text']};
        }}
        QMenuBar::item {{
            padding: 7px 14px;
            background: transparent;
        }}
        QMenuBar::item:selected {{
            background-color: {C['accent_light']};
            color: {C['accent']};
            border-radius: 4px;
        }}
        QMenu {{
            background-color: {C['surface']};
            border: 1px solid {C['border']};
            border-radius: 8px;
            padding: 4px;
            color: {C['text']};
        }}
        QMenu::item {{
            padding: 8px 24px;
            border-radius: 4px;
        }}
        QMenu::item:selected {{
            background-color: {C['accent_light']};
            color: {C['accent']};
        }}
        QMenu::separator {{
            height: 1px;
            background: {C['border']};
            margin: 4px 8px;
        }}
        QTabWidget::pane {{
            border: 1px solid {C['border']};
            background-color: {C['surface']};
            border-bottom-left-radius: 8px;
            border-bottom-right-radius: 8px;
        }}
        QTabBar::tab {{
            background-color: {C['surface_alt']};
            color: {C['text_sec']};
            padding: 10px 20px;
            margin-right: 2px;
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            border: 1px solid {C['border']};
            border-bottom: none;
            font-weight: 600;
            font-size: 13px;
        }}
        QTabBar::tab:selected {{
            background-color: {C['accent']};
            color: white;
            border-color: {C['accent']};
        }}
        QTabBar::tab:hover:!selected {{
            background-color: {C['accent_light']};
            color: {C['accent']};
            border-color: {C['accent_border']};
        }}
        QTabBar::tab:disabled {{
            color: {C['text_muted']};
            background-color: {C['border']};
        }}
        QToolTip {{
            background-color: {C['surface']};
            color: {C['text']};
            border: 1px solid {C['border']};
            border-radius: 4px;
            padding: 4px 8px;
        }}
        QMessageBox {{
            background-color: {C['surface']};
        }}
        QCalendarWidget QTableView {{
            selection-background-color: {C['accent']};
            selection-color: white;
            background-color: {C['surface']};
            gridline-color: {C['border']};
        }}
        QCalendarWidget QAbstractItemView:enabled {{
            color: {C['text']};
            selection-background-color: {C['accent']};
            selection-color: white;
        }}
        QCalendarWidget QAbstractItemView:disabled {{
            color: {C['text_muted']};
        }}
    """
