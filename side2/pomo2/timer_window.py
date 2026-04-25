"""
Main timer window for Pomodoro app.

Keyboard shortcuts (when the Timer tab is focused):
    Space  – Start / Pause toggle
    R      – Reset to beginning of current phase
    S      – Skip to next phase
    M      – Toggle mute
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QSystemTrayIcon, QMenu, QApplication,
                             QDialog, QMessageBox, QSizePolicy)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QUrl, QSize, QRectF, QThread
from PyQt6.QtGui import (QIcon, QFont, QAction, QPixmap, QPainter, QColor,
                         QPen, QKeySequence)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from enum import Enum
from datetime import datetime, timedelta
import os
import json
import math
import struct
import tempfile
import wave
import platform
from pathlib import Path
from database import Database
from models import Settings, ScheduleTask
from theme import COLORS, STATE_COLORS, get_state_bundle


class TimerState(Enum):
    """Possible states of the Pomodoro timer."""
    WORK        = "work"
    SHORT_BREAK = "short_break"
    LONG_BREAK  = "long_break"
    DOWNTIME    = "downtime"
    PAUSED      = "paused"


# ---------------------------------------------------------------------------
# Circular progress ring widget
# ---------------------------------------------------------------------------

class TimerRingWidget(QWidget):
    """Draws a circular arc that depletes as the timer counts down.

    The ring colour changes with the timer state:
      • Red   – Work
      • Sky   – Short break
      • Green – Long break
      • Gray  – Paused / idle
    Time and state labels are drawn *inside* the ring.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._time_text  = "00:00"
        self._state_text = "Work Time"
        self._progress   = 1.0          # 1.0 = full ring, 0.0 = empty
        self._color      = QColor(COLORS["work"])
        self.setMinimumSize(240, 240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def update_state(self, time_text: str, state_text: str,
                     progress: float, color_hex: str) -> None:
        """Refresh the ring display. Call whenever the timer ticks."""
        self._time_text  = time_text
        self._state_text = state_text
        self._progress   = max(0.0, min(1.0, progress))
        self._color      = QColor(color_hex)
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h     = self.width(), self.height()
        size     = min(w, h) - 12
        x        = (w - size) / 2
        y        = (h - size) / 2
        ring_w   = max(12, size // 13)
        half_rw  = ring_w / 2
        adjusted = QRectF(x + half_rw, y + half_rw,
                          size - ring_w, size - ring_w)

        # ── Background ring (light gray) ─────────────────────────────────────
        bg_pen = QPen(QColor(COLORS["border"]))
        bg_pen.setWidth(ring_w)
        bg_pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        p.setPen(bg_pen)
        p.drawEllipse(adjusted)

        # ── Foreground arc (coloured, starts at 12 o'clock = 90°) ───────────
        if self._progress > 0.002:
            arc_pen = QPen(self._color)
            arc_pen.setWidth(ring_w)
            arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            p.setPen(arc_pen)
            p.drawArc(adjusted, 90 * 16, -int(360 * self._progress * 16))

        # ── Center: time text ────────────────────────────────────────────────
        inner_margin = ring_w * 2
        inner = QRectF(x + inner_margin, y + inner_margin,
                       size - inner_margin * 2, size - inner_margin * 2)

        # Time (large, bold, dark)
        tf = QFont()
        tf.setPointSize(max(20, size // 6))
        tf.setBold(True)
        p.setFont(tf)
        p.setPen(QColor(COLORS["text"]))

        # Split inner vertically: time gets upper 55%, state gets lower 30%
        time_rect  = QRectF(inner.x(), inner.y(),
                            inner.width(), inner.height() * 0.55)
        state_rect = QRectF(inner.x(), inner.y() + inner.height() * 0.58,
                            inner.width(), inner.height() * 0.30)

        p.drawText(time_rect,
                   Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                   self._time_text)

        # State label (smaller, colored)
        sf = QFont()
        sf.setPointSize(max(9, size // 22))
        sf.setBold(False)
        p.setFont(sf)
        p.setPen(self._color)
        p.drawText(state_rect,
                   Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                   self._state_text)

        p.end()


# ---------------------------------------------------------------------------
# Session dots indicator
# ---------------------------------------------------------------------------

class SessionDotsWidget(QWidget):
    """Renders four dots showing progress through the 4-pomodoro cycle.

    Filled dots = completed work sessions since the last long break.
    """

    DOT_SIZE = 12
    DOT_GAP  = 10
    N        = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sessions = 0
        total_w = self.N * self.DOT_SIZE + (self.N - 1) * self.DOT_GAP
        self.setFixedSize(total_w + 4, self.DOT_SIZE + 8)

    def set_sessions(self, count: int) -> None:
        """Set the number of completed sessions (auto-wraps at 4)."""
        self._sessions = count % self.N
        self.update()

    def paintEvent(self, event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)

        total_w = self.N * self.DOT_SIZE + (self.N - 1) * self.DOT_GAP
        sx = (self.width() - total_w) / 2
        cy = self.height() / 2

        for i in range(self.N):
            x = sx + i * (self.DOT_SIZE + self.DOT_GAP)
            color = QColor(COLORS["work"]) if i < self._sessions else QColor(COLORS["border"])
            p.setBrush(color)
            p.drawEllipse(int(x), int(cy - self.DOT_SIZE / 2),
                          self.DOT_SIZE, self.DOT_SIZE)
        p.end()


# ---------------------------------------------------------------------------
# Alarm completion dialog
# ---------------------------------------------------------------------------

class AlarmDialog(QDialog):
    """Modal dialog shown when a timer phase completes; stops the alarm sound."""

    def __init__(self, parent=None, timer_name: str = "Timer", media_player=None):
        super().__init__(parent)
        self.media_player = media_player
        self.setWindowTitle("Timer Complete!")
        self.setModal(True)
        self.setMinimumSize(380, 190)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['surface']};
                border: 2px solid {COLORS['accent_border']};
                border-radius: 12px;
            }}
            QLabel {{ color: {COLORS['text']}; }}
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border: none;
                padding: 11px 28px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover  {{ background-color: {COLORS['accent_hover']}; }}
            QPushButton:pressed{{ background-color: {COLORS['accent_pressed']}; }}
        """)
        self._build(timer_name)
        self.raise_()
        self.activateWindow()

    def _build(self, timer_name: str) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(32, 28, 32, 28)

        title = QLabel(f"{timer_name} Complete!")
        tf = QFont()
        tf.setPointSize(22)
        tf.setBold(True)
        title.setFont(tf)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {COLORS['accent']};")
        layout.addWidget(title)

        msg = QLabel("Your timer has finished.")
        mf = QFont()
        mf.setPointSize(13)
        msg.setFont(mf)
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet(f"color: {COLORS['text_sec']};")
        layout.addWidget(msg)

        row = QHBoxLayout()
        row.addStretch()
        btn = QPushButton("Dismiss")
        btn.setMinimumSize(140, 42)
        btn.clicked.connect(self._stop_alarm)
        row.addWidget(btn)
        row.addStretch()
        layout.addLayout(row)

    def _stop_alarm(self) -> None:
        if self.media_player:
            self.media_player.stop()
        self.accept()


# ---------------------------------------------------------------------------
# Virtual desktop switcher (background thread — avoids freezing the UI)
# ---------------------------------------------------------------------------

class _DesktopSwitchThread(QThread):
    """Navigates to a target virtual desktop number (1-based) off the main thread.

    Pure navigation — no window is moved. The user arranges their own apps on
    each desktop; the timer just switches which desktop is visible.

    Strategy: Win+Ctrl+Left ×10 (safe floor to desktop 1) then Right ×(target-1).
    """

    done = pyqtSignal()

    def __init__(self, target: int, parent=None):
        super().__init__(parent)
        self._target = max(1, target)

    def run(self) -> None:
        try:
            import ctypes
            import time

            u32    = ctypes.windll.user32
            VK_LWIN, VK_CONTROL = 0x5B, 0x11
            VK_LEFT, VK_RIGHT   = 0x25, 0x27
            KEYUP               = 0x0002

            def press(arrow):
                u32.keybd_event(VK_LWIN,    0, 0,     0)
                u32.keybd_event(VK_CONTROL, 0, 0,     0)
                u32.keybd_event(arrow,      0, 0,     0)
                u32.keybd_event(arrow,      0, KEYUP, 0)
                u32.keybd_event(VK_CONTROL, 0, KEYUP, 0)
                u32.keybd_event(VK_LWIN,    0, KEYUP, 0)
                time.sleep(0.20)

            for _ in range(10):
                press(VK_LEFT)
            for _ in range(self._target - 1):
                press(VK_RIGHT)

        except Exception:
            pass
        finally:
            self.done.emit()


# ---------------------------------------------------------------------------
# Main timer widget
# ---------------------------------------------------------------------------

class TimerWindow(QWidget):
    """Pomodoro timer — displays a circular progress ring and controls.

    Keyboard shortcuts (requires widget focus):
        Space – Start / Pause toggle
        R     – Reset current phase
        S     – Skip to next phase
        M     – Toggle mute
    """

    timer_completed  = pyqtSignal(str)
    mini_tick        = pyqtSignal(str, str, str, str, bool)  # time, state, color, task, is_running
    desktop_switched = pyqtSignal()                           # emitted after every desktop nav

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db                   = Database()
        self._mini_task_text      = ""
        self.settings             = self._load_settings()
        self.state                = TimerState.WORK
        self.previous_state       = TimerState.WORK
        self.remaining_seconds    = 0
        self.work_sessions        = 0
        self.downtime_seconds     = 0
        self.last_notification_time = 0
        self.is_downtime_active   = False
        self.muted                = False
        self.timer                = QTimer(self)
        self.timer.timeout.connect(self._update_timer)
        self.tray_icon            = None
        self.alarm_dialog         = None

        self.audio_output  = QAudioOutput(self)
        self.media_player  = QMediaPlayer(self)
        self.media_player.setAudioOutput(self.audio_output)

        self.tick_audio_output = QAudioOutput(self)
        self.tick_audio_output.setVolume(0.5)
        self.tick_player = QMediaPlayer(self)
        self.tick_player.setAudioOutput(self.tick_audio_output)

        self._init_ui()
        self._setup_tray()
        self._load_state()

    # ── Settings helpers ──────────────────────────────────────────────────────

    def _load_settings(self) -> Settings:
        data = self.db.get_settings()
        if data:
            return Settings.from_dict(self._apply_day_preset_if_enabled(data))
        return Settings()

    def _apply_day_preset_if_enabled(self, settings_data: dict) -> dict:
        """Override timer values from weekday/weekend preset when enabled."""
        try:
            preset_path = Path(__file__).parent / "data" / "timer_presets.json"
            if not preset_path.exists():
                return settings_data
            with open(preset_path, "r", encoding="utf-8") as f:
                store = json.load(f) or {}
            if not store.get("auto_apply", False):
                return settings_data

            presets = store.get("presets", {})
            if not isinstance(presets, dict):
                return settings_data
            is_weekend  = datetime.now().weekday() >= 5
            key         = "weekend_preset" if is_weekend else "weekday_preset"
            preset_name = store.get(key)
            payload     = presets.get(preset_name, {})
            if not isinstance(payload, dict):
                return settings_data

            merged = dict(settings_data)
            for field in ("work_time", "short_break", "long_break",
                          "downtime", "downtime_notify_threshold"):
                if field in payload:
                    merged[field] = int(payload[field])
            return merged
        except Exception:
            return settings_data

    def _load_schedule_options(self) -> dict:
        defaults = {"include_bedtime_routine": False, "awake_hours": 16}
        try:
            path = Path(__file__).parent / "data" / "schedule_options.json"
            if not path.exists():
                return defaults
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f) or {}
            if not isinstance(loaded, dict):
                return defaults
            merged = defaults.copy()
            merged.update(loaded)
            return merged
        except Exception:
            return defaults

    # ── Schedule helpers (for indicator) ─────────────────────────────────────

    def _build_bedtime_windows(self, wake: datetime):
        opts = self._load_schedule_options()
        if not opts.get("include_bedtime_routine", False):
            return []

        awake_hours = max(8, min(20, int(opts.get("awake_hours", 16))))
        sleep_start = wake + timedelta(hours=awake_hours)
        sleep_end   = sleep_start + timedelta(hours=8)

        steps = [
            ("🧹 Tidy + Prepare Tomorrow", 30),
            ("📵 Wind Down (No Screens)",  30),
        ]

        windows = []
        total  = sum(m for _, m in steps)
        cursor = sleep_start - timedelta(minutes=total)
        for title, duration in steps:
            start = cursor
            end   = start + timedelta(minutes=duration)
            windows.append((
                ScheduleTask(id=None, task=title, duration_minutes=duration,
                             is_fixed_time=True,
                             fixed_time=start.strftime("%H:%M"),
                             fixed_time_end=end.strftime("%H:%M"),
                             offset_minutes=0, anchor_type="wake_up",
                             anchor_task_id=None, sort_order=10_000 + len(windows)),
                start, end,
            ))
            cursor = end

        windows.append((
            ScheduleTask(id=None, task="😴 Sleep",
                         duration_minutes=int((sleep_end - sleep_start).total_seconds() // 60),
                         is_fixed_time=True,
                         fixed_time=sleep_start.strftime("%H:%M"),
                         fixed_time_end=sleep_end.strftime("%H:%M"),
                         offset_minutes=0, anchor_type="wake_up",
                         anchor_task_id=None, sort_order=10_100),
            sleep_start, sleep_end,
        ))
        return windows

    def _get_fixed_end(self, task: ScheduleTask, start_dt: datetime) -> datetime:
        if task.fixed_time_end:
            try:
                h, m = map(int, task.fixed_time_end.split(":"))
                end_same = start_dt.replace(hour=h, minute=m, second=0, microsecond=0)
                if end_same > start_dt:
                    return end_same
                candidates = []
                if h < 12:
                    plus_12 = end_same + timedelta(hours=12)
                    if plus_12 > start_dt:
                        candidates.append(plus_12)
                plus_24 = end_same + timedelta(days=1)
                if plus_24 > start_dt:
                    candidates.append(plus_24)
                if candidates:
                    return min(candidates, key=lambda dt: dt - start_dt)
                return end_same
            except Exception:
                pass
        return start_dt + timedelta(minutes=max(int(task.duration_minutes or 30), 1))

    def _get_schedule_windows(self):
        date_str = datetime.now().strftime("%Y-%m-%d")
        wake_str = self.db.get_wakeup_time(date_str)
        if not wake_str:
            return []
        try:
            h, m = map(int, wake_str.split(":"))
        except ValueError:
            return []

        now  = datetime.now()
        wake = now.replace(hour=h, minute=m, second=0, microsecond=0)

        raw_tasks = self.db.get_schedule_tasks()
        tasks     = [ScheduleTask.from_dict(t) for t in raw_tasks]
        if not tasks:
            return []

        occupied_windows = []
        fixed_entries    = []

        for t in tasks:
            if not t.is_fixed_time or not t.fixed_time:
                continue
            try:
                sh, sm = map(int, t.fixed_time.split(":"))
                start  = wake.replace(hour=sh, minute=sm, second=0)
            except Exception:
                start = wake
            end = self._get_fixed_end(t, start)
            if end <= start:
                end = start + timedelta(minutes=30)
            fixed_entries.append((t, start, end))
            occupied_windows.append((start, end))

        for t, start, end in self._build_bedtime_windows(wake):
            fixed_entries.append((t, start, end))
            occupied_windows.append((start, end))

        def all_windows():
            wins = list(occupied_windows)
            wins.sort(key=lambda x: x[0])
            return wins

        relative_tasks = [t for t in tasks if not t.is_fixed_time]
        relative_tasks.sort(key=lambda x: (x.sort_order, x.id or 0))
        relative_entries = []
        cursor = wake

        for t in relative_tasks:
            dur          = max(1, int(t.duration_minutes))
            break_min    = max(0, int(t.offset_minutes or 0))
            start        = cursor + timedelta(minutes=break_min)
            end          = start + timedelta(minutes=dur)
            changed = True
            while changed:
                changed = False
                for ws, we in all_windows():
                    if start < we and end > ws:
                        start   = we + timedelta(minutes=break_min)
                        end     = start + timedelta(minutes=dur)
                        changed = True
            occupied_windows.append((start, end))
            relative_entries.append((t, start, end))
            cursor = end

        combined = fixed_entries + relative_entries
        combined.sort(key=lambda row: row[1])
        return combined

    def _update_schedule_indicator(self) -> None:
        if not hasattr(self, "schedule_now_label"):
            return
        now     = datetime.now()
        windows = self._get_schedule_windows()
        current = None
        for task, start, end in windows:
            if start <= now < end:
                current = (task, start, end)
                break
        if current:
            task, _, end = current
            self.schedule_now_label.setText(
                f"📌 Now: {task.task} (until {end.strftime('%I:%M %p').lstrip('0')})"
            )
            self._mini_task_text = task.task
        else:
            self.schedule_now_label.setText("📌 Schedule: —")
            self._mini_task_text = self._get_first_pending_todo()

    # ── UI construction ───────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        self.setWindowTitle("Pomodoro Timer")
        self.setMinimumSize(300, 150)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(32, 28, 32, 24)

        # ── Schedule indicator (top-right) ────────────────────────────────────
        top_row = QHBoxLayout()
        top_row.addStretch()
        self.schedule_now_label = QLabel("📌 Schedule: —")
        self.schedule_now_label.setStyleSheet(
            f"color: {COLORS['accent']}; font-size: 12px; font-weight: 600;"
        )
        self.schedule_now_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        top_row.addWidget(self.schedule_now_label)
        root.addLayout(top_row)

        # ── Circular timer ring ───────────────────────────────────────────────
        self.ring = TimerRingWidget()
        root.addWidget(self.ring, 1)

        # ── Session dots ──────────────────────────────────────────────────────
        dots_row = QHBoxLayout()
        dots_row.addStretch()
        self.session_dots = SessionDotsWidget()
        dots_row.addWidget(self.session_dots)
        dots_row.addStretch()
        root.addLayout(dots_row)

        # Sessions text
        self.sessions_label = QLabel("Work Sessions: 0")
        self.sessions_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sf = QFont()
        sf.setPointSize(12)
        self.sessions_label.setFont(sf)
        self.sessions_label.setStyleSheet(f"color: {COLORS['text_sec']};")
        root.addWidget(self.sessions_label)

        # ── Control buttons ───────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.start_button = self._make_button("▶  Start",  COLORS["success"],    "#059669", tip="Start  [Space]")
        self.pause_button = self._make_button("⏸  Pause",  COLORS["warning"],    "#d97706", tip="Pause  [Space]")
        self.reset_button = self._make_button("⏹  Reset",  COLORS["danger"],     "#dc2626", tip="Reset  [R]")
        self.skip_button  = self._make_button("⏭  Skip",   COLORS["short_break"],"#0284c7", tip="Skip   [S]")

        self.start_button.clicked.connect(self.start_timer)
        self.pause_button.clicked.connect(self.pause_timer)
        self.reset_button.clicked.connect(self.reset_timer)
        self.skip_button.clicked.connect(self.skip_timer)

        self.pause_button.setEnabled(False)

        for btn in (self.start_button, self.pause_button,
                    self.reset_button, self.skip_button):
            btn_row.addWidget(btn)

        root.addLayout(btn_row)

        # ── Mute toggle ───────────────────────────────────────────────────────
        mute_row = QHBoxLayout()
        mute_row.addStretch()
        self.mute_button = QPushButton("🔊  Mute")
        self.mute_button.setToolTip("Toggle mute  [M]")
        self.mute_button.setFixedHeight(32)
        self.mute_button.setFixedWidth(110)
        self.mute_button.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text_sec']};
                border: 1.5px solid {COLORS['border']};
                border-radius: 16px;
                font-size: 12px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: {COLORS['border']};
                color: {COLORS['text']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['accent_light']};
                color: {COLORS['accent']};
                border-color: {COLORS['accent_border']};
            }}
        """)
        self.mute_button.clicked.connect(self.toggle_mute)
        mute_row.addWidget(self.mute_button)
        mute_row.addStretch()
        root.addLayout(mute_row)

        # ── Downtime display ──────────────────────────────────────────────────
        self.downtime_container = QWidget()
        dt_layout = QVBoxLayout(self.downtime_container)
        dt_layout.setSpacing(4)
        dt_layout.setContentsMargins(0, 8, 0, 0)

        dt_title = QLabel("💤 Downtime")
        dt_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dtf = QFont()
        dtf.setPointSize(11)
        dt_title.setFont(dtf)
        dt_title.setStyleSheet(f"color: {COLORS['text_muted']};")
        dt_layout.addWidget(dt_title)

        self.downtime_label = QLabel("00:00")
        self.downtime_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        dlf = QFont()
        dlf.setPointSize(22)
        dlf.setBold(True)
        self.downtime_label.setFont(dlf)
        self.downtime_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        dt_layout.addWidget(self.downtime_label)

        self.downtime_container.setVisible(self.settings.enable_downtime)
        root.addWidget(self.downtime_container)

        self._update_display()
        self._apply_state_style()
        self._update_icon()
        self._update_ui_for_size()

    @staticmethod
    def _make_button(text: str, color: str, hover: str, tip: str = "") -> QPushButton:
        """Return a styled control button."""
        btn = QPushButton(text)
        btn.setToolTip(tip)
        btn.setMinimumHeight(40)
        btn.setMinimumWidth(100)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
            }}
            QPushButton:hover  {{ background-color: {hover}; }}
            QPushButton:pressed{{ background-color: {hover}; }}
            QPushButton:disabled {{
                background-color: {COLORS['border']};
                color: {COLORS['text_muted']};
            }}
        """)
        return btn

    # ── Icon helpers ──────────────────────────────────────────────────────────

    def _create_battery_icon(self, minutes: int, ratio: float, color: QColor) -> QIcon:
        """Return a taskbar/tray icon showing remaining minutes."""
        fill_ratio   = max(0.0, min(1.0, ratio))
        minutes_text = str(max(0, minutes))
        if len(minutes_text) > 2:
            minutes_text = "99+"

        def _render(size: int) -> QPixmap:
            pixmap = QPixmap(size, size)
            pixmap.fill(QColor(255, 255, 255, 0))
            p = QPainter(pixmap)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)

            margin = max(1, size // 10)
            rect_x, rect_y = margin, margin
            rect_w = size - margin * 2
            rect_h = size - margin * 2
            radius = max(2, size // 8)

            p.setBrush(QColor(255, 255, 255, 245))
            p.setPen(QColor(color.red(), color.green(), color.blue(), 230))
            p.drawRoundedRect(rect_x, rect_y, rect_w, rect_h, radius, radius)

            bar_margin = max(2, size // 8)
            bar_h      = max(2, size // 8)
            bar_x      = rect_x + bar_margin
            bar_w      = rect_w - bar_margin * 2
            bar_y      = rect_y + rect_h - bar_h - bar_margin

            p.setBrush(QColor(230, 230, 230))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 1, 1)

            if minutes > 0:
                fill_w = max(1, int(bar_w * fill_ratio))
                p.setBrush(QColor(color.red(), color.green(), color.blue(), 230))
                p.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 1, 1)

            font = QFont()
            if size <= 20:
                font.setPointSize(max(7, size // 2))
            elif size <= 32:
                font.setPointSize(max(9, size // 2))
            else:
                font.setPointSize(max(12, size // 3))
            font.setBold(True)
            p.setFont(font)
            p.setPen(QColor(20, 20, 20))
            text_rect = pixmap.rect().adjusted(0, 0, 0, -max(3, size // 6))
            p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, minutes_text)
            p.end()
            return pixmap

        icon = QIcon()
        for s in (16, 20, 24, 32, 40, 48, 64):
            icon.addPixmap(_render(s))
        return icon

    def _update_icon(self) -> None:
        color_map = {
            TimerState.WORK:        QColor(COLORS["work"]),
            TimerState.SHORT_BREAK: QColor(COLORS["short_break"]),
            TimerState.LONG_BREAK:  QColor(COLORS["long_break"]),
        }
        icon_color   = color_map.get(self.state, QColor(COLORS["text_sec"]))
        total_secs   = max(1, self._get_timer_duration())
        ratio        = self.remaining_seconds / total_secs
        minutes      = self.remaining_seconds // 60
        icon         = self._create_battery_icon(minutes, ratio, icon_color)

        self.setWindowIcon(icon)
        app = QApplication.instance()
        if app:
            app.setWindowIcon(icon)
        if self.tray_icon:
            self.tray_icon.setIcon(icon)

    # ── Tray ──────────────────────────────────────────────────────────────────

    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray_icon = QSystemTrayIcon(self)
        menu = QMenu()
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show)
        menu.addAction(show_action)
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(quit_action)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._tray_icon_activated)
        self.tray_icon.show()
        self._update_icon()

    def _tray_icon_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.raise_()
            self.activateWindow()

    # ── Display helpers ───────────────────────────────────────────────────────

    def _state_display_text(self) -> str:
        return {
            TimerState.WORK:        "Work Time",
            TimerState.SHORT_BREAK: "Short Break",
            TimerState.LONG_BREAK:  "Long Break",
            TimerState.DOWNTIME:    "Downtime",
            TimerState.PAUSED:      "Paused",
        }.get(self.state, "")

    def _state_color_hex(self) -> str:
        color_map = {
            TimerState.WORK:        COLORS["work"],
            TimerState.SHORT_BREAK: COLORS["short_break"],
            TimerState.LONG_BREAK:  COLORS["long_break"],
            TimerState.DOWNTIME:    COLORS["downtime"] if "downtime" in COLORS else COLORS["text_sec"],
            TimerState.PAUSED:      COLORS["text_sec"],
        }
        return color_map.get(self.state, COLORS["text_sec"])

    def _get_first_pending_todo(self) -> str:
        try:
            todos = self.db.get_todos()
            for t in todos:
                if not t.get("completed"):
                    return t.get("task") or ""
        except Exception:
            pass
        return ""

    def _update_display(self) -> None:
        mins = self.remaining_seconds // 60
        secs = self.remaining_seconds % 60
        time_text  = f"{mins:02d}:{secs:02d}"
        state_text = self._state_display_text()
        color_hex  = self._state_color_hex()

        total    = max(1, self._get_timer_duration())
        progress = self.remaining_seconds / total

        self.ring.update_state(time_text, state_text, progress, color_hex)

        self.sessions_label.setText(f"Work Sessions: {self.work_sessions}")
        self.session_dots.set_sessions(self.work_sessions)

        # Downtime display
        if hasattr(self, "downtime_label") and self.settings.enable_downtime:
            dm = self.downtime_seconds // 60
            ds = self.downtime_seconds % 60
            self.downtime_label.setText(f"{dm:02d}:{ds:02d}")
            if self.downtime_seconds >= self.settings.downtime_notify_threshold:
                self.downtime_label.setStyleSheet(f"color: {COLORS['warning']}; font-weight: bold;")
            else:
                self.downtime_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        elif hasattr(self, "downtime_label"):
            self.downtime_label.setText("--:--")
            self.downtime_label.setStyleSheet(f"color: {COLORS['border']};")

        self._update_icon()
        self._update_schedule_indicator()
        self.mini_tick.emit(time_text, state_text, color_hex,
                            self._mini_task_text, self.timer.isActive())

    def _apply_state_style(self) -> None:
        """Keep the background neutral — the ring handles all state colour."""
        self.setStyleSheet(f"QWidget {{ background-color: {COLORS['surface']}; }}")
        if hasattr(self, "downtime_container"):
            self.downtime_container.setVisible(self.settings.enable_downtime)
        self._update_icon()

    # ── Timer duration helpers ────────────────────────────────────────────────

    def _get_timer_duration(self) -> int:
        return {
            TimerState.WORK:        self.settings.work_time,
            TimerState.SHORT_BREAK: self.settings.short_break,
            TimerState.LONG_BREAK:  self.settings.long_break,
        }.get(self.state, 0)

    def _get_next_state(self) -> str:
        if self.state == TimerState.WORK:
            return "long_break" if (self.work_sessions + 1) % 4 == 0 else "short_break"
        return "work"

    def _next_state(self) -> None:
        if self.state == TimerState.WORK:
            self.work_sessions += 1
            self.state = (TimerState.LONG_BREAK
                          if self.work_sessions % 4 == 0
                          else TimerState.SHORT_BREAK)
        elif self.state in (TimerState.SHORT_BREAK, TimerState.LONG_BREAK):
            self.state = TimerState.WORK
        self.remaining_seconds = self._get_timer_duration()
        self._update_display()
        self._apply_state_style()

    # ── Audio helpers ─────────────────────────────────────────────────────────

    def _has_sound_for_state(self, state_name: str) -> bool:
        paths = {
            "work":        self.settings.alarm_sound_path,
            "short_break": self.settings.short_break_sound_path,
            "long_break":  self.settings.long_break_sound_path,
        }
        p = paths.get(state_name, "")
        return bool(p and os.path.exists(p))

    def _pause_system_media(self) -> None:
        """Send a media play/pause keystroke to pause browser/music apps (Windows)."""
        if platform.system() != "Windows":
            return
        try:
            import ctypes
            VK_MEDIA_PLAY_PAUSE = 0xB3
            KEYEVENTF_KEYUP     = 0x0002
            u32 = ctypes.windll.user32
            u32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
            u32.keybd_event(VK_MEDIA_PLAY_PAUSE, 0, KEYEVENTF_KEYUP, 0)
        except Exception:
            pass

    def _get_sound_path(self, state_name: str):
        sound_map = {
            "work":        self.settings.alarm_sound_path,
            "short_break": self.settings.short_break_sound_path,
            "long_break":  self.settings.long_break_sound_path,
            "downtime":    self.settings.downtime_sound_path,
        }
        p = sound_map.get(state_name) or self.settings.alarm_sound_path
        return p if (p and os.path.exists(p)) else None

    def _generate_tick_sound(self) -> str:
        if hasattr(self, "_tick_sound_path") and os.path.exists(self._tick_sound_path):
            return self._tick_sound_path
        sample_rate = 44100
        duration    = 0.08
        frequency   = 1200
        n_samples   = int(sample_rate * duration)
        samples = []
        for i in range(n_samples):
            t        = i / sample_rate
            envelope = math.exp(-t * 60)
            value    = envelope * math.sin(2 * math.pi * frequency * t)
            if i < 80:
                value += envelope * 0.5 * math.sin(2 * math.pi * 2400 * t)
            sample = max(-32768, min(32767, int(value * 32767 * 0.7)))
            samples.append(struct.pack("<h", sample))
        tick_path = os.path.join(tempfile.gettempdir(), "pomo_tick.wav")
        with wave.open(tick_path, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b"".join(samples))
        self._tick_sound_path = tick_path
        return tick_path

    def _play_tick(self) -> None:
        try:
            tick_path = self._generate_tick_sound()
            self.tick_player.setSource(QUrl.fromLocalFile(tick_path))
            self.tick_player.play()
        except Exception:
            pass

    # ── Public timer controls ─────────────────────────────────────────────────

    def start_timer(self) -> None:
        self._pause_system_media()
        if self.is_downtime_active:
            self._stop_downtime()
        if self.state == TimerState.PAUSED:
            self.state = self.previous_state
        if self.remaining_seconds == 0:
            self.remaining_seconds = self._get_timer_duration()
        self.timer.start(1000)
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self._apply_state_style()

        # Move window to the configured virtual desktop for this phase
        if self.settings.switch_desktop:
            target = (self.settings.work_desktop
                      if self.state == TimerState.WORK
                      else self.settings.break_desktop)
            self._switch_to_desktop(target)

    def pause_timer(self) -> None:
        self.timer.stop()
        self.previous_state = self.state
        self.state          = TimerState.PAUSED
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self._apply_state_style()
        self._update_display()

    def reset_timer(self) -> None:
        self.timer.stop()
        self._stop_downtime()
        self.state             = TimerState.WORK
        self.remaining_seconds = self._get_timer_duration()
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self._update_display()
        self._apply_state_style()

    def skip_timer(self) -> None:
        self.timer.stop()
        self._stop_downtime()
        self._next_state()
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        if self.settings.auto_start:
            self.start_timer()

    def toggle_mute(self) -> None:
        self.muted = not self.muted
        if self.muted:
            self.mute_button.setText("🔇  Unmute")
            if self.media_player and self.media_player.isPlaying():
                self.media_player.stop()
        else:
            self.mute_button.setText("🔊  Mute")

    # ── Keyboard shortcuts ────────────────────────────────────────────────────

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key == Qt.Key.Key_Space:
            if self.timer.isActive():
                self.pause_timer()
            else:
                self.start_timer()
        elif key == Qt.Key.Key_R:
            self.reset_timer()
        elif key == Qt.Key.Key_S:
            self.skip_timer()
        elif key == Qt.Key.Key_M:
            self.toggle_mute()
        else:
            super().keyPressEvent(event)

    # ── Timer tick ────────────────────────────────────────────────────────────

    def _update_timer(self) -> None:
        if self.is_downtime_active:
            self.downtime_seconds += 1
            self._check_downtime_notification()
            self._update_display()

        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self._update_display()
            if 0 < self.remaining_seconds <= 5 and not self.muted:
                self._play_tick()
            return

        if not self.is_downtime_active:
            self._handle_timer_completion()

    def _check_downtime_notification(self) -> None:
        if not (self.settings.enable_downtime
                and self.settings.downtime_notify_threshold > 0):
            return
        threshold = self.settings.downtime_notify_threshold
        intervals = self.downtime_seconds // threshold
        if intervals > 0 and intervals * threshold > self.last_notification_time:
            self.last_notification_time = intervals * threshold
            self._notify_downtime_exceeded()

    def _notify_downtime_exceeded(self) -> None:
        has_sound = bool(self.settings.downtime_sound_path
                         and os.path.exists(self.settings.downtime_sound_path))
        self._show_alarm_dialog("downtime", play_sound=has_sound and not self.muted)

    def _handle_timer_completion(self) -> None:
        if getattr(self, '_completing', False):
            return
        self._completing = True
        try:
            self._handle_timer_completion_inner()
        finally:
            self._completing = False

    def _handle_timer_completion_inner(self) -> None:
        duration = self._get_timer_duration()
        self.db.log_session(self.state.value, duration)

        self.timer_completed.emit(self.state.value)
        next_state = self._get_next_state()

        if self.settings.switch_desktop:
            target = (self.settings.work_desktop
                      if next_state == "work"
                      else self.settings.break_desktop)
            self._switch_to_desktop(target)

        has_sound = self._has_sound_for_state(next_state)
        self._show_alarm_dialog(next_state, play_sound=has_sound and not self.muted)

        self._next_state()
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)

        if self.settings.auto_start:
            self.start_timer()
        elif self.settings.enable_downtime:
            self._start_downtime()
        else:
            self.timer.stop()

    # ── Desktop switching (Windows) ───────────────────────────────────────────

    def _switch_to_desktop(self, target_desktop: int) -> None:
        """Navigate to a virtual desktop number (1-based) in a background thread."""
        if platform.system() != "Windows":
            return
        self._desktop_thread = _DesktopSwitchThread(target_desktop)
        self._desktop_thread.done.connect(self.desktop_switched)
        self._desktop_thread.start()

    def _bring_window_to_front(self) -> None:
        try:
            if platform.system() == "Windows":
                import ctypes
                hwnd = int(self.winId())
                ctypes.windll.user32.ShowWindow(hwnd, 5)
                ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass
        self.show()
        self.raise_()
        self.activateWindow()

    # ── Alarm dialog ──────────────────────────────────────────────────────────

    def _show_alarm_dialog(self, state_name: str, play_sound: bool = True) -> None:
        state_display = {
            "work":        "Work Time",
            "short_break": "Short Break",
            "long_break":  "Long Break",
            "downtime":    "Downtime",
        }
        display_name = state_display.get(state_name, "Timer")

        if play_sound:
            sound_path = self._get_sound_path(state_name)
            if sound_path:
                try:
                    self.media_player.setSource(QUrl.fromLocalFile(sound_path))
                    self.media_player.play()
                except Exception:
                    pass

        if self.isMinimized():
            self.showNormal()
        self.raise_()
        self.activateWindow()

        self.alarm_dialog = AlarmDialog(self, display_name, self.media_player)
        self.alarm_dialog.exec()
        if self.media_player:
            self.media_player.stop()

    # ── Downtime tracking ─────────────────────────────────────────────────────

    def _start_downtime(self) -> None:
        self.is_downtime_active     = True
        self.downtime_seconds       = 0
        self.last_notification_time = 0
        self.remaining_seconds      = 0
        if not self.timer.isActive():
            self.timer.start(1000)

    def _stop_downtime(self) -> None:
        self.is_downtime_active     = False
        self.downtime_seconds       = 0
        self.last_notification_time = 0

    # ── State load / refresh ──────────────────────────────────────────────────

    def _load_state(self) -> None:
        self.state             = TimerState.WORK
        self.remaining_seconds = self._get_timer_duration()
        self.previous_state    = self.state
        self._update_display()
        self._apply_state_style()

    def refresh_settings(self) -> None:
        """Reload settings from the database (called after Settings dialog closes)."""
        self.settings = self._load_settings()
        if hasattr(self, "downtime_container"):
            self.downtime_container.setVisible(self.settings.enable_downtime)
        if not self.timer.isActive():
            self._load_state()

    # ── Responsive compact mode ───────────────────────────────────────────────

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_ui_for_size()

    def _update_ui_for_size(self) -> None:
        compact = self.height() < 200 or self.width() < 300
        for attr in ("schedule_now_label", "sessions_label", "session_dots",
                     "downtime_container", "start_button", "pause_button",
                     "reset_button", "skip_button", "mute_button"):
            widget = getattr(self, attr, None)
            if widget:
                widget.setVisible(not compact)

    def closeEvent(self, event) -> None:
        if self.tray_icon and self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()
