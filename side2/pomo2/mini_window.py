"""
Mini (picture-in-picture) timer popup.

Shows the live timer + controls so you can start/pause/skip
without switching back to the main window.

Toggle: View -> Mini Timer  (Ctrl+P)
Drag anywhere to reposition.
"""
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QPushButton, QApplication
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter, QPainterPath, QBrush
from theme import COLORS

_W, _H, _R = 290, 96, 12


class MiniTimerWindow(QWidget):
    """Small always-on-top picture-in-picture timer popup."""

    closed              = pyqtSignal()
    play_pause_requested = pyqtSignal()
    skip_requested       = pyqtSignal()

    def __init__(self):
        super().__init__(
            None,
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.FramelessWindowHint  |
            Qt.WindowType.Tool,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(_W, _H)

        self._drag_pos:  QPoint | None = None
        self._color_hex  = COLORS["work"]
        self._is_running = False

        self._build_ui()
        self._place_bottom_right()

    # ── Layout ────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(2)

        # ── Row 1: time  state  × ────────────────────────────────────────────
        top = QHBoxLayout()
        top.setSpacing(8)

        self.time_label = QLabel("25:00")
        tf = QFont(); tf.setPointSize(22); tf.setBold(True)
        self.time_label.setFont(tf)
        top.addWidget(self.time_label)

        self.state_label = QLabel("Work Time")
        sf = QFont(); sf.setPointSize(10)
        self.state_label.setFont(sf)
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        top.addWidget(self.state_label)
        top.addStretch()

        self._close_btn = QPushButton("×")
        self._close_btn.setFixedSize(18, 18)
        self._close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._close_btn.clicked.connect(self._on_close)
        top.addWidget(self._close_btn)
        root.addLayout(top)

        # ── Row 2: task ───────────────────────────────────────────────────────
        self.task_label = QLabel("—")
        task_f = QFont(); task_f.setPointSize(9)
        self.task_label.setFont(task_f)
        root.addWidget(self.task_label)

        # ── Row 3: controls ───────────────────────────────────────────────────
        ctrl = QHBoxLayout()
        ctrl.setSpacing(6)
        ctrl.setContentsMargins(0, 2, 0, 0)

        self._play_btn = QPushButton("▶  Start")
        self._play_btn.setFixedHeight(24)
        self._play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._play_btn.clicked.connect(self.play_pause_requested)
        ctrl.addWidget(self._play_btn)

        self._skip_btn = QPushButton("⏭  Skip")
        self._skip_btn.setFixedHeight(24)
        self._skip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._skip_btn.clicked.connect(self.skip_requested)
        ctrl.addWidget(self._skip_btn)

        ctrl.addStretch()
        root.addLayout(ctrl)

        self._apply_style()

    # ── Public API ────────────────────────────────────────────────────────────

    def update_timer(self, time_text: str, state_text: str,
                     color_hex: str, task_text: str, is_running: bool) -> None:
        self.time_label.setText(time_text)
        self.state_label.setText(state_text)

        style_changed = color_hex != self._color_hex
        self._color_hex  = color_hex
        self._is_running = is_running

        task_display = task_text or "—"
        if len(task_display) > 42:
            task_display = task_display[:39] + "…"
        self.task_label.setText(task_display)

        self._play_btn.setText("⏸  Pause" if is_running else "▶  Start")

        if style_changed:
            self._apply_style()
            self.update()

    # ── Styling ───────────────────────────────────────────────────────────────

    def _apply_style(self) -> None:
        c      = self._color_hex
        text   = COLORS["text"]
        t_sec  = COLORS["text_sec"]
        danger = COLORS.get("danger", "#ef4444")
        border = COLORS["border"]

        self.time_label.setStyleSheet(f"color: {text}; background: transparent;")
        self.state_label.setStyleSheet(f"color: {c}; font-weight: 600; background: transparent;")
        self.task_label.setStyleSheet(f"color: {t_sec}; font-size: 9pt; background: transparent;")

        btn_base = f"""
            QPushButton {{
                background: {COLORS['surface_alt']};
                color: {text};
                border: 1px solid {border};
                border-radius: 5px;
                font-size: 10px;
                font-weight: 600;
                padding: 0 8px;
            }}
            QPushButton:hover  {{ background: {c}; color: white; border-color: {c}; }}
            QPushButton:pressed {{ background: {c}; color: white; }}
        """
        self._play_btn.setStyleSheet(btn_base)
        self._skip_btn.setStyleSheet(btn_base)

        self._close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {t_sec};
                border: none; font-size: 18px; font-weight: bold;
                padding: 0; margin: 0;
            }}
            QPushButton:hover {{ color: {danger}; }}
        """)

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        card = QPainterPath()
        card.addRoundedRect(0, 0, _W, _H, _R, _R)
        p.fillPath(card, QColor(COLORS["surface"]))

        bar = QPainterPath()
        bar.addRoundedRect(0, 0, 5 + _R, _H, _R, _R)
        p.fillPath(card.intersected(bar), QColor(self._color_hex))

        border_path = QPainterPath()
        border_path.addRoundedRect(0.5, 0.5, _W - 1, _H - 1, _R, _R)
        bc = QColor(COLORS["border"]); bc.setAlpha(180)
        p.setPen(bc)
        p.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        p.drawPath(border_path)
        p.end()

    # ── Close / drag ──────────────────────────────────────────────────────────

    def _on_close(self) -> None:
        self.hide()
        self.closed.emit()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None

    def _place_bottom_right(self) -> None:
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - _W - 24, screen.bottom() - _H - 24)
