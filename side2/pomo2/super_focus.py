"""
Super Focus mode tab for Pomodoro app.

Starts a single, full-screen-style deep-work countdown that locks all other
tabs until the session finishes (or is manually stopped).

Enable and configure the duration in Settings → Behavior → Super Focus.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QMessageBox, QFrame,
                             QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QRectF
from PyQt6.QtGui import QFont, QColor, QPainter, QPen
from database import Database
from theme import COLORS


class FocusRingWidget(QWidget):
    """Circular countdown ring for the Super Focus timer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._time_text = "00:00"
        self._progress  = 1.0
        self.setMinimumSize(220, 220)

    def update_state(self, time_text: str, progress: float) -> None:
        self._time_text = time_text
        self._progress  = max(0.0, min(1.0, progress))
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h   = self.width(), self.height()
        size   = min(w, h) - 12
        x      = (w - size) / 2
        y      = (h - size) / 2
        rw     = max(12, size // 13)
        half   = rw / 2
        adj    = QRectF(x + half, y + half, size - rw, size - rw)

        # Track ring
        bg_pen = QPen(QColor(COLORS["border"]))
        bg_pen.setWidth(rw)
        bg_pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        p.setPen(bg_pen)
        p.drawEllipse(adj)

        # Progress arc (accent / indigo)
        if self._progress > 0.002:
            arc_pen = QPen(QColor(COLORS["accent"]))
            arc_pen.setWidth(rw)
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(arc_pen)
            p.drawArc(adj, 90 * 16, -int(360 * self._progress * 16))

        # Time text
        inner_m = rw * 2
        tf = QFont()
        tf.setPointSize(max(20, size // 6))
        tf.setBold(True)
        p.setFont(tf)
        p.setPen(QColor(COLORS["text"]))
        inner = QRectF(x + inner_m, y + inner_m,
                       size - inner_m * 2, size - inner_m * 2)
        p.drawText(inner, Qt.AlignmentFlag.AlignCenter, self._time_text)
        p.end()


class SuperFocusWidget(QWidget):
    """Deep-focus timer tab — locks all other tabs while running."""

    focus_state_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db                = Database()
        self.settings          = self.db.get_super_focus_settings()
        self.remaining_seconds = 0
        self.total_seconds     = 0
        self.active            = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

        self._init_ui()
        self.refresh_settings()

    # ── UI construction ───────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        self.setStyleSheet(f"""
            QWidget {{ background-color: {COLORS['surface']}; }}
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(40, 32, 40, 32)
        root.setSpacing(18)
        root.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        # Title
        title = QLabel("Super Focus")
        tf = QFont()
        tf.setPointSize(26)
        tf.setBold(True)
        title.setFont(tf)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {COLORS['text']};")
        root.addWidget(title)

        subtitle = QLabel("One deep-focus session — all other tabs are locked until you finish.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {COLORS['text_sec']}; font-size: 13px;")
        root.addWidget(subtitle)

        # Circular ring timer
        ring_row = QHBoxLayout()
        ring_row.addStretch()
        self.ring = FocusRingWidget()
        self.ring.setFixedSize(280, 280)
        ring_row.addWidget(self.ring)
        ring_row.addStretch()
        root.addLayout(ring_row)

        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"""
            color: {COLORS['text_sec']};
            background-color: {COLORS['accent_light']};
            border: 1px solid {COLORS['accent_border']};
            border-radius: 8px;
            padding: 10px 18px;
            font-size: 13px;
        """)
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)
        btn_row.addStretch()

        self.start_btn = QPushButton("▶  Start Super Focus")
        self.start_btn.setMinimumSize(190, 44)
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover  {{ background-color: {COLORS['accent_hover']}; }}
            QPushButton:pressed{{ background-color: {COLORS['accent_pressed']}; }}
            QPushButton:disabled {{
                background-color: {COLORS['border']};
                color: {COLORS['text_muted']};
            }}
        """)
        self.start_btn.clicked.connect(self.start_focus)
        btn_row.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹  Stop")
        self.stop_btn.setMinimumSize(110, 44)
        self.stop_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover  {{ background-color: #dc2626; }}
            QPushButton:pressed{{ background-color: #b91c1c; }}
            QPushButton:disabled {{
                background-color: {COLORS['border']};
                color: {COLORS['text_muted']};
            }}
        """)
        self.stop_btn.clicked.connect(self.stop_focus)
        self.stop_btn.setEnabled(False)
        btn_row.addWidget(self.stop_btn)

        btn_row.addStretch()
        root.addLayout(btn_row)
        root.addStretch()

    # ── Public interface ──────────────────────────────────────────────────────

    def refresh_settings(self) -> None:
        """Reload super focus settings from the database."""
        self.settings = self.db.get_super_focus_settings()
        duration      = self.settings.get("duration_minutes", 60)
        enabled       = self.settings.get("enabled", False)
        state_str     = "Enabled" if enabled else "Disabled"
        self.status_label.setText(
            f"Status: {state_str}  ·  Duration: {duration} min\n"
            f"{'Enable Super Focus in Settings → Behavior to start.' if not enabled else 'Click Start to begin your session.'}"
        )
        if not self.active:
            self.total_seconds     = duration * 60
            self.remaining_seconds = self.total_seconds
            self._update_display()

    def start_focus(self) -> None:
        if not self.settings.get("enabled", False):
            QMessageBox.warning(
                self, "Super Focus Disabled",
                "Enable Super Focus in Settings → Behavior first."
            )
            return
        if self.active:
            return

        duration               = max(1, int(self.settings.get("duration_minutes", 60)))
        self.total_seconds     = duration * 60
        self.remaining_seconds = self.total_seconds
        self.active            = True
        self.timer.start(1000)
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText(
            f"Super Focus running — {duration} min session.  Other tabs are locked."
        )
        self._update_display()
        self.focus_state_changed.emit(True)

    def stop_focus(self) -> None:
        if not self.active:
            return
        self.timer.stop()
        self.active = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.refresh_settings()
        self.focus_state_changed.emit(False)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _tick(self) -> None:
        self.remaining_seconds -= 1
        if self.remaining_seconds <= 0:
            self.remaining_seconds = 0
            self._update_display()
            self.timer.stop()
            self.active = False
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.focus_state_changed.emit(False)
            QMessageBox.information(self, "Super Focus Complete",
                                    "🎉 Super Focus session complete. Great work!")
            self.refresh_settings()
            return
        self._update_display()

    def _update_display(self) -> None:
        mins = self.remaining_seconds // 60
        secs = self.remaining_seconds % 60
        text = f"{mins:02d}:{secs:02d}"
        progress = (self.remaining_seconds / self.total_seconds
                    if self.total_seconds > 0 else 1.0)
        self.ring.update_state(text, progress)
