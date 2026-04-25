"""
Calendar and daily notes widget for Pomodoro app.

Select any date on the calendar to view or edit the note for that day.
Notes are saved automatically 1.5 seconds after you stop typing (debounced
auto-save).  Ctrl+S triggers an immediate save.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QCalendarWidget, QTextEdit, QPushButton, QFrame,
                              QGraphicsDropShadowEffect)
from PyQt6.QtCore import QDate, Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QKeySequence, QShortcut
from datetime import datetime
from database import Database
from theme import COLORS


def _shadow(blur=16, dy=3, alpha=20):
    fx = QGraphicsDropShadowEffect()
    fx.setBlurRadius(blur)
    fx.setXOffset(0)
    fx.setYOffset(dy)
    fx.setColor(QColor(0, 0, 0, alpha))
    return fx


class CalendarNotesWidget(QWidget):
    """Calendar picker + free-text note editor for each day."""

    _AUTOSAVE_DELAY_MS = 1500   # debounce delay for auto-save

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db           = Database()
        self.current_date = datetime.now().date()
        self._dirty       = False

        # Debounce timer — fires once typing stops.
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._autosave)

        self._init_ui()
        self._load_note_for_date()

    # ── UI construction ───────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        self.setStyleSheet(f"QWidget {{ background-color: {COLORS['bg']}; }}")

        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # ── Top bar ───────────────────────────────────────────────────────────
        top_bar = QFrame()
        top_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        top_bar.setGraphicsEffect(_shadow())
        tb = QVBoxLayout(top_bar)
        tb.setContentsMargins(28, 20, 28, 18)
        tb.setSpacing(4)

        title = QLabel("Daily Notes")
        tf = QFont()
        tf.setPointSize(22)
        tf.setBold(True)
        title.setFont(tf)
        title.setStyleSheet(f"color: {COLORS['text']};")
        tb.addWidget(title)

        subtitle = QLabel(
            "One note per day — saved automatically as you type.  Ctrl+S to save immediately."
        )
        subtitle.setStyleSheet(f"color: {COLORS['text_sec']}; font-size: 12px;")
        tb.addWidget(subtitle)

        root.addWidget(top_bar)

        # ── Body ──────────────────────────────────────────────────────────────
        body = QHBoxLayout()
        body.setSpacing(0)
        body.setContentsMargins(0, 0, 0, 0)

        # Left: calendar
        left_pane = QWidget()
        left_pane.setFixedWidth(300)
        left_pane.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['surface']};
                border-right: 1px solid {COLORS['border']};
            }}
        """)
        lp = QVBoxLayout(left_pane)
        lp.setContentsMargins(18, 18, 18, 18)
        lp.setSpacing(12)

        self.calendar = QCalendarWidget()
        self.calendar.setSelectedDate(QDate.currentDate())
        self.calendar.setVerticalHeaderFormat(
            QCalendarWidget.VerticalHeaderFormat.NoVerticalHeader
        )
        self.calendar.setStyleSheet(f"""
            QCalendarWidget {{
                background-color: {COLORS['surface']};
            }}
            QCalendarWidget QTableView {{
                selection-background-color: {COLORS['accent']};
                selection-color: white;
                background-color: {COLORS['surface']};
                gridline-color: {COLORS['border']};
            }}
            QCalendarWidget QAbstractItemView:enabled {{
                color: {COLORS['text']};
                selection-background-color: {COLORS['accent']};
                selection-color: white;
            }}
            QCalendarWidget QAbstractItemView:disabled {{
                color: {COLORS['text_muted']};
            }}
            QCalendarWidget QToolButton {{
                background-color: transparent;
                color: {COLORS['text']};
                font-weight: bold;
                border-radius: 4px;
                padding: 4px;
            }}
            QCalendarWidget QToolButton:hover {{
                background-color: {COLORS['accent_light']};
                color: {COLORS['accent']};
            }}
            QCalendarWidget QMenu {{
                background-color: {COLORS['surface']};
            }}
            #qt_calendar_navigationbar {{
                background-color: {COLORS['accent_light']};
                border-radius: 8px;
                margin: 4px;
            }}
        """)
        self.calendar.selectionChanged.connect(self._on_date_selected)
        lp.addWidget(self.calendar)
        lp.addStretch()

        body.addWidget(left_pane)

        # Right: note editor
        right_pane = QWidget()
        right_pane.setStyleSheet(f"background-color: {COLORS['bg']};")
        rp = QVBoxLayout(right_pane)
        rp.setContentsMargins(24, 20, 24, 20)
        rp.setSpacing(14)

        # Date header
        self.date_label = QLabel()
        df = QFont()
        df.setPointSize(16)
        df.setBold(True)
        self.date_label.setFont(df)
        self.date_label.setStyleSheet(f"""
            color: {COLORS['accent']};
            background-color: {COLORS['accent_light']};
            border: 1px solid {COLORS['accent_border']};
            border-radius: 8px;
            padding: 8px 14px;
        """)
        self._update_date_label()
        rp.addWidget(self.date_label)

        # Notes header row (label + save status)
        notes_header_row = QHBoxLayout()
        notes_header = QLabel("Notes")
        nhf = QFont()
        nhf.setPointSize(13)
        nhf.setBold(True)
        notes_header.setFont(nhf)
        notes_header.setStyleSheet(f"color: {COLORS['text_sec']};")
        notes_header_row.addWidget(notes_header)
        notes_header_row.addStretch()

        self.save_status = QLabel("")
        self.save_status.setStyleSheet(f"color: {COLORS['success']}; font-size: 12px;")
        notes_header_row.addWidget(self.save_status)
        rp.addLayout(notes_header_row)

        # Note editor
        self.notes_editor = QTextEdit()
        self.notes_editor.setPlaceholderText(
            "Write anything here — goals, reflections, highlights…"
        )
        self.notes_editor.setStyleSheet(f"""
            QTextEdit {{
                border: 1.5px solid {COLORS['border']};
                border-radius: 10px;
                padding: 12px;
                font-size: 13px;
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                line-height: 1.5;
            }}
            QTextEdit:focus {{
                border-color: {COLORS['accent']};
                background-color: {COLORS['surface']};
            }}
        """)
        self.notes_editor.textChanged.connect(self._on_text_changed)
        rp.addWidget(self.notes_editor, 1)

        body.addWidget(right_pane, 1)
        root.addLayout(body, 1)

        # Ctrl+S shortcut for immediate save
        save_shortcut = QShortcut(QKeySequence("Ctrl+S"), self.notes_editor)
        save_shortcut.activated.connect(self._save_now)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _update_date_label(self) -> None:
        self.date_label.setText(
            f"📅  {self.current_date.strftime('%A, %B %d, %Y')}"
        )

    def _on_date_selected(self) -> None:
        # Save any pending changes before switching dates.
        if self._dirty:
            self._save_now()
        self.current_date = self.calendar.selectedDate().toPyDate()
        self._update_date_label()
        self._load_note_for_date()

    def _load_note_for_date(self) -> None:
        date_str = self.current_date.strftime("%Y-%m-%d")
        note     = self.db.get_note(date_str)
        # Block signals so loading doesn't trigger auto-save.
        self.notes_editor.blockSignals(True)
        self.notes_editor.setPlainText(note if note else "")
        self.notes_editor.blockSignals(False)
        self._dirty = False
        self.save_status.setText("")

    def _on_text_changed(self) -> None:
        self._dirty = True
        self.save_status.setText("Unsaved…")
        self.save_status.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        self._save_timer.start(self._AUTOSAVE_DELAY_MS)

    def _autosave(self) -> None:
        if self._dirty:
            self._persist()
            self.save_status.setText("Saved")
            self.save_status.setStyleSheet(f"color: {COLORS['success']}; font-size: 12px;")
            # Fade out the "Saved" label after 2 s.
            QTimer.singleShot(2000, lambda: self.save_status.setText(""))

    def _save_now(self) -> None:
        self._save_timer.stop()
        self._persist()
        self.save_status.setText("✓  Saved!")
        self.save_status.setStyleSheet(f"color: {COLORS['success']}; font-size: 12px; font-weight: 600;")
        QTimer.singleShot(1500, lambda: self.save_status.setText(""))

    def _persist(self) -> None:
        date_str  = self.current_date.strftime("%Y-%m-%d")
        note_text = self.notes_editor.toPlainText()
        self.db.save_note(date_str, note_text)
        self._dirty = False
