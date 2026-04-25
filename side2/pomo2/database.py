"""
Database module for Pomodoro app.
Handles SQLite database operations for settings, notes, todos, schedule, and session history.
"""
import sqlite3
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta


class Database:
    """Singleton database class for managing SQLite operations."""

    _instance = None
    _connection = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._connection is None:
            self._init_database()

    def _get_db_path(self) -> str:
        data_dir = Path(__file__).parent / "data"
        data_dir.mkdir(exist_ok=True)
        return str(data_dir / "pomodoro.db")

    def _init_database(self):
        db_path = self._get_db_path()
        self._connection = sqlite3.connect(db_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._create_tables()
        self._run_migrations()
        self._init_defaults()

    # ── Schema creation ───────────────────────────────────────────────────────

    def _create_tables(self):
        c = self._connection.cursor()

        c.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY,
                work_time INTEGER NOT NULL DEFAULT 1500,
                short_break INTEGER NOT NULL DEFAULT 300,
                long_break INTEGER NOT NULL DEFAULT 900,
                downtime INTEGER NOT NULL DEFAULT 0,
                auto_start BOOLEAN NOT NULL DEFAULT 0,
                enable_downtime BOOLEAN NOT NULL DEFAULT 1,
                alarm_sound_path TEXT DEFAULT '',
                short_break_sound_path TEXT DEFAULT '',
                long_break_sound_path TEXT DEFAULT '',
                downtime_sound_path TEXT DEFAULT '',
                downtime_notify_threshold INTEGER NOT NULL DEFAULT 300,
                switch_desktop BOOLEAN NOT NULL DEFAULT 0,
                work_desktop INTEGER NOT NULL DEFAULT 1,
                break_desktop INTEGER NOT NULL DEFAULT 2
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                note TEXT NOT NULL DEFAULT ''
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                completed BOOLEAN NOT NULL DEFAULT 0,
                date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 1,
                is_repeatable BOOLEAN NOT NULL DEFAULT 0,
                repeat_type TEXT DEFAULT '',
                last_repeated_date TEXT DEFAULT ''
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS eisenhower_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                quadrant INTEGER NOT NULL DEFAULT 1,
                completed BOOLEAN NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS schedule_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL DEFAULT 30,
                is_fixed_time BOOLEAN NOT NULL DEFAULT 0,
                fixed_time TEXT DEFAULT '',
                fixed_time_end TEXT DEFAULT '',
                offset_minutes INTEGER NOT NULL DEFAULT 0,
                anchor_type TEXT NOT NULL DEFAULT 'wake_up',
                anchor_task_id INTEGER,
                sort_order INTEGER NOT NULL DEFAULT 0
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS schedule_wakeup (
                date TEXT PRIMARY KEY,
                wake_time TEXT NOT NULL
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS super_focus_settings (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                enabled BOOLEAN NOT NULL DEFAULT 0,
                duration_minutes INTEGER NOT NULL DEFAULT 60
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS session_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                state TEXT NOT NULL,
                duration_seconds INTEGER NOT NULL,
                completed_at TEXT NOT NULL
            )
        """)

        self._connection.commit()

    # ── Migrations (idempotent ALTER TABLE calls) ─────────────────────────────

    def _try_alter(self, sql: str):
        try:
            self._connection.cursor().execute(sql)
        except sqlite3.OperationalError:
            pass

    def _run_migrations(self):
        # schedule_tasks extras
        self._try_alter("ALTER TABLE schedule_tasks ADD COLUMN fixed_time_end TEXT DEFAULT ''")
        self._try_alter("ALTER TABLE schedule_tasks ADD COLUMN anchor_type TEXT NOT NULL DEFAULT 'wake_up'")
        self._try_alter("ALTER TABLE schedule_tasks ADD COLUMN anchor_task_id INTEGER")
        # settings extras
        self._try_alter("ALTER TABLE settings ADD COLUMN alarm_sound_path TEXT DEFAULT ''")
        self._try_alter("ALTER TABLE settings ADD COLUMN short_break_sound_path TEXT DEFAULT ''")
        self._try_alter("ALTER TABLE settings ADD COLUMN long_break_sound_path TEXT DEFAULT ''")
        self._try_alter("ALTER TABLE settings ADD COLUMN downtime_sound_path TEXT DEFAULT ''")
        self._try_alter("ALTER TABLE settings ADD COLUMN downtime_notify_threshold INTEGER NOT NULL DEFAULT 300")
        self._try_alter("ALTER TABLE settings ADD COLUMN switch_desktop BOOLEAN NOT NULL DEFAULT 0")
        self._try_alter("ALTER TABLE settings ADD COLUMN work_desktop INTEGER NOT NULL DEFAULT 1")
        self._try_alter("ALTER TABLE settings ADD COLUMN break_desktop INTEGER NOT NULL DEFAULT 2")
        # todos extras
        self._try_alter("ALTER TABLE todos ADD COLUMN priority INTEGER NOT NULL DEFAULT 1")
        self._try_alter("ALTER TABLE todos ADD COLUMN is_repeatable BOOLEAN NOT NULL DEFAULT 0")
        self._try_alter("ALTER TABLE todos ADD COLUMN repeat_type TEXT DEFAULT ''")
        self._try_alter("ALTER TABLE todos ADD COLUMN last_repeated_date TEXT DEFAULT ''")
        self._connection.commit()

    # ── Default data ──────────────────────────────────────────────────────────

    def _init_defaults(self):
        c = self._connection.cursor()

        c.execute("SELECT COUNT(*) FROM settings")
        if c.fetchone()[0] == 0:
            c.execute("""
                INSERT INTO settings (id, work_time, short_break, long_break,
                    downtime, auto_start, enable_downtime, alarm_sound_path,
                    short_break_sound_path, long_break_sound_path, downtime_sound_path,
                    downtime_notify_threshold, switch_desktop, work_desktop, break_desktop)
                VALUES (1, 1500, 300, 900, 0, 0, 1, '', '', '', '', 300, 0, 1, 2)
            """)
        else:
            # Migrate old minute-based defaults (25/5/15) to seconds.
            c.execute("SELECT work_time, short_break, long_break FROM settings WHERE id = 1")
            row = c.fetchone()
            if row and row['work_time'] == 25 and row['short_break'] == 5 and row['long_break'] == 15:
                c.execute("""
                    UPDATE settings SET
                        work_time = work_time * 60,
                        short_break = short_break * 60,
                        long_break = long_break * 60,
                        downtime = CASE WHEN downtime > 0 THEN downtime * 60 ELSE downtime END
                    WHERE id = 1
                """)

        c.execute("SELECT COUNT(*) FROM super_focus_settings")
        if c.fetchone()[0] == 0:
            c.execute("INSERT INTO super_focus_settings (id, enabled, duration_minutes) VALUES (1, 0, 60)")

        self._connection.commit()

    def get_connection(self):
        return self._connection

    # ── Settings ──────────────────────────────────────────────────────────────

    def get_settings(self) -> Optional[Dict[str, Any]]:
        c = self._connection.cursor()
        c.execute("SELECT * FROM settings WHERE id = 1")
        row = c.fetchone()
        if not row:
            return None
        keys = [
            'id', 'work_time', 'short_break', 'long_break', 'downtime',
            'auto_start', 'enable_downtime', 'alarm_sound_path',
            'short_break_sound_path', 'long_break_sound_path', 'downtime_sound_path',
            'downtime_notify_threshold', 'switch_desktop', 'work_desktop', 'break_desktop',
        ]
        result = {}
        for k in keys:
            try:
                result[k] = row[k]
            except (IndexError, KeyError):
                pass
        result.setdefault('alarm_sound_path', '')
        result.setdefault('short_break_sound_path', '')
        result.setdefault('long_break_sound_path', '')
        result.setdefault('downtime_sound_path', '')
        result.setdefault('downtime_notify_threshold', 300)
        result.setdefault('switch_desktop', False)
        result.setdefault('work_desktop', 1)
        result.setdefault('break_desktop', 2)
        result['auto_start'] = bool(result.get('auto_start', False))
        result['enable_downtime'] = bool(result.get('enable_downtime', True))
        result['switch_desktop'] = bool(result.get('switch_desktop', False))
        return result

    def update_settings(self, settings: Dict[str, Any]):
        c = self._connection.cursor()
        c.execute("PRAGMA table_info(settings)")
        existing = {col[1] for col in c.fetchall()}

        field_map = {
            'work_time':                 settings.get('work_time', 1500),
            'short_break':               settings.get('short_break', 300),
            'long_break':                settings.get('long_break', 900),
            'downtime':                  settings.get('downtime', 0),
            'auto_start':                1 if settings.get('auto_start') else 0,
            'enable_downtime':           1 if settings.get('enable_downtime') else 0,
            'alarm_sound_path':          settings.get('alarm_sound_path', ''),
            'short_break_sound_path':    settings.get('short_break_sound_path', ''),
            'long_break_sound_path':     settings.get('long_break_sound_path', ''),
            'downtime_sound_path':       settings.get('downtime_sound_path', ''),
            'downtime_notify_threshold': settings.get('downtime_notify_threshold', 300),
            'switch_desktop':            1 if settings.get('switch_desktop') else 0,
            'work_desktop':              settings.get('work_desktop', 1),
            'break_desktop':             settings.get('break_desktop', 2),
        }

        updates = [(col, val) for col, val in field_map.items() if col in existing]
        if not updates:
            return
        set_clause = ', '.join(f"{col} = ?" for col, _ in updates)
        values = [val for _, val in updates] + [1]
        c.execute(f"UPDATE settings SET {set_clause} WHERE id = ?", values)
        self._connection.commit()

    # ── Notes ─────────────────────────────────────────────────────────────────

    def get_note(self, date_str: str) -> Optional[str]:
        c = self._connection.cursor()
        c.execute("SELECT note FROM notes WHERE date = ?", (date_str,))
        row = c.fetchone()
        return row['note'] if row else None

    def save_note(self, date_str: str, note: str):
        c = self._connection.cursor()
        c.execute("""
            INSERT INTO notes (date, note) VALUES (?, ?)
            ON CONFLICT(date) DO UPDATE SET note = ?
        """, (date_str, note, note))
        self._connection.commit()

    def get_all_notes(self) -> List[Dict[str, Any]]:
        c = self._connection.cursor()
        c.execute("SELECT * FROM notes ORDER BY date DESC")
        return [dict(row) for row in c.fetchall()]

    # ── Todos ─────────────────────────────────────────────────────────────────

    def add_todo(self, task: str, date_str: str, priority: int = 1,
                 is_repeatable: bool = False, repeat_type: str = '') -> int:
        c = self._connection.cursor()
        c.execute("""
            INSERT INTO todos (task, completed, date, created_at, priority, is_repeatable, repeat_type)
            VALUES (?, 0, ?, ?, ?, ?, ?)
        """, (task, date_str, datetime.now().isoformat(),
              priority, 1 if is_repeatable else 0, repeat_type))
        self._connection.commit()
        return c.lastrowid

    def get_todos(self, date_str: Optional[str] = None) -> List[Dict[str, Any]]:
        c = self._connection.cursor()
        order = "ORDER BY priority DESC, date DESC, created_at DESC"
        if date_str:
            c.execute(f"SELECT * FROM todos WHERE date = ? {order}", (date_str,))
        else:
            c.execute(f"SELECT * FROM todos {order}")
        todos = []
        for row in c.fetchall():
            d = dict(row)
            d.setdefault('priority', 1)
            d.setdefault('is_repeatable', False)
            d.setdefault('repeat_type', '')
            d.setdefault('last_repeated_date', '')
            todos.append(d)
        return todos

    def update_todo(self, todo_id: int, task: Optional[str] = None,
                    completed: Optional[bool] = None, priority: Optional[int] = None,
                    is_repeatable: Optional[bool] = None, repeat_type: Optional[str] = None):
        updates, values = [], []
        if task is not None:
            updates.append("task = ?"); values.append(task)
        if completed is not None:
            updates.append("completed = ?"); values.append(1 if completed else 0)
        if priority is not None:
            updates.append("priority = ?"); values.append(priority)
        if is_repeatable is not None:
            updates.append("is_repeatable = ?"); values.append(1 if is_repeatable else 0)
        if repeat_type is not None:
            updates.append("repeat_type = ?"); values.append(repeat_type)
        if not updates:
            return
        values.append(todo_id)
        self._connection.cursor().execute(
            f"UPDATE todos SET {', '.join(updates)} WHERE id = ?", values)
        self._connection.commit()

    def handle_repeatable_todos(self):
        c = self._connection.cursor()
        today = datetime.now().date().strftime("%Y-%m-%d")
        c.execute("SELECT * FROM todos WHERE is_repeatable = 1 AND completed = 1")
        for row in c.fetchall():
            todo = dict(row)
            last = todo.get('last_repeated_date') or todo.get('date', '')
            rtype = todo.get('repeat_type', 'daily')
            if not last:
                continue
            try:
                last_date = datetime.strptime(last, "%Y-%m-%d").date()
                today_date = datetime.strptime(today, "%Y-%m-%d").date()
                thresholds = {'daily': 1, 'weekly': 7, 'monthly': 30}
                if (today_date - last_date).days >= thresholds.get(rtype, 1):
                    c.execute("""
                        INSERT INTO todos (task, completed, date, created_at, priority, is_repeatable, repeat_type)
                        VALUES (?, 0, ?, ?, ?, 1, ?)
                    """, (todo['task'], today, datetime.now().isoformat(),
                          todo.get('priority', 1), rtype))
                    c.execute("UPDATE todos SET last_repeated_date = ? WHERE id = ?",
                              (today, todo['id']))
            except (ValueError, KeyError):
                continue
        self._connection.commit()

    def delete_todo(self, todo_id: int):
        self._connection.cursor().execute("DELETE FROM todos WHERE id = ?", (todo_id,))
        self._connection.commit()

    # ── Eisenhower ────────────────────────────────────────────────────────────

    def add_eisenhower_task(self, task: str, quadrant: int) -> int:
        c = self._connection.cursor()
        c.execute("""
            INSERT INTO eisenhower_tasks (task, quadrant, completed, created_at)
            VALUES (?, ?, 0, ?)
        """, (task, quadrant, datetime.now().isoformat()))
        self._connection.commit()
        return c.lastrowid

    def get_eisenhower_tasks(self, quadrant: Optional[int] = None) -> List[Dict[str, Any]]:
        c = self._connection.cursor()
        if quadrant is not None:
            c.execute("""
                SELECT * FROM eisenhower_tasks WHERE quadrant = ?
                ORDER BY completed ASC, created_at DESC
            """, (quadrant,))
        else:
            c.execute("""
                SELECT * FROM eisenhower_tasks
                ORDER BY quadrant ASC, completed ASC, created_at DESC
            """)
        return [dict(row) for row in c.fetchall()]

    def update_eisenhower_task(self, task_id: int, task: Optional[str] = None,
                               quadrant: Optional[int] = None,
                               completed: Optional[bool] = None):
        updates, values = [], []
        if task is not None:
            updates.append("task = ?"); values.append(task)
        if quadrant is not None:
            updates.append("quadrant = ?"); values.append(quadrant)
        if completed is not None:
            updates.append("completed = ?"); values.append(1 if completed else 0)
        if not updates:
            return
        values.append(task_id)
        self._connection.cursor().execute(
            f"UPDATE eisenhower_tasks SET {', '.join(updates)} WHERE id = ?", values)
        self._connection.commit()

    def delete_eisenhower_task(self, task_id: int):
        self._connection.cursor().execute("DELETE FROM eisenhower_tasks WHERE id = ?", (task_id,))
        self._connection.commit()

    # ── Schedule ──────────────────────────────────────────────────────────────

    def add_schedule_task(self, task: str, duration_minutes: int = 30,
                          is_fixed_time: bool = False, fixed_time: str = '',
                          fixed_time_end: str = '', offset_minutes: int = 0,
                          anchor_type: str = 'wake_up',
                          anchor_task_id: Optional[int] = None) -> int:
        c = self._connection.cursor()
        c.execute("SELECT COALESCE(MAX(sort_order), -1) + 1 FROM schedule_tasks")
        sort_order = c.fetchone()[0]
        c.execute("""
            INSERT INTO schedule_tasks
                (task, duration_minutes, is_fixed_time, fixed_time, fixed_time_end,
                 offset_minutes, anchor_type, anchor_task_id, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (task, duration_minutes, 1 if is_fixed_time else 0,
              fixed_time, fixed_time_end, offset_minutes,
              anchor_type, anchor_task_id, sort_order))
        self._connection.commit()
        return c.lastrowid

    def get_schedule_tasks(self) -> List[Dict[str, Any]]:
        c = self._connection.cursor()
        c.execute("SELECT * FROM schedule_tasks ORDER BY sort_order ASC")
        return [dict(row) for row in c.fetchall()]

    def update_schedule_task(self, task_id: int, **kwargs):
        if not kwargs:
            return
        c = self._connection.cursor()
        bool_cols = {'is_fixed_time'}
        updates, values = [], []
        for col, val in kwargs.items():
            updates.append(f"{col} = ?")
            values.append(1 if val else 0 if col in bool_cols else val)
        values.append(task_id)
        c.execute(f"UPDATE schedule_tasks SET {', '.join(updates)} WHERE id = ?", values)
        self._connection.commit()

    def delete_schedule_task(self, task_id: int):
        self._connection.cursor().execute("DELETE FROM schedule_tasks WHERE id = ?", (task_id,))
        self._connection.commit()

    def set_wakeup_time(self, date_str: str, wake_time: str):
        c = self._connection.cursor()
        c.execute("""
            INSERT INTO schedule_wakeup (date, wake_time) VALUES (?, ?)
            ON CONFLICT(date) DO UPDATE SET wake_time = ?
        """, (date_str, wake_time, wake_time))
        self._connection.commit()

    def get_wakeup_time(self, date_str: str) -> Optional[str]:
        c = self._connection.cursor()
        c.execute("SELECT wake_time FROM schedule_wakeup WHERE date = ?", (date_str,))
        row = c.fetchone()
        return row['wake_time'] if row else None

    # ── Super Focus ───────────────────────────────────────────────────────────

    def get_super_focus_settings(self) -> Dict[str, Any]:
        c = self._connection.cursor()
        c.execute("SELECT enabled, duration_minutes FROM super_focus_settings WHERE id = 1")
        row = c.fetchone()
        if not row:
            return {'enabled': False, 'duration_minutes': 60}
        return {'enabled': bool(row['enabled']),
                'duration_minutes': max(1, int(row['duration_minutes']))}

    def update_super_focus_settings(self, enabled: bool, duration_minutes: int):
        c = self._connection.cursor()
        c.execute("""
            INSERT INTO super_focus_settings (id, enabled, duration_minutes)
            VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                enabled = excluded.enabled,
                duration_minutes = excluded.duration_minutes
        """, (1 if enabled else 0, max(1, int(duration_minutes))))
        self._connection.commit()

    # ── Session History ───────────────────────────────────────────────────────

    def log_session(self, state: str, duration_seconds: int):
        """Record a completed timer phase."""
        c = self._connection.cursor()
        c.execute("""
            INSERT INTO session_history (state, duration_seconds, completed_at)
            VALUES (?, ?, ?)
        """, (state, duration_seconds, datetime.now().isoformat()))
        self._connection.commit()

    def get_sessions_for_date(self, date_str: str) -> List[Dict[str, Any]]:
        """Return all session records for a given YYYY-MM-DD date."""
        c = self._connection.cursor()
        c.execute("""
            SELECT * FROM session_history
            WHERE date(completed_at) = ?
            ORDER BY completed_at ASC
        """, (date_str,))
        return [dict(row) for row in c.fetchall()]

    def get_daily_stats(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Return per-day aggregated stats between two YYYY-MM-DD dates (inclusive)."""
        c = self._connection.cursor()
        c.execute("""
            SELECT
                date(completed_at) AS day,
                SUM(CASE WHEN state = 'work' THEN 1 ELSE 0 END) AS work_sessions,
                SUM(CASE WHEN state = 'work' THEN duration_seconds ELSE 0 END) AS focus_seconds
            FROM session_history
            WHERE date(completed_at) BETWEEN ? AND ?
            GROUP BY day
            ORDER BY day ASC
        """, (start_date, end_date))
        return [dict(row) for row in c.fetchall()]

    def get_all_time_stats(self) -> Dict[str, Any]:
        """Return lifetime aggregate stats."""
        c = self._connection.cursor()
        c.execute("""
            SELECT
                COUNT(*) AS total_sessions,
                SUM(CASE WHEN state = 'work' THEN 1 ELSE 0 END) AS work_sessions,
                SUM(CASE WHEN state = 'work' THEN duration_seconds ELSE 0 END) AS total_focus_seconds,
                MIN(date(completed_at)) AS first_day,
                COUNT(DISTINCT date(completed_at)) AS active_days
            FROM session_history
        """)
        row = c.fetchone()
        return dict(row) if row else {}

    def get_streak_days(self) -> int:
        """Return the number of consecutive calendar days ending today with ≥1 work session."""
        c = self._connection.cursor()
        c.execute("""
            SELECT DISTINCT date(completed_at) AS day
            FROM session_history
            WHERE state = 'work'
            ORDER BY day DESC
        """)
        days = [row['day'] for row in c.fetchall()]
        if not days:
            return 0
        today = date.today()
        streak = 0
        for i, day_str in enumerate(days):
            try:
                day = datetime.strptime(day_str, "%Y-%m-%d").date()
            except ValueError:
                break
            if day == today - timedelta(days=i):
                streak += 1
            else:
                break
        return streak

    # ── Utility ───────────────────────────────────────────────────────────────

    def close(self):
        if self._connection:
            self._connection.close()
            self._connection = None
