"""
Todo list management widget for Pomodoro app.
Beautiful, modern card-based design.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QScrollArea, QFrame,
                             QCheckBox, QMessageBox, QDateEdit, QComboBox,
                             QDialog, QFormLayout, QDialogButtonBox,
                             QSizePolicy, QGraphicsDropShadowEffect,
                             QSpacerItem)
from PyQt6.QtCore import QDate, Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize
from PyQt6.QtGui import QFont, QColor, QIcon, QPixmap, QPainter
from datetime import datetime
from database import Database
from models import Todo


# ── Color Palette ─────────────────────────────────────────────────────────────
COLORS = {
    "bg":          "#f0f2f5",
    "card":        "#ffffff",
    "text":        "#1a1a2e",
    "text_sec":    "#6b7280",
    "accent":      "#6366f1",   # Indigo
    "accent_hover":"#4f46e5",
    "success":     "#10b981",   # Emerald
    "warning":     "#f59e0b",   # Amber
    "danger":      "#ef4444",   # Red
    "border":      "#e5e7eb",
    "input_bg":    "#f9fafb",
    "shadow":      "#00000018",
}

PRIORITY = {
    1: {"label": "Low",    "color": "#10b981", "bg": "#ecfdf5", "border": "#6ee7b7", "icon": "○"},
    2: {"label": "Medium", "color": "#f59e0b", "bg": "#fffbeb", "border": "#fcd34d", "icon": "◐"},
    3: {"label": "High",   "color": "#ef4444", "bg": "#fef2f2", "border": "#fca5a5", "icon": "●"},
}


def _shadow(blur=18, dx=0, dy=4, color=QColor(0, 0, 0, 25)):
    """Create a drop-shadow effect."""
    fx = QGraphicsDropShadowEffect()
    fx.setBlurRadius(blur)
    fx.setXOffset(dx)
    fx.setYOffset(dy)
    fx.setColor(color)
    return fx


# ── Edit / Add Dialog ─────────────────────────────────────────────────────────

class TodoEditDialog(QDialog):
    """Modern dialog for editing / adding a todo item."""
    
    def __init__(self, parent=None, todo: Todo = None):
        super().__init__(parent)
        self.todo = todo
        self.setWindowTitle("Edit Task" if todo else "New Task")
        self.setMinimumSize(460, 420)
        self.setStyleSheet(self._sheet())
        self._build(todo)

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build(self, todo):
        root = QVBoxLayout()
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # Header bar
        header = QFrame()
        header.setObjectName("dialogHeader")
        header.setFixedHeight(56)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(24, 0, 24, 0)
        title = QLabel("✏️  Edit Task" if todo else "✨  New Task")
        title.setObjectName("dialogTitle")
        hl.addWidget(title)
        root.addWidget(header)

        # Body
        body = QWidget()
        body.setObjectName("dialogBody")
        form = QFormLayout(body)
        form.setSpacing(16)
        form.setContentsMargins(28, 24, 28, 24)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Task input
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("What needs to be done?")
        self.task_input.setMinimumHeight(40)
        if todo:
            self.task_input.setText(todo.task)
        form.addRow("Task", self.task_input)
        
        # Date
        self.date_picker = QDateEdit()
        self.date_picker.setCalendarPopup(True)
        self.date_picker.setMinimumHeight(40)
        if todo:
            try:
                self.date_picker.setDate(QDate.fromString(todo.date, "yyyy-MM-dd"))
            except Exception:
                self.date_picker.setDate(QDate.currentDate())
        else:
            self.date_picker.setDate(QDate.currentDate())
        form.addRow("Date", self.date_picker)
        
        # Priority
        self.priority_combo = QComboBox()
        self.priority_combo.setMinimumHeight(40)
        for p in (1, 2, 3):
            self.priority_combo.addItem(f"{PRIORITY[p]['icon']}  {PRIORITY[p]['label']}")
        if todo:
            self.priority_combo.setCurrentIndex(todo.priority - 1)
        form.addRow("Priority", self.priority_combo)
        
        # Repeatable
        self.repeatable_check = QCheckBox("Enable")
        if todo:
            self.repeatable_check.setChecked(todo.is_repeatable)
        form.addRow("Repeat", self.repeatable_check)
        
        # Repeat type
        self.repeat_type_combo = QComboBox()
        self.repeat_type_combo.setMinimumHeight(40)
        self.repeat_type_combo.addItems(["Daily", "Weekly", "Monthly"])
        if todo and todo.repeat_type:
            idx = {"daily": 0, "weekly": 1, "monthly": 2}.get(todo.repeat_type.lower(), 0)
            self.repeat_type_combo.setCurrentIndex(idx)
        self.repeat_type_combo.setEnabled(self.repeatable_check.isChecked())
        self.repeatable_check.toggled.connect(self.repeat_type_combo.setEnabled)
        form.addRow("Frequency", self.repeat_type_combo)

        root.addWidget(body, 1)

        # Footer buttons
        footer = QFrame()
        footer.setObjectName("dialogFooter")
        footer.setFixedHeight(64)
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(24, 0, 24, 0)
        fl.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.setMinimumSize(100, 38)
        cancel_btn.clicked.connect(self.reject)
        fl.addWidget(cancel_btn)

        save_btn = QPushButton("Save Task" if self.todo else "Add Task")
        save_btn.setObjectName("saveBtn")
        save_btn.setMinimumSize(120, 38)
        save_btn.clicked.connect(self._validate_and_accept)
        fl.addWidget(save_btn)

        root.addWidget(footer)
        self.setLayout(root)

    def _validate_and_accept(self):
        if not self.task_input.text().strip():
            self.task_input.setFocus()
            self.task_input.setStyleSheet("border: 2px solid #ef4444;")
            return
        self.accept()

    # ── Data ──────────────────────────────────────────────────────────────────
    def get_todo_data(self):
        pri_map = {0: 1, 1: 2, 2: 3}
        rep_map = {0: "daily", 1: "weekly", 2: "monthly"}
        return {
            "task":          self.task_input.text().strip(),
            "date":          self.date_picker.date().toPyDate().strftime("%Y-%m-%d"),
            "priority":      pri_map[self.priority_combo.currentIndex()],
            "is_repeatable": self.repeatable_check.isChecked(),
            "repeat_type":   rep_map[self.repeat_type_combo.currentIndex()] if self.repeatable_check.isChecked() else "",
        }

    # ── Stylesheet ────────────────────────────────────────────────────────────
    @staticmethod
    def _sheet():
        return f"""
            QDialog {{
                background-color: {COLORS['bg']};
                border-radius: 12px;
            }}
            #dialogHeader {{
                background-color: {COLORS['accent']};
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }}
            #dialogTitle {{
                color: white;
                font-size: 16px;
                font-weight: bold;
            }}
            #dialogBody {{
                background-color: {COLORS['card']};
            }}
            QLabel {{
                color: {COLORS['text_sec']};
                font-size: 13px;
                font-weight: 600;
            }}
            QLineEdit, QDateEdit, QComboBox {{
                border: 1.5px solid {COLORS['border']};
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                background-color: {COLORS['input_bg']};
                color: {COLORS['text']};
            }}
            QLineEdit:focus, QDateEdit:focus, QComboBox:focus {{
                border-color: {COLORS['accent']};
            }}
            QCheckBox {{
                font-size: 13px;
                color: {COLORS['text']};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 20px; height: 20px;
                border-radius: 4px;
                border: 2px solid {COLORS['border']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLORS['accent']};
                border-color: {COLORS['accent']};
            }}
            #dialogFooter {{
                background-color: {COLORS['bg']};
                border-top: 1px solid {COLORS['border']};
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }}
            #cancelBtn {{
                background-color: transparent;
                border: 1.5px solid {COLORS['border']};
                border-radius: 8px;
                color: {COLORS['text_sec']};
                font-weight: 600;
                font-size: 13px;
            }}
            #cancelBtn:hover {{
                background-color: {COLORS['border']};
            }}
            #saveBtn {{
                background-color: {COLORS['accent']};
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: 600;
                font-size: 13px;
            }}
            #saveBtn:hover {{
                background-color: {COLORS['accent_hover']};
            }}
        """


# ── Single Todo Card ──────────────────────────────────────────────────────────

class TodoCard(QFrame):
    """A single todo item rendered as a card."""

    toggled  = pyqtSignal(int, bool)
    deleted  = pyqtSignal(int)
    edited   = pyqtSignal(int)

    def __init__(self, todo: Todo, parent=None):
        super().__init__(parent)
        self.todo = todo
        self.setObjectName("todoCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setGraphicsEffect(_shadow())
        self._build()

    def _build(self):
        pri = PRIORITY.get(self.todo.priority, PRIORITY[1])
        done = self.todo.completed

        self.setStyleSheet(f"""
            #todoCard {{
                background-color: {COLORS['card']};
                border-radius: 12px;
                border-left: 4px solid {pri['color'] if not done else COLORS['border']};
            }}
            #todoCard:hover {{
                border-left: 4px solid {COLORS['accent']};
            }}
        """)

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(14)

        # ── Checkbox ──────────────────────────────────────────────────────────
        self.cb = QCheckBox()
        self.cb.setChecked(done)
        self.cb.setStyleSheet(f"""
            QCheckBox::indicator {{
                width: 22px; height: 22px;
                border-radius: 11px;
                border: 2px solid {pri['color']};
                background-color: {"" + pri['color'] if done else "white"};
            }}
            QCheckBox::indicator:hover {{
                border-color: {COLORS['accent']};
            }}
        """)
        self.cb.stateChanged.connect(
            lambda s: self.toggled.emit(self.todo.id, s == Qt.CheckState.Checked.value)
        )
        root.addWidget(self.cb)

        # ── Content column ────────────────────────────────────────────────────
        col = QVBoxLayout()
        col.setSpacing(4)
        col.setContentsMargins(0, 0, 0, 0)

        # Task text
        self.task_lbl = QLabel(self.todo.task)
        fnt = QFont()
        fnt.setPointSize(13)
        fnt.setBold(not done)
        self.task_lbl.setFont(fnt)
        self.task_lbl.setWordWrap(True)
        if done:
            self.task_lbl.setStyleSheet(
                f"color: {COLORS['text_sec']}; text-decoration: line-through;"
            )
        else:
            self.task_lbl.setStyleSheet(f"color: {COLORS['text']};")
        col.addWidget(self.task_lbl)

        # Meta row: priority pill + date + repeat badge
        meta = QHBoxLayout()
        meta.setSpacing(8)
        meta.setContentsMargins(0, 2, 0, 0)

        # Priority pill
        pill = QLabel(f"  {pri['icon']}  {pri['label']}  ")
        pill.setStyleSheet(f"""
            background-color: {pri['bg']};
            color: {pri['color']};
            border: 1px solid {pri['border']};
            border-radius: 10px;
            font-size: 11px;
            font-weight: 600;
            padding: 2px 4px;
        """)
        pill.setFixedHeight(22)
        meta.addWidget(pill)

        # Date badge
        date_text, date_color = self._format_date()
        if date_text:
            date_lbl = QLabel(f"  {date_text}  ")
            date_lbl.setStyleSheet(f"""
                color: {date_color};
                font-size: 11px;
                font-weight: 500;
                padding: 2px 0px;
            """)
            date_lbl.setFixedHeight(22)
            meta.addWidget(date_lbl)

        # Repeat badge
        if self.todo.is_repeatable and self.todo.repeat_type:
            rpt_icons = {"daily": "↻ Daily", "weekly": "↻ Weekly", "monthly": "↻ Monthly"}
            rpt_text = rpt_icons.get(self.todo.repeat_type.lower(), "↻ Repeat")
            rpt_lbl = QLabel(f"  {rpt_text}  ")
            rpt_lbl.setStyleSheet(f"""
                background-color: #eef2ff;
                color: {COLORS['accent']};
                border: 1px solid #c7d2fe;
                border-radius: 10px;
                font-size: 11px;
                font-weight: 600;
                padding: 2px 4px;
            """)
            rpt_lbl.setFixedHeight(22)
            meta.addWidget(rpt_lbl)

        meta.addStretch()
        col.addLayout(meta)
        root.addLayout(col, 1)

        # ── Action buttons ────────────────────────────────────────────────────
        btn_col = QVBoxLayout()
        btn_col.setSpacing(4)
        btn_col.setContentsMargins(0, 0, 0, 0)

        edit_btn = QPushButton("✎")
        edit_btn.setToolTip("Edit task")
        edit_btn.setFixedSize(30, 30)
        edit_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1.5px solid {COLORS['border']};
                border-radius: 6px;
                color: {COLORS['text_sec']};
                font-size: 14px;
            }}
            QPushButton:hover {{
                background: {COLORS['accent']};
                border-color: {COLORS['accent']};
                color: white;
            }}
        """)
        edit_btn.clicked.connect(lambda: self.edited.emit(self.todo.id))
        btn_col.addWidget(edit_btn)

        del_btn = QPushButton("×")
        del_btn.setToolTip("Delete task")
        del_btn.setFixedSize(30, 30)
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1.5px solid {COLORS['border']};
                border-radius: 6px;
                color: {COLORS['text_sec']};
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {COLORS['danger']};
                border-color: {COLORS['danger']};
                color: white;
            }}
        """)
        del_btn.clicked.connect(lambda: self.deleted.emit(self.todo.id))
        btn_col.addWidget(del_btn)

        btn_col.addStretch()
        root.addLayout(btn_col)

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _format_date(self):
        try:
            d = datetime.strptime(self.todo.date, "%Y-%m-%d").date()
            today = datetime.now().date()
            if d == today:
                return "📅 Today", COLORS['accent']
            elif d < today:
                days = (today - d).days
                return f"⚠ {days}d overdue", COLORS['danger']
            else:
                days = (d - today).days
                if days == 1:
                    return "Tomorrow", COLORS['warning']
                elif days <= 7:
                    return f"In {days} days", COLORS['success']
                else:
                    return d.strftime("%b %d"), COLORS['text_sec']
        except Exception:
            return "", COLORS['text_sec']


# ── Main Widget ───────────────────────────────────────────────────────────────

class TodoListWidget(QWidget):
    """Beautiful todo-list widget with card-based layout."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = Database()
        self.active_filter = None  # None = all, date obj = specific date
        self._init_ui()
        self.db.handle_repeatable_todos()
        self._load_todos()
    
    # ── UI ────────────────────────────────────────────────────────────────────
    def _init_ui(self):
        self.setStyleSheet(f"background-color: {COLORS['bg']};")

        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # ── Top bar ───────────────────────────────────────────────────────────
        top_bar = QFrame()
        top_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        top_bar.setGraphicsEffect(_shadow(12, 0, 2, QColor(0, 0, 0, 15)))

        tb = QVBoxLayout(top_bar)
        tb.setSpacing(16)
        tb.setContentsMargins(28, 22, 28, 20)

        # Title row
        title_row = QHBoxLayout()
        title_lbl = QLabel("Tasks")
        tf = QFont()
        tf.setPointSize(22)
        tf.setBold(True)
        title_lbl.setFont(tf)
        title_lbl.setStyleSheet(f"color: {COLORS['text']};")
        title_row.addWidget(title_lbl)

        title_row.addStretch()

        # Counter badge
        self.counter_lbl = QLabel("0")
        self.counter_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.counter_lbl.setFixedSize(32, 32)
        self.counter_lbl.setStyleSheet(f"""
            background-color: {COLORS['accent']};
            color: white;
            border-radius: 16px;
                font-size: 13px;
            font-weight: bold;
        """)
        title_row.addWidget(self.counter_lbl)
        tb.addLayout(title_row)

        # Input row
        input_row = QHBoxLayout()
        input_row.setSpacing(10)

        self.todo_input = QLineEdit()
        self.todo_input.setPlaceholderText("What needs to be done?  Press Enter to add…")
        self.todo_input.setMinimumHeight(44)
        self.todo_input.setStyleSheet(f"""
            QLineEdit {{
                border: 2px solid {COLORS['border']};
                border-radius: 10px;
                padding: 0 16px;
                font-size: 14px;
                background-color: {COLORS['input_bg']};
                color: {COLORS['text']};
            }}
            QLineEdit:focus {{
                border-color: {COLORS['accent']};
                background-color: white;
            }}
        """)
        self.todo_input.returnPressed.connect(self._quick_add_todo)
        input_row.addWidget(self.todo_input, 1)

        add_btn = QPushButton("+ Add")
        add_btn.setMinimumSize(80, 44)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border: none;
                border-radius: 10px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_hover']};
            }}
        """)
        add_btn.clicked.connect(self._quick_add_todo)
        input_row.addWidget(add_btn)

        detail_btn = QPushButton("+ Detailed")
        detail_btn.setMinimumSize(100, 44)
        detail_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['accent']};
                border: 2px solid {COLORS['accent']};
                border-radius: 10px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent']};
                color: white;
            }}
        """)
        detail_btn.clicked.connect(self._add_todo_with_details)
        input_row.addWidget(detail_btn)

        tb.addLayout(input_row)

        # Filter chips
        chip_row = QHBoxLayout()
        chip_row.setSpacing(8)

        self.chip_all = self._make_chip("All", active=True)
        self.chip_all.clicked.connect(lambda: self._set_filter(None))
        chip_row.addWidget(self.chip_all)

        self.chip_today = self._make_chip("Today")
        self.chip_today.clicked.connect(lambda: self._set_filter(datetime.now().date()))
        chip_row.addWidget(self.chip_today)

        self.chip_active = self._make_chip("Active")
        self.chip_active.clicked.connect(lambda: self._set_filter("active"))
        chip_row.addWidget(self.chip_active)

        self.chip_done = self._make_chip("Done")
        self.chip_done.clicked.connect(lambda: self._set_filter("done"))
        chip_row.addWidget(self.chip_done)

        chip_row.addStretch()
        tb.addLayout(chip_row)

        root.addWidget(top_bar)

        # ── Scrollable card list ──────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {COLORS['bg']};
            }}
            QScrollBar:vertical {{
                width: 8px;
                background: transparent;
            }}
            QScrollBar::handle:vertical {{
                background: #c4c4c4;
                border-radius: 4px;
                min-height: 40px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: #a0a0a0;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)

        self.card_container = QWidget()
        self.card_container.setStyleSheet(f"background-color: {COLORS['bg']};")
        self.card_layout = QVBoxLayout(self.card_container)
        self.card_layout.setSpacing(10)
        self.card_layout.setContentsMargins(28, 16, 28, 28)
        self.card_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Empty state placeholder
        self.empty_label = QLabel("No tasks yet — add one above!")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(f"""
            color: {COLORS['text_sec']};
            font-size: 15px;
            padding: 60px 0;
        """)
        self.card_layout.addWidget(self.empty_label)

        scroll.setWidget(self.card_container)
        root.addWidget(scroll, 1)

    # ── Chip factory ──────────────────────────────────────────────────────────
    def _make_chip(self, text, active=False):
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setChecked(active)
        btn.setMinimumHeight(32)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent'] if active else 'transparent'};
                color: {'white' if active else COLORS['text_sec']};
                border: 1.5px solid {COLORS['accent'] if active else COLORS['border']};
                border-radius: 16px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent']};
                color: white;
                border-color: {COLORS['accent']};
            }}
            QPushButton:checked {{
                background-color: {COLORS['accent']};
                color: white;
                border-color: {COLORS['accent']};
            }}
        """)
        return btn

    def _update_chips(self):
        """Keep only the active chip checked."""
        chips = [self.chip_all, self.chip_today, self.chip_active, self.chip_done]
        for c in chips:
            c.setChecked(False)
            c.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLORS['text_sec']};
                    border: 1.5px solid {COLORS['border']};
                    border-radius: 16px;
                    padding: 0 16px;
                    font-size: 12px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['accent']};
                    color: white;
                    border-color: {COLORS['accent']};
                }}
                QPushButton:checked {{
                    background-color: {COLORS['accent']};
                    color: white;
                    border-color: {COLORS['accent']};
                }}
            """)

        target = {
            None:     self.chip_all,
            "active": self.chip_active,
            "done":   self.chip_done,
        }.get(self.active_filter if not isinstance(self.active_filter, type(datetime.now().date())) else "date", self.chip_today)

        if isinstance(self.active_filter, type(datetime.now().date())):
            target = self.chip_today

        target.setChecked(True)
        target.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border: 1.5px solid {COLORS['accent']};
                border-radius: 16px;
                padding: 0 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_hover']};
            }}
        """)

    # ── Data helpers ──────────────────────────────────────────────────────────
    def _set_filter(self, f):
        self.active_filter = f
        self._update_chips()
        self._load_todos()
    
    def _quick_add_todo(self):
        text = self.todo_input.text().strip()
        if not text:
            return
        date_str = QDate.currentDate().toPyDate().strftime("%Y-%m-%d")
        self.db.add_todo(text, date_str, priority=1, is_repeatable=False)
        self.todo_input.clear()
        self._load_todos()
    
    def _add_todo_with_details(self):
        dlg = TodoEditDialog(self)
        if dlg.exec():
            d = dlg.get_todo_data()
            self.db.add_todo(d["task"], d["date"],
                             priority=d["priority"],
                             is_repeatable=d["is_repeatable"],
                             repeat_type=d["repeat_type"])
            self._load_todos()
    
    def _load_todos(self, filter_date=None):
        # Clear current cards
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        f = filter_date or self.active_filter

        if isinstance(f, type(datetime.now().date())):
            todos = self.db.get_todos(f.strftime("%Y-%m-%d"))
        else:
            todos = self.db.get_todos()
        
        items = [Todo.from_dict(t) for t in todos]

        # Apply local filters
        if f == "active":
            items = [t for t in items if not t.completed]
        elif f == "done":
            items = [t for t in items if t.completed]

        # Update counter
        active_count = sum(1 for t in items if not t.completed)
        self.counter_lbl.setText(str(active_count))

        if not items:
            self.empty_label = QLabel("No tasks yet — add one above!")
            self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.empty_label.setStyleSheet(f"""
                color: {COLORS['text_sec']};
                font-size: 15px;
                padding: 60px 0;
            """)
            self.card_layout.addWidget(self.empty_label)
            return

        for todo in items:
            card = TodoCard(todo, self)
            card.toggled.connect(self._on_toggle)
            card.deleted.connect(self._on_delete)
            card.edited.connect(self._on_edit)
            self.card_layout.addWidget(card)

        # Push remaining space to bottom
        self.card_layout.addStretch()

    # ── Callbacks ─────────────────────────────────────────────────────────────
    def _on_toggle(self, todo_id, completed):
        self.db.update_todo(todo_id, completed=completed)
        if completed:
            self.db.handle_repeatable_todos()
        self._load_todos()
    
    def _on_delete(self, todo_id):
        reply = QMessageBox.question(
            self, "Delete Task",
            "Are you sure you want to delete this task?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_todo(todo_id)
            self._load_todos()
    
    def _on_edit(self, todo_id):
        todos = self.db.get_todos()
        data = next((t for t in todos if t["id"] == todo_id), None)
        if not data:
            return
        todo = Todo.from_dict(data)
        dlg = TodoEditDialog(self, todo)
        if dlg.exec():
            d = dlg.get_todo_data()
            self.db.update_todo(todo_id,
                                task=d["task"],
                                priority=d["priority"],
                                is_repeatable=d["is_repeatable"],
                                repeat_type=d["repeat_type"])
            self._load_todos()
    
    def _filter_todos(self, filter_date):
        """Legacy compat — called from elsewhere."""
        self._set_filter(filter_date)
