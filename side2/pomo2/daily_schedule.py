"""
Daily Schedule widget for Pomodoro app.
Shows a timeline of tasks computed from wake-up time.
Tasks can be relative (minutes after wake-up) or fixed (exact clock time).
Fixed-time tasks take priority — relative tasks that would overlap are delayed.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QScrollArea, QFrame,
                             QCheckBox, QMessageBox, QSpinBox, QTimeEdit,
                             QDialog, QFormLayout, QComboBox,
                             QGraphicsDropShadowEffect, QSizePolicy)
from PyQt6.QtCore import Qt, QTime, QTimer
from PyQt6.QtGui import QFont, QColor
from datetime import datetime, timedelta
import json
from pathlib import Path
from database import Database
from models import ScheduleTask
from theme import COLORS as _THEME_COLORS

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    Request = None
    Credentials = None
    InstalledAppFlow = None
    build = None
    HttpError = Exception

GOOGLE_CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

# Use the centralized theme palette; add local aliases for convenience.
COLORS = dict(_THEME_COLORS)
COLORS.setdefault("card", COLORS["surface"])


def _shadow(blur=18, dx=0, dy=4, color=QColor(0, 0, 0, 25)):
    fx = QGraphicsDropShadowEffect()
    fx.setBlurRadius(blur)
    fx.setXOffset(dx)
    fx.setYOffset(dy)
    fx.setColor(color)
    return fx


# ── Schedule Task Edit Dialog ─────────────────────────────────────────────────

class ScheduleTaskDialog(QDialog):
    """Dialog for adding / editing a schedule task."""

    def __init__(self, parent=None, task: ScheduleTask = None, available_tasks=None):
        super().__init__(parent)
        self.task_data = task
        self.available_tasks = available_tasks or []
        self.setWindowTitle("Edit Schedule Task" if task else "New Schedule Task")
        self.setMinimumSize(460, 400)
        self.setStyleSheet(self._sheet())
        self._build(task)

    def _build(self, task):
        root = QVBoxLayout()
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QFrame()
        header.setObjectName("dialogHeader")
        header.setFixedHeight(56)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(24, 0, 24, 0)
        title = QLabel("✏️  Edit Task" if task else "📋  New Schedule Task")
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

        # Task name
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText("e.g. Morning routine, Work, Exercise…")
        self.task_input.setMinimumHeight(40)
        if task:
            self.task_input.setText(task.task)
        form.addRow("Task", self.task_input)

        # Time type
        self.time_type_combo = QComboBox()
        self.time_type_combo.setMinimumHeight(40)
        self.time_type_combo.addItems(["Auto Sequence", "Fixed Time"])
        if task and task.is_fixed_time:
            self.time_type_combo.setCurrentIndex(1)
        self.time_type_combo.currentIndexChanged.connect(self._toggle_time_inputs)
        form.addRow("Time Type", self.time_type_combo)

        # ── Relative task fields ──────────────────────────────────────────────
        # Break before this task: hours + minutes
        self.offset_widget = QWidget()
        offset_layout = QHBoxLayout(self.offset_widget)
        offset_layout.setContentsMargins(0, 0, 0, 0)
        offset_layout.setSpacing(8)

        self.offset_hours_spin = QSpinBox()
        self.offset_hours_spin.setRange(0, 23)
        self.offset_hours_spin.setSuffix(" h")
        self.offset_hours_spin.setMinimumHeight(40)

        self.offset_mins_spin = QSpinBox()
        self.offset_mins_spin.setRange(0, 59)
        self.offset_mins_spin.setSuffix(" m")
        self.offset_mins_spin.setMinimumHeight(40)

        if task and not task.is_fixed_time:
            self.offset_hours_spin.setValue(task.offset_minutes // 60)
            self.offset_mins_spin.setValue(task.offset_minutes % 60)

        offset_layout.addWidget(self.offset_hours_spin)
        offset_layout.addWidget(self.offset_mins_spin)
        offset_layout.addStretch()
        form.addRow("Break Before", self.offset_widget)

        # Duration (for relative tasks)
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(5, 480)
        self.duration_spin.setSuffix(" min")
        self.duration_spin.setMinimumHeight(40)
        self.duration_spin.setValue(task.duration_minutes if task else 30)
        form.addRow("Duration", self.duration_spin)

        # ── Fixed time fields ─────────────────────────────────────────────────
        # Start time
        self.time_start_edit = QTimeEdit()
        self.time_start_edit.setDisplayFormat("hh:mm AP")
        self.time_start_edit.setMinimumHeight(40)
        if task and task.fixed_time:
            try:
                self.time_start_edit.setTime(QTime.fromString(task.fixed_time, "HH:mm"))
            except Exception:
                self.time_start_edit.setTime(QTime(9, 0))
        else:
            self.time_start_edit.setTime(QTime(9, 0))
        form.addRow("Start Time", self.time_start_edit)

        # End time
        self.time_end_edit = QTimeEdit()
        self.time_end_edit.setDisplayFormat("hh:mm AP")
        self.time_end_edit.setMinimumHeight(40)
        if task and task.fixed_time_end:
            try:
                self.time_end_edit.setTime(QTime.fromString(task.fixed_time_end, "HH:mm"))
            except Exception:
                self.time_end_edit.setTime(QTime(17, 0))
        else:
            self.time_end_edit.setTime(QTime(17, 0))
        form.addRow("End Time", self.time_end_edit)

        # Store form-row labels for toggling visibility
        self.offset_label = form.labelForField(self.offset_widget)
        self.duration_label = form.labelForField(self.duration_spin)
        self.start_label = form.labelForField(self.time_start_edit)
        self.end_label = form.labelForField(self.time_end_edit)
        self._toggle_time_inputs(self.time_type_combo.currentIndex())

        root.addWidget(body, 1)

        # Footer
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

        save_btn = QPushButton("Save" if self.task_data else "Add Task")
        save_btn.setObjectName("saveBtn")
        save_btn.setMinimumSize(120, 38)
        save_btn.clicked.connect(self._validate_and_accept)
        fl.addWidget(save_btn)

        root.addWidget(footer)
        self.setLayout(root)

    def _toggle_time_inputs(self, idx):
        is_fixed = idx == 1
        # Break-before field applies only to auto-sequence tasks.
        self.offset_widget.setVisible(not is_fixed)
        self.duration_spin.setVisible(not is_fixed)
        if self.offset_label:
            self.offset_label.setVisible(not is_fixed)
        if self.duration_label:
            self.duration_label.setVisible(not is_fixed)
        # Fixed fields
        self.time_start_edit.setVisible(is_fixed)
        self.time_end_edit.setVisible(is_fixed)
        if self.start_label:
            self.start_label.setVisible(is_fixed)
        if self.end_label:
            self.end_label.setVisible(is_fixed)

    def _validate_and_accept(self):
        if not self.task_input.text().strip():
            self.task_input.setFocus()
            self.task_input.setStyleSheet("border: 2px solid #ef4444;")
            return
        self.accept()

    def get_data(self) -> dict:
        is_fixed = self.time_type_combo.currentIndex() == 1
        offset_total = self.offset_hours_spin.value() * 60 + self.offset_mins_spin.value()
        return {
            "task": self.task_input.text().strip(),
            "duration_minutes": self.duration_spin.value() if not is_fixed else 0,
            "is_fixed_time": is_fixed,
            "fixed_time": self.time_start_edit.time().toString("HH:mm") if is_fixed else "",
            "fixed_time_end": self.time_end_edit.time().toString("HH:mm") if is_fixed else "",
            "offset_minutes": offset_total if not is_fixed else 0,
            "anchor_type": "wake_up",
            "anchor_task_id": None,
        }

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
                color: white; font-size: 16px; font-weight: bold;
            }}
            #dialogBody {{
                background-color: {COLORS['card']};
            }}
            QLabel {{
                color: {COLORS['text_sec']}; font-size: 13px; font-weight: 600;
            }}
            QLineEdit, QSpinBox, QTimeEdit, QComboBox {{
                border: 1.5px solid {COLORS['border']};
                border-radius: 8px; padding: 8px 12px; font-size: 13px;
                background-color: {COLORS['input_bg']}; color: {COLORS['text']};
            }}
            QLineEdit:focus, QSpinBox:focus, QTimeEdit:focus, QComboBox:focus {{
                border-color: {COLORS['accent']};
            }}
            #dialogFooter {{
                background-color: {COLORS['bg']};
                border-top: 1px solid {COLORS['border']};
            }}
            #cancelBtn {{
                background-color: transparent;
                border: 1.5px solid {COLORS['border']}; border-radius: 8px;
                color: {COLORS['text_sec']}; font-weight: 600; font-size: 13px;
            }}
            #cancelBtn:hover {{ background-color: {COLORS['border']}; }}
            #saveBtn {{
                background-color: {COLORS['accent']}; border: none; border-radius: 8px;
                color: white; font-weight: 600; font-size: 13px;
            }}
            #saveBtn:hover {{ background-color: {COLORS['accent_hover']}; }}
        """


# ── Schedule Card ─────────────────────────────────────────────────────────────

class ScheduleCard(QFrame):
    """A single schedule task rendered as a timeline card."""

    def __init__(self, task: ScheduleTask, computed_time: str = "",
                 computed_end: str = "",
                 anchor_label: str = "wake-up",
                 is_current: bool = False, parent=None):
        super().__init__(parent)
        self.task = task
        self.computed_time = computed_time
        self.computed_end = computed_end
        self.anchor_label = anchor_label
        self.is_current = is_current
        self.setObjectName("scheduleCard")
        self.setGraphicsEffect(_shadow())
        self._build()

    def _build(self):
        t = self.task
        is_fixed = t.is_fixed_time

        border_color = COLORS['fixed_border'] if is_fixed else COLORS['relative_border']
        if self.is_current:
            border_color = COLORS['accent']

        self.setStyleSheet(f"""
            #scheduleCard {{
                background-color: {COLORS['card']};
                border-radius: 12px;
                border-left: 4px solid {border_color};
            }}
            #scheduleCard:hover {{
                border-left: 4px solid {COLORS['accent']};
            }}
        """)

        root = QHBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(14)

        # Time column
        time_col = QVBoxLayout()
        time_col.setSpacing(2)
        time_col.setContentsMargins(0, 0, 0, 0)

        start_str = self.computed_time if self.computed_time else "—"
        time_lbl = QLabel(start_str)
        tf = QFont()
        tf.setPointSize(14)
        tf.setBold(True)
        time_lbl.setFont(tf)
        time_lbl.setStyleSheet(f"color: {COLORS['accent']};")
        time_lbl.setFixedWidth(90)
        time_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        time_col.addWidget(time_lbl)

        # Show end time underneath
        if self.computed_end:
            end_lbl = QLabel(f"to {self.computed_end}")
            end_lbl.setStyleSheet(f"color: {COLORS['text_sec']}; font-size: 11px;")
            end_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            end_lbl.setFixedWidth(90)
            time_col.addWidget(end_lbl)

        root.addLayout(time_col)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet(f"color: {COLORS['border']};")
        root.addWidget(sep)

        # Content column
        col = QVBoxLayout()
        col.setSpacing(4)

        task_lbl = QLabel(t.task)
        nf = QFont()
        nf.setPointSize(13)
        nf.setBold(True)
        task_lbl.setFont(nf)
        task_lbl.setWordWrap(True)
        task_lbl.setStyleSheet(f"color: {COLORS['text']};")
        col.addWidget(task_lbl)

        # Type badge
        badge_row = QHBoxLayout()
        badge_row.setSpacing(8)

        if is_fixed:
            badge = QLabel(f"  ⏰  Fixed {t.fixed_time} – {t.fixed_time_end}  ")
            badge.setStyleSheet(f"""
                background-color: {COLORS['fixed_bg']};
                color: {COLORS['warning']};
                border: 1px solid {COLORS['fixed_border']};
                border-radius: 10px; font-size: 11px; font-weight: 600; padding: 2px 4px;
            """)
        else:
            hours = t.offset_minutes // 60
            mins = t.offset_minutes % 60
            parts = []
            if hours:
                parts.append(f"{hours}h")
            if mins or not hours:
                parts.append(f"{mins}m")
            break_str = " ".join(parts)
            badge = QLabel(f"  🌅  Break {break_str}  ·  {t.duration_minutes} min  ")
            badge.setStyleSheet(f"""
                background-color: {COLORS['relative_bg']};
                color: {COLORS['success']};
                border: 1px solid {COLORS['relative_border']};
                border-radius: 10px; font-size: 11px; font-weight: 600; padding: 2px 4px;
            """)

        badge.setFixedHeight(22)
        badge_row.addWidget(badge)

        if self.is_current:
            now_badge = QLabel("  ▶ NOW  ")
            now_badge.setStyleSheet(f"""
                background-color: {COLORS['accent']};
                color: white;
                border-radius: 10px; font-size: 11px; font-weight: 700; padding: 2px 8px;
            """)
            now_badge.setFixedHeight(22)
            badge_row.addWidget(now_badge)

        badge_row.addStretch()
        col.addLayout(badge_row)

        root.addLayout(col, 1)

        # Action buttons
        btn_col = QVBoxLayout()
        btn_col.setSpacing(4)

        self.edit_btn = QPushButton("✎")
        self.edit_btn.setToolTip("Edit")
        self.edit_btn.setFixedSize(30, 30)
        self.edit_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: 1.5px solid {COLORS['border']};
                border-radius: 6px; color: {COLORS['text_sec']}; font-size: 14px;
            }}
            QPushButton:hover {{
                background: {COLORS['accent']}; border-color: {COLORS['accent']}; color: white;
            }}
        """)
        btn_col.addWidget(self.edit_btn)

        self.del_btn = QPushButton("×")
        self.del_btn.setToolTip("Delete")
        self.del_btn.setFixedSize(30, 30)
        self.del_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; border: 1.5px solid {COLORS['border']};
                border-radius: 6px; color: {COLORS['text_sec']}; font-size: 16px; font-weight: bold;
            }}
            QPushButton:hover {{
                background: {COLORS['danger']}; border-color: {COLORS['danger']}; color: white;
            }}
        """)
        btn_col.addWidget(self.del_btn)
        btn_col.addStretch()

        root.addLayout(btn_col)


# ── Main Widget ───────────────────────────────────────────────────────────────

class DailyScheduleWidget(QWidget):
    """Daily schedule widget with wake-up button and timeline."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = Database()
        self.wake_time = None       # datetime or None
        self.schedule_options = self._load_schedule_options()
        self._init_ui()
        self._try_load_today_wakeup()
        self._load_schedule()

        # Refresh "NOW" marker every 60 seconds
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._load_schedule)
        self._refresh_timer.start(60_000)

    # ── UI ────────────────────────────────────────────────────────────────────
    def _init_ui(self):
        self.setStyleSheet(f"background-color: {COLORS['bg']};")
        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # Top bar
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
        title_lbl = QLabel("Daily Schedule")
        tf = QFont()
        tf.setPointSize(22)
        tf.setBold(True)
        title_lbl.setFont(tf)
        title_lbl.setStyleSheet(f"color: {COLORS['text']};")
        title_row.addWidget(title_lbl)
        title_row.addStretch()

        # Wake-up info label
        self.wake_info_lbl = QLabel("")
        self.wake_info_lbl.setStyleSheet(f"""
            color: {COLORS['accent']}; font-size: 14px; font-weight: 600;
        """)
        title_row.addWidget(self.wake_info_lbl)

        tb.addLayout(title_row)

        # Wake-up + Add buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.wake_btn = QPushButton("☀️  I'm Awake!")
        self.wake_btn.setMinimumSize(160, 48)
        self.wake_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['wake_bg']};
                color: {COLORS['accent']};
                border: 2px solid {COLORS['wake_border']};
                border-radius: 12px; font-size: 15px; font-weight: 700;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent']};
                color: white; border-color: {COLORS['accent']};
            }}
        """)
        self.wake_btn.clicked.connect(self._on_wake_up)
        btn_row.addWidget(self.wake_btn)

        # Bedtime routine options
        self.bedtime_check = QCheckBox("🌙 Bedtime routine")
        self.bedtime_check.setChecked(bool(self.schedule_options.get("include_bedtime_routine", False)))
        self.bedtime_check.stateChanged.connect(self._on_schedule_options_changed)
        btn_row.addWidget(self.bedtime_check)

        awake_lbl = QLabel("Awake:")
        awake_lbl.setStyleSheet(f"color: {COLORS['text_sec']}; font-weight: 600;")
        btn_row.addWidget(awake_lbl)

        self.awake_hours_spin = QSpinBox()
        self.awake_hours_spin.setRange(8, 20)
        self.awake_hours_spin.setValue(int(self.schedule_options.get("awake_hours", 16)))
        self.awake_hours_spin.setSuffix(" h")
        self.awake_hours_spin.setMinimumHeight(36)
        self.awake_hours_spin.valueChanged.connect(self._on_schedule_options_changed)
        btn_row.addWidget(self.awake_hours_spin)

        btn_row.addStretch()

        gcal_btn = QPushButton("📅  Google Calendar")
        gcal_btn.setMinimumSize(180, 44)
        gcal_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #ffffff; color: #1a73e8;
                border: 2px solid #1a73e8; border-radius: 10px;
                font-size: 14px; font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #1a73e8; color: white;
            }}
        """)
        gcal_btn.clicked.connect(self._export_to_google_calendar)
        btn_row.addWidget(gcal_btn)

        add_btn = QPushButton("+ Add Task")
        add_btn.setMinimumSize(120, 44)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']}; color: white;
                border: none; border-radius: 10px; font-size: 14px; font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {COLORS['accent_hover']}; }}
        """)
        add_btn.clicked.connect(self._add_task)
        btn_row.addWidget(add_btn)

        tb.addLayout(btn_row)

        root.addWidget(top_bar)

        # Scrollable timeline
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none; background-color: {COLORS['bg']};
            }}
            QScrollBar:vertical {{
                width: 8px; background: transparent;
            }}
            QScrollBar::handle:vertical {{
                background: #c4c4c4; border-radius: 4px; min-height: 40px;
            }}
            QScrollBar::handle:vertical:hover {{ background: #a0a0a0; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)

        self.card_container = QWidget()
        self.card_container.setStyleSheet(f"background-color: {COLORS['bg']};")
        self.card_layout = QVBoxLayout(self.card_container)
        self.card_layout.setSpacing(10)
        self.card_layout.setContentsMargins(28, 16, 28, 28)
        self.card_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        scroll.setWidget(self.card_container)
        root.addWidget(scroll, 1)

    def _schedule_options_path(self) -> Path:
        data_dir = Path(__file__).parent / "data"
        data_dir.mkdir(exist_ok=True)
        return data_dir / "schedule_options.json"

    def _load_schedule_options(self) -> dict:
        defaults = {
            "include_bedtime_routine": False,
            "awake_hours": 16
        }
        path = self._schedule_options_path()
        if not path.exists():
            with open(path, "w", encoding="utf-8") as f:
                json.dump(defaults, f, indent=2)
            return defaults
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f) or {}
            if not isinstance(loaded, dict):
                return defaults
            merged = defaults.copy()
            merged.update(loaded)
            return merged
        except Exception:
            return defaults

    def _save_schedule_options(self):
        with open(self._schedule_options_path(), "w", encoding="utf-8") as f:
            json.dump(self.schedule_options, f, indent=2)

    def _on_schedule_options_changed(self):
        self.schedule_options["include_bedtime_routine"] = self.bedtime_check.isChecked()
        self.schedule_options["awake_hours"] = self.awake_hours_spin.value()
        self._save_schedule_options()
        self._load_schedule()

    def _build_bedtime_windows(self, wake: datetime):
        """Return synthetic bedtime routine windows."""
        if not self.schedule_options.get("include_bedtime_routine", False):
            return []

        awake_hours = max(8, min(20, int(self.schedule_options.get("awake_hours", 16))))
        sleep_start = wake + timedelta(hours=awake_hours)
        sleep_end = sleep_start + timedelta(hours=8)

        bedtime_steps = [
            ("🧹 Tidy + Prepare Tomorrow", 30),
            ("📵 Wind Down (No Screens)", 30),
        ]
        total_before = sum(minutes for _, minutes in bedtime_steps)
        cursor = sleep_start - timedelta(minutes=total_before)
        windows = []
        for title, duration in bedtime_steps:
            start = cursor
            end = start + timedelta(minutes=duration)
            t = ScheduleTask(
                id=None,
                task=title,
                duration_minutes=duration,
                is_fixed_time=True,
                fixed_time=start.strftime("%H:%M"),
                fixed_time_end=end.strftime("%H:%M"),
                offset_minutes=0,
                anchor_type="wake_up",
                anchor_task_id=None,
                sort_order=10_000 + len(windows),
            )
            windows.append((t, start, end))
            cursor = end

        sleep_task = ScheduleTask(
            id=None,
            task="😴 Sleep",
            duration_minutes=int((sleep_end - sleep_start).total_seconds() // 60),
            is_fixed_time=True,
            fixed_time=sleep_start.strftime("%H:%M"),
            fixed_time_end=sleep_end.strftime("%H:%M"),
            offset_minutes=0,
            anchor_type="wake_up",
            anchor_task_id=None,
            sort_order=10_100,
        )
        windows.append((sleep_task, sleep_start, sleep_end))
        return windows

    # ── Wake-up ───────────────────────────────────────────────────────────────
    def _try_load_today_wakeup(self):
        today = datetime.now().strftime("%Y-%m-%d")
        saved = self.db.get_wakeup_time(today)
        if saved:
            try:
                h, m = map(int, saved.split(":"))
                now = datetime.now()
                self.wake_time = now.replace(hour=h, minute=m, second=0, microsecond=0)
                self._update_wake_label()
            except Exception:
                self.wake_time = None

    def _on_wake_up(self):
        now = datetime.now()
        self.wake_time = now.replace(second=0, microsecond=0)
        today = now.strftime("%Y-%m-%d")
        self.db.set_wakeup_time(today, self.wake_time.strftime("%H:%M"))
        self._update_wake_label()
        self._load_schedule()

    def _update_wake_label(self):
        if self.wake_time:
            t = self.wake_time.strftime("%I:%M %p")
            self.wake_info_lbl.setText(f"🌅 Woke up at {t}")
            self.wake_btn.setText(f"☀️  Woke up at {t}")
            self.wake_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['success']};
                    color: white;
                    border: 2px solid {COLORS['success']};
                    border-radius: 12px; font-size: 15px; font-weight: 700;
                }}
                QPushButton:hover {{
                    background-color: #059669;
                    border-color: #059669;
                }}
            """)
        else:
            self.wake_info_lbl.setText("")

    # ── Schedule Computation ──────────────────────────────────────────────────
    def _get_fixed_end(self, t, start_dt):
        """Return the end datetime for a fixed-time task."""
        if t.fixed_time_end:
            try:
                h, m = map(int, t.fixed_time_end.split(":"))
                end_same_day = start_dt.replace(hour=h, minute=m, second=0, microsecond=0)
                if end_same_day > start_dt:
                    return end_same_day

                # Heuristic for entries like "10 to 5" where end may mean 5 PM.
                # Choose the nearest valid future interpretation.
                candidates = []
                if h < 12:
                    plus_12 = end_same_day + timedelta(hours=12)
                    if plus_12 > start_dt:
                        candidates.append(plus_12)
                plus_24 = end_same_day + timedelta(days=1)
                if plus_24 > start_dt:
                    candidates.append(plus_24)
                if candidates:
                    return min(candidates, key=lambda dt: dt - start_dt)
                return end_same_day
            except Exception:
                pass
        # Fallback: use duration_minutes if end time missing
        return start_dt + timedelta(minutes=max(t.duration_minutes, 30))

    def _anchor_label_for_task(self, task: ScheduleTask, tasks_by_id: dict) -> str:
        """Legacy placeholder for card signature; anchors are no longer user-configurable."""
        return "previous task"

    def _compute_times(self, tasks):
        """
        Compute the actual start time for each task.

        Rules:
        1. Fixed-time tasks always keep their specified start/end time.
        2. Non-fixed tasks are scheduled sequentially in sort order.
        3. Each non-fixed task starts after:
           - the previous non-fixed task ends
           - plus its configured break (offset_minutes)
        4. Tasks are pushed forward to avoid overlap with fixed-time windows.

        Returns a list of (task, computed_start_str, computed_end_str, anchor_label, is_current).
        """
        if not self.wake_time or not tasks:
            return [(t, "", "", "wake-up", False) for t in tasks]

        wake = self.wake_time
        now = datetime.now()
        tasks_by_id = {t.id: t for t in tasks if t.id is not None}

        # First pass: fixed tasks reserve their exact time windows.
        scheduled = {}  # task_id -> (occupied_start_dt, occupied_end_dt)
        occupied_windows = []
        fixed_entries = []
        for t in tasks:
            if not (t.is_fixed_time and t.fixed_time):
                continue
            try:
                h, m = map(int, t.fixed_time.split(":"))
                start = wake.replace(hour=h, minute=m, second=0)
            except Exception:
                start = wake
            end_dt = self._get_fixed_end(t, start)
            if end_dt <= start:
                end_dt = start + timedelta(minutes=30)
            occupied_start = start
            occupied_end = end_dt
            fixed_entries.append((t, start, end_dt))
            occupied_windows.append((occupied_start, occupied_end))
            if t.id is not None:
                scheduled[t.id] = (occupied_start, occupied_end)

        # Synthetic end-of-day routine + sleep block.
        for t, start, end_dt in self._build_bedtime_windows(wake):
            fixed_entries.append((t, start, end_dt))
            occupied_windows.append((start, end_dt))

        # Non-fixed tasks are a simple sequence.
        sequential_tasks = [t for t in tasks if not t.is_fixed_time]
        sequential_tasks.sort(key=lambda x: (x.sort_order, x.id or 0))
        resolved_relative = []

        def _all_windows():
            windows = list(occupied_windows)
            windows.sort(key=lambda w: w[0])
            return windows

        cursor_dt = wake
        for t in sequential_tasks:
            dur = max(1, t.duration_minutes)
            break_minutes = max(0, int(t.offset_minutes or 0))
            proposed_start = cursor_dt + timedelta(minutes=break_minutes)
            proposed_end = proposed_start + timedelta(minutes=dur)
            windows = _all_windows()
            changed = True
            while changed:
                changed = False
                for win_start, win_end in windows:
                    if proposed_start < win_end and proposed_end > win_start:
                        # Keep the configured break even when a fixed task blocks the slot.
                        proposed_start = win_end + timedelta(minutes=break_minutes)
                        proposed_end = proposed_start + timedelta(minutes=dur)
                        changed = True
                if changed:
                    windows = _all_windows()
            if t.id is not None:
                scheduled[t.id] = (proposed_start, proposed_end)
            occupied_windows.append((proposed_start, proposed_end))
            resolved_relative.append((t, proposed_start, proposed_end))
            cursor_dt = proposed_end

        # Combine and sort all tasks by computed start
        resolved = []
        for t, s, e in fixed_entries:
            resolved.append((t, s, e))
        resolved.extend(resolved_relative)
        resolved.sort(key=lambda r: r[1])

        # Build result with formatted strings
        result = []
        for t, start, end in resolved:
            is_current = (start <= now < end)
            start_str = start.strftime("%I:%M %p").lstrip("0")
            end_str = end.strftime("%I:%M %p").lstrip("0")
            anchor_label = self._anchor_label_for_task(t, tasks_by_id)
            result.append((t, start_str, end_str, anchor_label, is_current))

        return result

    # ── Load / Refresh ────────────────────────────────────────────────────────
    def _load_schedule(self):
        # Clear cards
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        tasks_raw = self.db.get_schedule_tasks()
        tasks = [ScheduleTask.from_dict(d) for d in tasks_raw]

        if not tasks:
            empty = QLabel("No schedule tasks yet — add one above!")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setStyleSheet(f"""
                color: {COLORS['text_sec']}; font-size: 15px; padding: 60px 0;
            """)
            self.card_layout.addWidget(empty)
            return

        computed = self._compute_times(tasks)

        for task, time_str, end_str, anchor_label, is_current in computed:
            card = ScheduleCard(task, time_str, end_str, anchor_label, is_current, parent=self)
            card.edit_btn.clicked.connect(lambda checked, tid=task.id: self._edit_task(tid))
            card.del_btn.clicked.connect(lambda checked, tid=task.id: self._delete_task(tid))
            self.card_layout.addWidget(card)

        self.card_layout.addStretch()

    # ── CRUD Actions ──────────────────────────────────────────────────────────
    def _add_task(self):
        existing_tasks = self.db.get_schedule_tasks()
        dlg = ScheduleTaskDialog(self, available_tasks=existing_tasks)
        if dlg.exec():
            d = dlg.get_data()
            self.db.add_schedule_task(
                task=d["task"],
                duration_minutes=d["duration_minutes"],
                is_fixed_time=d["is_fixed_time"],
                fixed_time=d["fixed_time"],
                fixed_time_end=d["fixed_time_end"],
                offset_minutes=d["offset_minutes"],
                anchor_type=d["anchor_type"],
                anchor_task_id=d["anchor_task_id"],
            )
            self._load_schedule()

    def _edit_task(self, task_id):
        tasks_raw = self.db.get_schedule_tasks()
        data = next((t for t in tasks_raw if t["id"] == task_id), None)
        if not data:
            return
        task = ScheduleTask.from_dict(data)
        dlg = ScheduleTaskDialog(self, task, available_tasks=tasks_raw)
        if dlg.exec():
            d = dlg.get_data()
            self.db.update_schedule_task(
                task_id,
                task=d["task"],
                duration_minutes=d["duration_minutes"],
                is_fixed_time=d["is_fixed_time"],
                fixed_time=d["fixed_time"],
                fixed_time_end=d["fixed_time_end"],
                offset_minutes=d["offset_minutes"],
                anchor_type=d["anchor_type"],
                anchor_task_id=d["anchor_task_id"],
            )
            self._load_schedule()

    def _delete_task(self, task_id):
        reply = QMessageBox.question(
            self, "Delete Task",
            "Are you sure you want to delete this schedule task?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.delete_schedule_task(task_id)
            self._load_schedule()

    # ── Google Calendar Export ─────────────────────────────────────────────────
    def _generate_ics(self, computed):
        """
        Generate an .ics (iCalendar) file from the computed schedule.
        Returns the file path.
        """
        today = datetime.now().date()
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Pomodoro App//Daily Schedule//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
        ]

        tasks_by_id = {t["id"]: ScheduleTask.from_dict(t) for t in self.db.get_schedule_tasks() if t.get("id") is not None}

        for task, start_str, end_str, _anchor_label, _is_current in computed:
            # Parse start/end strings back to datetime for ICS format
            # start_str is like "9:00 AM", end_str is like "5:00 PM"
            try:
                start_dt = datetime.strptime(
                    f"{today.strftime('%Y-%m-%d')} {start_str}",
                    "%Y-%m-%d %I:%M %p"
                )
                end_dt = datetime.strptime(
                    f"{today.strftime('%Y-%m-%d')} {end_str}",
                    "%Y-%m-%d %I:%M %p"
                )
            except ValueError:
                continue

            dtstart = start_dt.strftime("%Y%m%dT%H%M%S")
            dtend = end_dt.strftime("%Y%m%dT%H%M%S")
            uid = f"{dtstart}-{task.task.replace(' ', '')}@pomodoro-app"

            desc = self._build_event_description(task, tasks_by_id)

            lines += [
                "BEGIN:VEVENT",
                f"DTSTART:{dtstart}",
                f"DTEND:{dtend}",
                f"SUMMARY:{task.task}",
                f"DESCRIPTION:{desc}",
                f"UID:{uid}",
                "STATUS:CONFIRMED",
                "END:VEVENT",
            ]

        lines.append("END:VCALENDAR")

        # Write to a file in the app data directory
        from pathlib import Path
        data_dir = Path(__file__).parent / "data"
        data_dir.mkdir(exist_ok=True)
        ics_path = str(data_dir / f"schedule_{today.strftime('%Y%m%d')}.ics")

        with open(ics_path, "w", encoding="utf-8") as f:
            f.write("\r\n".join(lines))

        return ics_path

    def _get_google_calendar_paths(self):
        """Return all local Google Calendar integration file paths."""
        data_dir = Path(__file__).parent / "data"
        data_dir.mkdir(exist_ok=True)
        default_client_secret = data_dir / "google_client_secret.json"
        detected_client_secret = default_client_secret

        if not default_client_secret.exists():
            # Accept standard Google download names so users can drop the file as-is.
            candidates = sorted(data_dir.glob("client_secret*.json"))
            if not candidates:
                candidates = sorted(data_dir.glob("*apps.googleusercontent.com*.json"))
            if candidates:
                detected_client_secret = candidates[0]

        return {
            "data_dir": data_dir,
            "client_secret": detected_client_secret,
            "default_client_secret": default_client_secret,
            "token": data_dir / "google_token.json",
            "config": data_dir / "google_calendar_config.json",
        }

    def _load_google_calendar_config(self, paths):
        """
        Load optional Google Calendar config.
        Creates a template file if it does not exist.
        """
        default_cfg = {
            "calendar_id": "primary",
        }
        config_path = paths["config"]
        if not config_path.exists():
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(default_cfg, f, indent=2)
            return default_cfg
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f) or {}
            if not isinstance(loaded, dict):
                return default_cfg
            cfg = default_cfg.copy()
            cfg.update(loaded)
            return cfg
        except Exception:
            return default_cfg

    def _build_event_description(self, task, tasks_by_id):
        """Build event description text for Google Calendar and ICS."""
        if task.is_fixed_time:
            return f"Fixed time: {task.fixed_time} - {task.fixed_time_end}"

        h = task.offset_minutes // 60
        m = task.offset_minutes % 60
        return f"Break before task: {h}h {m}m, duration: {task.duration_minutes} min"

    def _build_google_calendar_payloads(self, computed):
        """Convert computed rows into Google Calendar API event payloads."""
        today = datetime.now().date()
        local_tz = datetime.now().astimezone().tzinfo
        payloads = []
        tasks_by_id = {
            t["id"]: ScheduleTask.from_dict(t)
            for t in self.db.get_schedule_tasks()
            if t.get("id") is not None
        }

        for task, start_str, end_str, _anchor_label, _is_current in computed:
            try:
                start_dt = datetime.strptime(
                    f"{today.strftime('%Y-%m-%d')} {start_str}",
                    "%Y-%m-%d %I:%M %p"
                )
                end_dt = datetime.strptime(
                    f"{today.strftime('%Y-%m-%d')} {end_str}",
                    "%Y-%m-%d %I:%M %p"
                )
            except ValueError:
                continue

            if end_dt <= start_dt:
                end_dt += timedelta(days=1)
            if local_tz:
                start_dt = start_dt.replace(tzinfo=local_tz)
                end_dt = end_dt.replace(tzinfo=local_tz)

            payloads.append({
                "summary": task.task,
                "description": self._build_event_description(task, tasks_by_id),
                "start": {"dateTime": start_dt.isoformat()},
                "end": {"dateTime": end_dt.isoformat()},
            })

        return payloads

    def _get_google_calendar_credentials(self, paths):
        """Load/refresh OAuth credentials or run consent flow."""
        creds = None
        token_path = paths["token"]
        client_secret_path = paths["client_secret"]

        if token_path.exists():
            creds = Credentials.from_authorized_user_file(
                str(token_path), GOOGLE_CALENDAR_SCOPES
            )

        if creds and creds.valid:
            return creds

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not client_secret_path.exists():
                raise FileNotFoundError(str(client_secret_path))
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secret_path), GOOGLE_CALENDAR_SCOPES
            )
            creds = flow.run_local_server(port=0)

        with open(token_path, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

        return creds

    def _show_google_calendar_setup_help(self, paths):
        """Show one-time setup instructions for Google Calendar API."""
        msg = (
            "Google Calendar API setup required.\n\n"
            "1) In Google Cloud Console, enable the Google Calendar API.\n"
            "2) Create OAuth client credentials for a Desktop app.\n"
            "3) Download the JSON credentials file.\n"
            f"4) Save it as:\n{paths['default_client_secret']}\n"
            "5) Click 'Google Calendar' again and approve access in the browser.\n\n"
            "Optional:\n"
            f"- Set a custom calendar ID in:\n{paths['config']}\n"
            '  Example: {"calendar_id": "primary"}\n\n'
            "If you prefer, you can still use the .ics fallback import now."
        )
        QMessageBox.information(self, "Google Calendar API Setup", msg)

    def _export_to_google_calendar(self):
        """Add today's computed schedule directly using Google Calendar API."""
        if not self.wake_time:
            QMessageBox.warning(
                self, "No Wake-Up Time",
                "Please press 'I'm Awake!' first so the schedule times can be computed."
            )
            return

        tasks_raw = self.db.get_schedule_tasks()
        tasks = [ScheduleTask.from_dict(d) for d in tasks_raw]

        if not tasks:
            QMessageBox.warning(
                self, "No Tasks",
                "Add some schedule tasks first before exporting."
            )
            return

        computed = self._compute_times(tasks)
        if not all([Request, Credentials, InstalledAppFlow, build]):
            QMessageBox.warning(
                self,
                "Google API Packages Missing",
                "Google Calendar API packages are not installed.\n\n"
                "Run:\n"
                "pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib\n\n"
                "Then restart the app and click Google Calendar again."
            )
            return

        paths = self._get_google_calendar_paths()
        self._load_google_calendar_config(paths)  # Ensures config template exists.
        try:
            cfg = self._load_google_calendar_config(paths)
            creds = self._get_google_calendar_credentials(paths)
            service = build("calendar", "v3", credentials=creds)

            payloads = self._build_google_calendar_payloads(computed)
            if not payloads:
                QMessageBox.warning(
                    self, "Nothing to Export",
                    "No valid schedule times were found to send to Google Calendar."
                )
                return

            calendar_id = cfg.get("calendar_id", "primary")
            inserted = 0
            for payload in payloads:
                service.events().insert(calendarId=calendar_id, body=payload).execute()
                inserted += 1

            QMessageBox.information(
                self, "Google Calendar Updated",
                f"Added {inserted} event(s) to calendar '{calendar_id}'."
            )
        except FileNotFoundError:
            self._show_google_calendar_setup_help(paths)
        except HttpError as e:
            QMessageBox.critical(
                self,
                "Google Calendar API Error",
                f"Google Calendar API request failed:\n{e}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Google Calendar Error",
                f"Could not add events via API:\n{e}"
            )

