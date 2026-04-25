"""
Eisenhower Matrix widget for Pomodoro app.

The classic 2×2 decision matrix:
  Q1 (red)    – Urgent   & Important   → Do First
  Q2 (blue)   – Not Urgent & Important → Schedule
  Q3 (orange) – Urgent   & Not Important → Delegate
  Q4 (gray)   – Not Urgent & Not Important → Eliminate
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QListWidget,
                             QListWidgetItem, QCheckBox, QGridLayout,
                             QFrame, QSizePolicy, QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from database import Database
from theme import COLORS


# ── Quadrant definitions ──────────────────────────────────────────────────────

QUADRANTS = {
    1: {
        "title":    "Do First",
        "subtitle": "Urgent & Important",
        "color":    "#ef4444",
        "bg":       "#fef2f2",
        "border":   "#fca5a5",
        "badge_bg": "#fee2e2",
    },
    2: {
        "title":    "Schedule",
        "subtitle": "Not Urgent & Important",
        "color":    "#0ea5e9",
        "bg":       "#f0f9ff",
        "border":   "#7dd3fc",
        "badge_bg": "#e0f2fe",
    },
    3: {
        "title":    "Delegate",
        "subtitle": "Urgent & Not Important",
        "color":    "#f59e0b",
        "bg":       "#fffbeb",
        "border":   "#fcd34d",
        "badge_bg": "#fef3c7",
    },
    4: {
        "title":    "Eliminate",
        "subtitle": "Not Urgent & Not Important",
        "color":    "#94a3b8",
        "bg":       "#f8fafc",
        "border":   "#cbd5e1",
        "badge_bg": "#f1f5f9",
    },
}


def _card_shadow():
    fx = QGraphicsDropShadowEffect()
    fx.setBlurRadius(16)
    fx.setXOffset(0)
    fx.setYOffset(3)
    fx.setColor(QColor(0, 0, 0, 20))
    return fx


# ── Single task row ───────────────────────────────────────────────────────────

class TaskItemWidget(QWidget):
    """One task row inside a quadrant list."""

    def __init__(self, task_id: int, task_text: str, completed: bool,
                 quadrant: int, parent_widget=None):
        super().__init__()
        self.task_id       = task_id
        self.quadrant      = quadrant
        self.parent_widget = parent_widget
        q = QUADRANTS[quadrant]

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(8)

        self.checkbox = QCheckBox()
        self.checkbox.setChecked(completed)
        self.checkbox.setStyleSheet(f"""
            QCheckBox::indicator {{
                width: 18px; height: 18px;
                border-radius: 9px;
                border: 2px solid {q['border']};
                background-color: {'white' if not completed else q['color']};
            }}
            QCheckBox::indicator:hover {{
                border-color: {q['color']};
            }}
        """)
        self.checkbox.stateChanged.connect(self._on_toggle)
        layout.addWidget(self.checkbox)

        self.label = QLabel(task_text)
        self.label.setWordWrap(True)
        self.label.setSizePolicy(QSizePolicy.Policy.Expanding,
                                 QSizePolicy.Policy.Preferred)
        lf = QFont()
        lf.setPointSize(12)
        self.label.setFont(lf)
        if completed:
            self.label.setStyleSheet(
                f"text-decoration: line-through; color: {COLORS['text_muted']};"
            )
        else:
            self.label.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(self.label, 1)

        del_btn = QPushButton("×")
        del_btn.setFixedSize(26, 26)
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1.5px solid {COLORS['border']};
                border-radius: 6px;
                color: {COLORS['text_muted']};
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {COLORS['danger']};
                border-color: {COLORS['danger']};
                color: white;
            }}
        """)
        del_btn.clicked.connect(self._on_delete)
        layout.addWidget(del_btn)

    def _on_toggle(self, state: int) -> None:
        completed = state == 2
        Database().update_eisenhower_task(self.task_id, completed=completed)
        if completed:
            self.label.setStyleSheet(
                f"text-decoration: line-through; color: {COLORS['text_muted']};"
            )
        else:
            q = QUADRANTS[self.quadrant]
            self.label.setStyleSheet(f"color: {COLORS['text']};")

    def _on_delete(self) -> None:
        Database().delete_eisenhower_task(self.task_id)
        if self.parent_widget:
            self.parent_widget.load_tasks()


# ── One quadrant ──────────────────────────────────────────────────────────────

class QuadrantWidget(QFrame):
    """Card widget representing a single Eisenhower quadrant."""

    def __init__(self, quadrant: int, parent_matrix=None):
        super().__init__()
        self.quadrant      = quadrant
        self.parent_matrix = parent_matrix
        self.db            = Database()
        q = QUADRANTS[quadrant]

        self.setFrameStyle(QFrame.Shape.NoFrame)
        self.setStyleSheet(f"""
            QuadrantWidget, QFrame {{
                background-color: {q['bg']};
                border: 1.5px solid {q['border']};
                border-radius: 12px;
            }}
        """)
        self.setGraphicsEffect(_card_shadow())

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)

        # Header row
        header_row = QHBoxLayout()
        badge = QLabel(q["title"])
        bf = QFont()
        bf.setPointSize(13)
        bf.setBold(True)
        badge.setFont(bf)
        badge.setStyleSheet(f"""
            color: {q['color']};
            background-color: {q['badge_bg']};
            border: 1px solid {q['border']};
            border-radius: 8px;
            padding: 3px 10px;
        """)
        header_row.addWidget(badge)
        header_row.addStretch()

        sub = QLabel(q["subtitle"])
        sf = QFont()
        sf.setPointSize(10)
        sub.setFont(sf)
        sub.setStyleSheet(f"color: {q['color']}; opacity: 0.8; border: none;")
        header_row.addWidget(sub)

        layout.addLayout(header_row)

        # Task list
        self.task_list = QListWidget()
        self.task_list.setStyleSheet(f"""
            QListWidget {{
                background-color: white;
                border: 1px solid {q['border']};
                border-radius: 8px;
                padding: 2px;
            }}
            QListWidget::item {{
                border-bottom: 1px solid {COLORS['border']};
                border-radius: 0px;
            }}
            QListWidget::item:last-child {{
                border-bottom: none;
            }}
            QListWidget::item:hover {{
                background-color: {q['bg']};
            }}
            QScrollBar:vertical {{
                width: 6px;
                background: transparent;
            }}
            QScrollBar::handle:vertical {{
                background: {COLORS['border']};
                border-radius: 3px;
                min-height: 30px;
            }}
        """)
        layout.addWidget(self.task_list, 1)

        # Input row
        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Add a task…")
        self.input_field.setMinimumHeight(36)
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                padding: 0 10px;
                border: 1.5px solid {q['border']};
                border-radius: 8px;
                background-color: white;
                color: {COLORS['text']};
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: {q['color']};
            }}
        """)
        self.input_field.returnPressed.connect(self._add_task)
        input_row.addWidget(self.input_field, 1)

        add_btn = QPushButton("+")
        add_btn.setFixedSize(36, 36)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {q['color']};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                opacity: 0.85;
            }}
        """)
        add_btn.clicked.connect(self._add_task)
        input_row.addWidget(add_btn)

        layout.addLayout(input_row)
        self.load_tasks()

    def _add_task(self) -> None:
        text = self.input_field.text().strip()
        if not text:
            return
        self.db.add_eisenhower_task(text, self.quadrant)
        self.input_field.clear()
        self.load_tasks()

    def load_tasks(self) -> None:
        self.task_list.clear()
        for task in self.db.get_eisenhower_tasks(self.quadrant):
            item   = QListWidgetItem()
            widget = TaskItemWidget(
                task_id=task["id"],
                task_text=task["task"],
                completed=bool(task["completed"]),
                quadrant=self.quadrant,
                parent_widget=self,
            )
            item.setSizeHint(widget.sizeHint())
            self.task_list.addItem(item)
            self.task_list.setItemWidget(item, widget)


# ── Main widget ───────────────────────────────────────────────────────────────

class EisenhowerMatrixWidget(QWidget):
    """The full 2×2 Eisenhower Matrix."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        self.setStyleSheet(f"QWidget {{ background-color: {COLORS['bg']}; }}")

        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # ── Header bar ────────────────────────────────────────────────────────
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        hb = QVBoxLayout(header)
        hb.setContentsMargins(28, 18, 28, 16)
        hb.setSpacing(4)

        title = QLabel("Eisenhower Matrix")
        tf = QFont()
        tf.setPointSize(22)
        tf.setBold(True)
        title.setFont(tf)
        title.setStyleSheet(f"color: {COLORS['text']};")
        hb.addWidget(title)

        subtitle = QLabel(
            "Prioritise tasks by urgency and importance. "
            "Do First → Schedule → Delegate → Eliminate."
        )
        subtitle.setStyleSheet(f"color: {COLORS['text_sec']}; font-size: 12px;")
        hb.addWidget(subtitle)

        root.addWidget(header)

        # ── Axis labels + grid ────────────────────────────────────────────────
        body = QVBoxLayout()
        body.setContentsMargins(16, 12, 16, 16)
        body.setSpacing(6)

        # Column labels (URGENT / NOT URGENT)
        col_labels = QHBoxLayout()
        col_labels.addSpacing(32)           # placeholder for row label column

        for txt, col in (("URGENT", QUADRANTS[1]["color"]),
                         ("NOT URGENT", QUADRANTS[2]["color"])):
            lbl = QLabel(txt)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                f"color: {col}; font-weight: 700; font-size: 11px; letter-spacing: 1px;"
            )
            col_labels.addWidget(lbl, 1)

        body.addLayout(col_labels)

        # Grid rows (with vertical IMPORTANT / NOT IMPORTANT labels on left)
        grid_row = QHBoxLayout()
        grid_row.setSpacing(0)

        # Vertical label column
        v_labels = QVBoxLayout()
        v_labels.setSpacing(0)
        for txt, col in (("IMPORTANT", QUADRANTS[2]["color"]),
                         ("NOT IMPORTANT", QUADRANTS[3]["color"])):
            lbl = QLabel()
            lbl.setText(txt)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                f"color: {col}; font-weight: 700; font-size: 10px; letter-spacing: 1px;"
            )
            # Rotate text 90°
            lbl.setFixedWidth(22)
            # PyQt6 doesn't support CSS transform; use a workaround via layout
            # We'll just use a narrow label — readable enough for short text
            v_labels.addWidget(lbl, 1)

        grid_row.addLayout(v_labels)

        grid = QGridLayout()
        grid.setSpacing(10)

        self.q1 = QuadrantWidget(1, self)
        self.q2 = QuadrantWidget(2, self)
        self.q3 = QuadrantWidget(3, self)
        self.q4 = QuadrantWidget(4, self)

        grid.addWidget(self.q1, 0, 0)
        grid.addWidget(self.q2, 0, 1)
        grid.addWidget(self.q3, 1, 0)
        grid.addWidget(self.q4, 1, 1)

        grid_row.addLayout(grid, 1)
        body.addLayout(grid_row, 1)
        root.addLayout(body, 1)

    def refresh(self) -> None:
        """Reload all four quadrants from the database."""
        for q in (self.q1, self.q2, self.q3, self.q4):
            q.load_tasks()
