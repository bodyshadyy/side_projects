"""
Statistics tab for Pomodoro app.

Displays a 7-day bar chart of work sessions, today's summary, all-time
totals, and a consecutive-day streak counter.  All data is read from the
session_history table via the Database singleton.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QFrame, QScrollArea, QGraphicsDropShadowEffect,
                              QSizePolicy)
from PyQt6.QtCore import Qt, QRectF, QTimer
from PyQt6.QtGui import QFont, QColor, QPainter, QPen, QBrush, QLinearGradient
from datetime import date, timedelta
from database import Database
from theme import COLORS


# ── Helpers ───────────────────────────────────────────────────────────────────

def _shadow(blur=16, dy=3, alpha=20):
    fx = QGraphicsDropShadowEffect()
    fx.setBlurRadius(blur)
    fx.setXOffset(0)
    fx.setYOffset(dy)
    fx.setColor(QColor(0, 0, 0, alpha))
    return fx


def _fmt_seconds(s: int) -> str:
    """Format seconds as 'Xh Ym' or 'Ym'."""
    s = int(s or 0)
    h, m = divmod(s // 60, 60)
    if h:
        return f"{h}h {m}m"
    return f"{m}m"


# ── Stat card ─────────────────────────────────────────────────────────────────

class StatCard(QFrame):
    """A single metric card showing a number + label."""

    def __init__(self, label: str, value: str, color: str = None, parent=None):
        super().__init__(parent)
        self.setObjectName("statCard")
        self.setGraphicsEffect(_shadow())
        self.setStyleSheet(f"""
            #statCard {{
                background-color: {COLORS['surface']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        val_lbl = QLabel(value)
        vf = QFont()
        vf.setPointSize(28)
        vf.setBold(True)
        val_lbl.setFont(vf)
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val_lbl.setStyleSheet(f"color: {color or COLORS['accent']};")
        layout.addWidget(val_lbl)

        lbl = QLabel(label)
        lf = QFont()
        lf.setPointSize(11)
        lbl.setFont(lf)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"color: {COLORS['text_sec']};")
        layout.addWidget(lbl)

        self.value_label = val_lbl

    def set_value(self, value: str):
        self.value_label.setText(value)


# ── 7-day bar chart ───────────────────────────────────────────────────────────

class WeekBarChart(QWidget):
    """Custom-drawn 7-day bar chart of completed work sessions."""

    BAR_GAP = 10
    LABEL_H = 24
    VALUE_H = 20
    MIN_H   = 200

    def __init__(self, parent=None):
        super().__init__(parent)
        self._days: list[str] = []    # 7 short day labels e.g. "Mon"
        self._counts: list[int] = []  # session counts per day
        self._today_idx: int = 6      # index of today in the 7-day window
        self.setMinimumHeight(self.MIN_H)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_data(self, days: list[str], counts: list[int], today_idx: int = 6):
        self._days    = days
        self._counts  = counts
        self._today_idx = today_idx
        self.update()

    def paintEvent(self, event):
        if not self._counts:
            return

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        n          = len(self._counts)
        w, h       = self.width(), self.height()
        chart_h    = h - self.LABEL_H - self.VALUE_H - 8
        total_gap  = self.BAR_GAP * (n + 1)
        bar_w      = max(8, (w - total_gap) // n)
        max_count  = max(self._counts) if any(self._counts) else 1

        for i, (day, count) in enumerate(zip(self._days, self._counts)):
            x        = self.BAR_GAP + i * (bar_w + self.BAR_GAP)
            ratio    = count / max_count if max_count else 0
            bar_h    = max(4, int(chart_h * ratio))
            bar_y    = self.VALUE_H + (chart_h - bar_h)

            # Bar fill — gradient
            is_today = (i == self._today_idx)
            color    = QColor(COLORS['accent'] if is_today else COLORS['short_break'])
            color.setAlpha(220 if is_today else 160)

            grad = QLinearGradient(x, bar_y, x, bar_y + bar_h)
            grad.setColorAt(0, color)
            light = QColor(color)
            light.setAlpha(80)
            grad.setColorAt(1, light)

            p.setBrush(QBrush(grad))
            p.setPen(Qt.PenStyle.NoPen)
            radius = min(6, bar_w // 4)
            p.drawRoundedRect(int(x), int(bar_y), int(bar_w), int(bar_h), radius, radius)

            # Session count above bar
            if count > 0:
                p.setPen(QColor(COLORS['text_sec']))
                cf = QFont()
                cf.setPointSize(9)
                cf.setBold(True)
                p.setFont(cf)
                p.drawText(int(x), 0, int(bar_w), self.VALUE_H,
                           Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom,
                           str(count))

            # Day label below bar
            label_y = self.VALUE_H + chart_h + 4
            lf = QFont()
            lf.setPointSize(9)
            lf.setBold(is_today)
            p.setFont(lf)
            p.setPen(QColor(COLORS['accent'] if is_today else COLORS['text_sec']))
            p.drawText(int(x), int(label_y), int(bar_w), self.LABEL_H,
                       Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
                       day)

        p.end()


# ── Main widget ───────────────────────────────────────────────────────────────

class StatsWidget(QWidget):
    """Statistics overview tab."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = Database()
        self._init_ui()
        self.refresh()

        # Auto-refresh every 60 seconds so newly completed sessions appear.
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(60_000)

    # ── UI construction ───────────────────────────────────────────────────────

    def _init_ui(self):
        self.setStyleSheet(f"QWidget {{ background-color: {COLORS['bg']}; }}")

        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        header.setGraphicsEffect(_shadow())
        hb = QVBoxLayout(header)
        hb.setContentsMargins(28, 20, 28, 16)
        hb.setSpacing(4)

        title = QLabel("Statistics")
        tf = QFont()
        tf.setPointSize(22)
        tf.setBold(True)
        title.setFont(tf)
        title.setStyleSheet(f"color: {COLORS['text']};")
        hb.addWidget(title)

        subtitle = QLabel("Your focus history at a glance.")
        subtitle.setStyleSheet(f"color: {COLORS['text_sec']}; font-size: 12px;")
        hb.addWidget(subtitle)

        root.addWidget(header)

        # Scrollable body
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("border: none;")

        body_widget = QWidget()
        body_widget.setStyleSheet(f"background-color: {COLORS['bg']};")
        body = QVBoxLayout(body_widget)
        body.setSpacing(20)
        body.setContentsMargins(28, 24, 28, 28)

        # ── Today row ─────────────────────────────────────────────────────────
        today_lbl = QLabel("Today")
        today_lbl.setStyleSheet(
            f"color: {COLORS['text_sec']}; font-size: 12px; font-weight: 700; letter-spacing: 1px;"
        )
        body.addWidget(today_lbl)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)

        self.card_sessions = StatCard("Pomodoros", "0", COLORS['work'])
        self.card_focus    = StatCard("Focus Time", "0m", COLORS['accent'])
        self.card_streak   = StatCard("Day Streak", "0", COLORS['success'])

        for card in (self.card_sessions, self.card_focus, self.card_streak):
            cards_row.addWidget(card, 1)
        body.addLayout(cards_row)

        # ── 7-day chart ───────────────────────────────────────────────────────
        week_lbl = QLabel("Last 7 Days — Work Sessions")
        week_lbl.setStyleSheet(
            f"color: {COLORS['text_sec']}; font-size: 12px; font-weight: 700; letter-spacing: 1px;"
        )
        body.addWidget(week_lbl)

        chart_card = QFrame()
        chart_card.setObjectName("chartCard")
        chart_card.setGraphicsEffect(_shadow())
        chart_card.setStyleSheet(f"""
            #chartCard {{
                background-color: {COLORS['surface']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        chart_card_layout = QVBoxLayout(chart_card)
        chart_card_layout.setContentsMargins(20, 20, 20, 16)

        self.bar_chart = WeekBarChart()
        self.bar_chart.setMinimumHeight(180)
        chart_card_layout.addWidget(self.bar_chart)

        body.addWidget(chart_card)

        # ── All-time row ──────────────────────────────────────────────────────
        alltime_lbl = QLabel("All Time")
        alltime_lbl.setStyleSheet(
            f"color: {COLORS['text_sec']}; font-size: 12px; font-weight: 700; letter-spacing: 1px;"
        )
        body.addWidget(alltime_lbl)

        alltime_row = QHBoxLayout()
        alltime_row.setSpacing(14)

        self.card_total_sessions = StatCard("Total Pomodoros", "0", COLORS['work'])
        self.card_total_focus    = StatCard("Total Focus Time", "0h", COLORS['accent'])
        self.card_active_days    = StatCard("Active Days", "0", COLORS['short_break'])

        for card in (self.card_total_sessions, self.card_total_focus, self.card_active_days):
            alltime_row.addWidget(card, 1)
        body.addLayout(alltime_row)

        body.addStretch()
        scroll.setWidget(body_widget)
        root.addWidget(scroll, 1)

    # ── Data refresh ──────────────────────────────────────────────────────────

    def refresh(self):
        today = date.today()

        # Today stats
        today_str    = today.strftime("%Y-%m-%d")
        today_rows   = self.db.get_sessions_for_date(today_str)
        work_today   = [r for r in today_rows if r['state'] == 'work']
        focus_today  = sum(r['duration_seconds'] for r in work_today)
        streak       = self.db.get_streak_days()

        self.card_sessions.set_value(str(len(work_today)))
        self.card_focus.set_value(_fmt_seconds(focus_today))
        self.card_streak.set_value(str(streak))

        # 7-day chart
        start = today - timedelta(days=6)
        daily = self.db.get_daily_stats(
            start.strftime("%Y-%m-%d"), today_str
        )
        daily_map = {r['day']: r['work_sessions'] for r in daily}

        day_labels, counts = [], []
        for i in range(7):
            d = start + timedelta(days=i)
            day_labels.append(d.strftime("%a"))
            counts.append(int(daily_map.get(d.strftime("%Y-%m-%d"), 0)))

        self.bar_chart.set_data(day_labels, counts, today_idx=6)

        # All-time stats
        ats = self.db.get_all_time_stats()
        self.card_total_sessions.set_value(str(int(ats.get('work_sessions') or 0)))
        self.card_total_focus.set_value(_fmt_seconds(ats.get('total_focus_seconds') or 0))
        self.card_active_days.set_value(str(int(ats.get('active_days') or 0)))
