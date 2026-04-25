"""
Prayer Times for Egypt (Cairo) with Google Calendar sync.

- Fetches daily prayer times from api.aladhan.com (no API key needed).
- Creates 15-min Google Calendar events for each prayer (skips duplicates).
- Adds prayers as todos in the local DB.
- Refreshes automatically at midnight.
"""
import json
import urllib.request
import urllib.error
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QFrame, QScrollArea,
                              QGraphicsDropShadowEffect)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QTime
from PyQt6.QtGui import QFont, QColor
from theme import COLORS
from database import Database

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    _GCAL_OK = True
except ImportError:
    _GCAL_OK = False

CAIRO_TZ  = ZoneInfo("Africa/Cairo")
_DATA_DIR  = Path(__file__).parent / "data"
_TOKEN     = _DATA_DIR / "google_token.json"
_SCOPES    = ["https://www.googleapis.com/auth/calendar.events"]
_PRAYERS   = ("Fajr", "Sunrise", "Dhuhr", "Asr", "Maghrib", "Isha")
_PRAYER_EMOJI = {
    "Fajr":    "🌙",
    "Sunrise": "🌅",
    "Dhuhr":   "☀️",
    "Asr":     "🌤️",
    "Maghrib": "🌇",
    "Isha":    "🌃",
}
_CALENDAR_ID = "primary"
_cfg = _DATA_DIR / "google_calendar_config.json"
if _cfg.exists():
    try:
        _CALENDAR_ID = json.loads(_cfg.read_text()).get("calendar_id", "primary")
    except Exception:
        pass


# ── Backend helpers ───────────────────────────────────────────────────────────

def _get_service():
    if not _GCAL_OK:
        raise RuntimeError("Google API packages not installed.")
    creds = Credentials.from_authorized_user_file(str(_TOKEN), _SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _TOKEN.write_text(creds.to_json())
    return build("calendar", "v3", credentials=creds)


def fetch_prayer_times(for_date: date | None = None) -> dict[str, str]:
    """Return {prayer_name: 'HH:MM'} for Cairo. Raises on network failure."""
    d   = for_date or date.today()
    url = (
        f"https://api.aladhan.com/v1/timings/{d.strftime('%d-%m-%Y')}"
        "?latitude=30.0444&longitude=31.2357&method=5"
    )
    req = urllib.request.Request(url, headers={"User-Agent": "PomodoroApp/1.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        data = json.loads(r.read())
    timings = data["data"]["timings"]
    return {k: timings[k] for k in _PRAYERS}


def sync_prayers_to_calendar(for_date: date | None = None) -> tuple[int, int]:
    """Create Google Calendar events for each prayer. Returns (created, skipped)."""
    d       = for_date or date.today()
    prayers = fetch_prayer_times(d)
    service = _get_service()

    day_start = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=CAIRO_TZ).isoformat()
    day_end   = datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=CAIRO_TZ).isoformat()
    existing  = service.events().list(
        calendarId=_CALENDAR_ID,
        timeMin=day_start,
        timeMax=day_end,
        singleEvents=True,
    ).execute()
    existing_summaries = {e.get("summary", "") for e in existing.get("items", [])}

    created = skipped = 0
    for name, time_str in prayers.items():
        summary = f"{_PRAYER_EMOJI.get(name, '🕌')} {name} Prayer"
        if summary in existing_summaries:
            skipped += 1
            continue
        h, m   = map(int, time_str.split(":")[:2])
        start  = datetime(d.year, d.month, d.day, h, m, tzinfo=CAIRO_TZ)
        end    = start + timedelta(minutes=15)
        event  = {
            "summary": summary,
            "start":   {"dateTime": start.isoformat(), "timeZone": "Africa/Cairo"},
            "end":     {"dateTime": end.isoformat(),   "timeZone": "Africa/Cairo"},
            "colorId": "9",
            "reminders": {"useDefault": False, "overrides": []},
        }
        service.events().insert(calendarId=_CALENDAR_ID, body=event).execute()
        created += 1

    return created, skipped


def add_prayers_as_todos(db: Database, for_date: date | None = None) -> int:
    """Insert today's prayers into the todo table. Returns count inserted."""
    d        = for_date or date.today()
    date_str = d.strftime("%Y-%m-%d")
    prayers  = fetch_prayer_times(d)
    existing = {t["task"] for t in db.get_todos(date_str)}
    added    = 0
    for name, time_str in prayers.items():
        task = f"{_PRAYER_EMOJI.get(name, '🕌')} {name} Prayer — {time_str}"
        if task in existing:
            continue
        db.add_todo(task, date_str, priority=2)
        added += 1
    return added


# ── Background worker ─────────────────────────────────────────────────────────

class _SyncWorker(QThread):
    done    = pyqtSignal(str)
    error   = pyqtSignal(str)

    def __init__(self, do_gcal: bool, do_todos: bool, db: Database):
        super().__init__()
        self._do_gcal  = do_gcal
        self._do_todos = do_todos
        self._db       = db

    def run(self):
        try:
            prayers = fetch_prayer_times()
            lines   = []

            if self._do_todos:
                added = add_prayers_as_todos(self._db)
                lines.append(f"Added {added} prayer(s) to Todos.")

            if self._do_gcal:
                created, skipped = sync_prayers_to_calendar()
                lines.append(
                    f"Google Calendar: {created} created, {skipped} already existed."
                )

            # Store for widget to display times
            self.done.emit("\n".join(lines) if lines else "Done.")
        except urllib.error.URLError as e:
            self.error.emit(f"Network error: {e.reason}")
        except Exception as e:
            self.error.emit(str(e))


class _FetchWorker(QThread):
    done  = pyqtSignal(dict)
    error = pyqtSignal(str)

    def run(self):
        try:
            self.done.emit(fetch_prayer_times())
        except Exception as e:
            self.error.emit(str(e))


# ── Widget ────────────────────────────────────────────────────────────────────

def _shadow(blur=14, dy=2, alpha=18):
    fx = QGraphicsDropShadowEffect()
    fx.setBlurRadius(blur)
    fx.setXOffset(0); fx.setYOffset(dy)
    fx.setColor(QColor(0, 0, 0, alpha))
    return fx


class PrayerTimesWidget(QWidget):
    """Tab showing today's prayer times for Cairo with calendar/todo sync."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db        = Database()
        self._prayers  = {}
        self._worker   = None
        self._build_ui()
        self._refresh_times()

        # Refresh at midnight
        self._midnight_timer = QTimer(self)
        self._midnight_timer.timeout.connect(self._refresh_times)
        self._schedule_midnight()

        # Highlight next prayer every minute
        self._highlight_timer = QTimer(self)
        self._highlight_timer.timeout.connect(self._update_highlights)
        self._highlight_timer.start(60_000)

    # ── Construction ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.setStyleSheet(f"QWidget {{ background-color: {COLORS['bg']}; }}")
        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # Header bar
        hdr = QFrame()
        hdr.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        hdr.setGraphicsEffect(_shadow())
        hl = QVBoxLayout(hdr)
        hl.setContentsMargins(28, 20, 28, 18)
        hl.setSpacing(4)

        title = QLabel("Prayer Times — Cairo")
        tf = QFont(); tf.setPointSize(22); tf.setBold(True)
        title.setFont(tf)
        title.setStyleSheet(f"color: {COLORS['text']};")
        hl.addWidget(title)

        self._sub = QLabel("Loading prayer times…")
        self._sub.setStyleSheet(f"color: {COLORS['text_sec']}; font-size: 12px;")
        hl.addWidget(self._sub)
        root.addWidget(hdr)

        # Scroll area for prayer cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        inner = QWidget()
        inner.setStyleSheet(f"background: {COLORS['bg']};")
        self._cards_layout = QVBoxLayout(inner)
        self._cards_layout.setContentsMargins(28, 24, 28, 24)
        self._cards_layout.setSpacing(10)
        self._cards_layout.addStretch()
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        # Bottom action bar
        bar = QFrame()
        bar.setStyleSheet(f"""
            QFrame {{
                background: {COLORS['surface']};
                border-top: 1px solid {COLORS['border']};
            }}
        """)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(28, 12, 28, 12)
        bl.setSpacing(10)

        self._gcal_btn = QPushButton("📅  Sync to Google Calendar")
        self._gcal_btn.setFixedHeight(38)
        self._gcal_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._gcal_btn.clicked.connect(lambda: self._sync(do_gcal=True, do_todos=False))
        self._gcal_btn.setStyleSheet(self._btn_style("#1a73e8"))
        bl.addWidget(self._gcal_btn)

        self._todo_btn = QPushButton("✅  Add to Todos")
        self._todo_btn.setFixedHeight(38)
        self._todo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._todo_btn.clicked.connect(lambda: self._sync(do_gcal=False, do_todos=True))
        self._todo_btn.setStyleSheet(self._btn_style(COLORS.get("success", "#22c55e")))
        bl.addWidget(self._todo_btn)

        self._both_btn = QPushButton("⚡  Sync Both")
        self._both_btn.setFixedHeight(38)
        self._both_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._both_btn.clicked.connect(lambda: self._sync(do_gcal=True, do_todos=True))
        self._both_btn.setStyleSheet(self._btn_style(COLORS.get("accent", "#6366f1")))
        bl.addWidget(self._both_btn)

        bl.addStretch()

        self._status = QLabel("")
        self._status.setStyleSheet(f"color: {COLORS['text_sec']}; font-size: 11px;")
        bl.addWidget(self._status)

        root.addWidget(bar)

    def _btn_style(self, color: str) -> str:
        return f"""
            QPushButton {{
                background: transparent;
                color: {color};
                border: 1.5px solid {color};
                border-radius: 8px;
                font-size: 12px;
                font-weight: 600;
                padding: 0 16px;
            }}
            QPushButton:hover   {{ background: {color}; color: white; }}
            QPushButton:pressed {{ background: {color}; color: white; opacity: 0.8; }}
            QPushButton:disabled {{ opacity: 0.4; }}
        """

    # ── Prayer card ───────────────────────────────────────────────────────────

    def _build_cards(self) -> None:
        # Remove old cards (keep stretch at end)
        while self._cards_layout.count() > 1:
            item = self._cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._card_widgets: dict[str, QFrame] = {}
        now = datetime.now(CAIRO_TZ).time()
        next_prayer = self._next_prayer_name(now)

        for name in _PRAYERS:
            time_str = self._prayers.get(name, "--:--")
            card = self._make_card(name, time_str, is_next=(name == next_prayer))
            self._cards_layout.insertWidget(self._cards_layout.count() - 1, card)
            self._card_widgets[name] = card

    def _make_card(self, name: str, time_str: str, is_next: bool) -> QFrame:
        accent = COLORS.get("accent", "#6366f1")
        surface = COLORS["surface"]
        border  = accent if is_next else COLORS["border"]
        bg      = COLORS.get("accent_light", "#ede9fe") if is_next else surface

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {bg};
                border: 1.5px solid {border};
                border-radius: 12px;
            }}
        """)
        card.setGraphicsEffect(_shadow())

        row = QHBoxLayout(card)
        row.setContentsMargins(20, 14, 20, 14)
        row.setSpacing(14)

        emoji_lbl = QLabel(_PRAYER_EMOJI.get(name, "🕌"))
        ef = QFont(); ef.setPointSize(20)
        emoji_lbl.setFont(ef)
        emoji_lbl.setStyleSheet("background: transparent; border: none;")
        row.addWidget(emoji_lbl)

        name_lbl = QLabel(name)
        nf = QFont(); nf.setPointSize(14); nf.setBold(True)
        name_lbl.setFont(nf)
        name_lbl.setStyleSheet(f"color: {COLORS['text']}; background: transparent; border: none;")
        row.addWidget(name_lbl)

        if is_next:
            badge = QLabel("  next  ")
            badge.setStyleSheet(f"""
                background: {accent}; color: white;
                border-radius: 6px; font-size: 10px; font-weight: 700;
                padding: 2px 6px; border: none;
            """)
            row.addWidget(badge)

        row.addStretch()

        time_lbl = QLabel(self._format_time(time_str))
        tf = QFont(); tf.setPointSize(16); tf.setBold(True)
        time_lbl.setFont(tf)
        time_lbl.setStyleSheet(f"color: {accent if is_next else COLORS['text']}; background: transparent; border: none;")
        row.addWidget(time_lbl)

        return card

    def _format_time(self, hhmm: str) -> str:
        try:
            h, m = map(int, hhmm.split(":")[:2])
            suffix = "AM" if h < 12 else "PM"
            h12    = h % 12 or 12
            return f"{h12}:{m:02d} {suffix}"
        except Exception:
            return hhmm

    def _next_prayer_name(self, now: QTime | None = None) -> str | None:
        if not self._prayers:
            return None
        t = datetime.now(CAIRO_TZ).time() if now is None else now
        for name in _PRAYERS:
            ts = self._prayers.get(name, "")
            if not ts:
                continue
            try:
                h, m = map(int, ts.split(":")[:2])
                if (h, m) > (t.hour, t.minute):
                    return name
            except Exception:
                pass
        return None

    # ── Data loading ──────────────────────────────────────────────────────────

    def _refresh_times(self) -> None:
        self._sub.setText("Loading…")
        w = _FetchWorker(self)
        w.done.connect(self._on_times_loaded)
        w.error.connect(self._on_fetch_error)
        w.finished.connect(w.deleteLater)
        w.start()

    def _on_times_loaded(self, prayers: dict) -> None:
        self._prayers = prayers
        today = date.today().strftime("%A, %d %B %Y")
        self._sub.setText(f"Cairo  ·  {today}  ·  Method: Egyptian General Authority of Survey")
        self._build_cards()
        self._schedule_midnight()

    def _on_fetch_error(self, msg: str) -> None:
        self._sub.setText(f"Could not load prayer times: {msg}")

    def _update_highlights(self) -> None:
        if not self._prayers:
            return
        now         = datetime.now(CAIRO_TZ).time()
        next_prayer = self._next_prayer_name(now)
        for name, card in getattr(self, "_card_widgets", {}).items():
            is_next = name == next_prayer
            accent  = COLORS.get("accent", "#6366f1")
            bg      = COLORS.get("accent_light", "#ede9fe") if is_next else COLORS["surface"]
            border  = accent if is_next else COLORS["border"]
            card.setStyleSheet(f"""
                QFrame {{
                    background: {bg};
                    border: 1.5px solid {border};
                    border-radius: 12px;
                }}
            """)

    # ── Sync ──────────────────────────────────────────────────────────────────

    def _sync(self, do_gcal: bool, do_todos: bool) -> None:
        for b in (self._gcal_btn, self._todo_btn, self._both_btn):
            b.setEnabled(False)
        self._status.setText("Syncing…")

        self._worker = _SyncWorker(do_gcal, do_todos, self.db)
        self._worker.done.connect(self._on_sync_done)
        self._worker.error.connect(self._on_sync_error)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def _on_sync_done(self, msg: str) -> None:
        self._status.setText(msg)
        for b in (self._gcal_btn, self._todo_btn, self._both_btn):
            b.setEnabled(True)
        QTimer.singleShot(6000, lambda: self._status.setText(""))

    def _on_sync_error(self, msg: str) -> None:
        self._status.setText(f"Error: {msg}")
        for b in (self._gcal_btn, self._todo_btn, self._both_btn):
            b.setEnabled(True)

    # ── Midnight refresh ──────────────────────────────────────────────────────

    def _schedule_midnight(self) -> None:
        now  = datetime.now(CAIRO_TZ)
        tomorrow = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=5, microsecond=0
        )
        ms = int((tomorrow - now).total_seconds() * 1000)
        self._midnight_timer.setSingleShot(True)
        self._midnight_timer.start(max(ms, 1000))
