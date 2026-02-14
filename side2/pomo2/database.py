"""
Database module for Pomodoro app.
Handles SQLite database operations for settings, notes, and todos.
"""
import sqlite3
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime


class Database:
    """Singleton database class for managing SQLite operations."""
    
    _instance = None
    _connection = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._connection is None:
            self._init_database()
    
    def _get_db_path(self) -> str:
        """Get the database file path."""
        data_dir = Path(__file__).parent / "data"
        data_dir.mkdir(exist_ok=True)
        return str(data_dir / "pomodoro.db")
    
    def _init_database(self):
        """Initialize the database with required tables."""
        db_path = self._get_db_path()
        self._connection = sqlite3.connect(db_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._create_tables()
        self._init_default_settings()
    
    def _create_tables(self):
        """Create all required tables if they don't exist."""
        cursor = self._connection.cursor()
        
        # Settings table
        cursor.execute("""
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
        
        # Notes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL UNIQUE,
                note TEXT NOT NULL DEFAULT ''
            )
        """)
        
        # Todos table
        cursor.execute("""
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
        
        # Eisenhower matrix tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS eisenhower_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                quadrant INTEGER NOT NULL DEFAULT 1,
                completed BOOLEAN NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        
        self._connection.commit()
    
    def _init_default_settings(self):
        """Initialize default settings if no settings exist."""
        cursor = self._connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM settings")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO settings (id, work_time, short_break, long_break, 
                                    downtime, auto_start, enable_downtime, alarm_sound_path,
                                    short_break_sound_path, long_break_sound_path, downtime_sound_path,
                                    downtime_notify_threshold, switch_desktop, work_desktop, break_desktop)
                VALUES (1, 1500, 300, 900, 0, 0, 1, '', '', '', '', 300, 0, 1, 2)
            """)
            self._connection.commit()
        else:
            # Add alarm sound path columns if they don't exist
            try:
                cursor.execute("ALTER TABLE settings ADD COLUMN alarm_sound_path TEXT DEFAULT ''")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE settings ADD COLUMN short_break_sound_path TEXT DEFAULT ''")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE settings ADD COLUMN long_break_sound_path TEXT DEFAULT ''")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE settings ADD COLUMN downtime_sound_path TEXT DEFAULT ''")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE settings ADD COLUMN downtime_notify_threshold INTEGER NOT NULL DEFAULT 300")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE settings ADD COLUMN switch_desktop BOOLEAN NOT NULL DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE settings ADD COLUMN work_desktop INTEGER NOT NULL DEFAULT 1")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE settings ADD COLUMN break_desktop INTEGER NOT NULL DEFAULT 2")
            except sqlite3.OperationalError:
                pass
            self._connection.commit()
            
            # Check if we need to migrate from minutes to seconds (only for old default values)
            # Only migrate if we detect the old default values (25, 5, 15) which were definitely in minutes
            cursor.execute("SELECT work_time, short_break, long_break FROM settings WHERE id = 1")
            row = cursor.fetchone()
            if row:
                work_time = row['work_time']
                short_break = row['short_break']
                long_break = row['long_break']
                
                # Only migrate if we detect the exact old default values (25 min, 5 min, 15 min)
                # This ensures we don't accidentally convert legitimate second values
                if work_time == 25 and short_break == 5 and long_break == 15:
                    # This is definitely old minute-based data, migrate it
                    cursor.execute("""
                        UPDATE settings SET
                            work_time = work_time * 60,
                            short_break = short_break * 60,
                            long_break = long_break * 60,
                            downtime = CASE WHEN downtime > 0 THEN downtime * 60 ELSE downtime END
                        WHERE id = 1
                    """)
                    self._connection.commit()
    
    def get_connection(self):
        """Get the database connection."""
        return self._connection
    
    # Settings operations
    def get_settings(self) -> Dict[str, Any]:
        """Get current settings."""
        cursor = self._connection.cursor()
        cursor.execute("SELECT * FROM settings WHERE id = 1")
        row = cursor.fetchone()
        if row:
            result = {
                'id': row['id'],
                'work_time': row['work_time'],
                'short_break': row['short_break'],
                'long_break': row['long_break'],
                'downtime': row['downtime'],
                'auto_start': bool(row['auto_start']),
                'enable_downtime': bool(row['enable_downtime'])
            }
            # Add alarm sound paths if columns exist
            try:
                result['alarm_sound_path'] = row['alarm_sound_path'] if row['alarm_sound_path'] else ''
            except (IndexError, KeyError):
                result['alarm_sound_path'] = ''
            try:
                result['short_break_sound_path'] = row['short_break_sound_path'] if row['short_break_sound_path'] else ''
            except (IndexError, KeyError):
                result['short_break_sound_path'] = ''
            try:
                result['long_break_sound_path'] = row['long_break_sound_path'] if row['long_break_sound_path'] else ''
            except (IndexError, KeyError):
                result['long_break_sound_path'] = ''
            try:
                result['downtime_sound_path'] = row['downtime_sound_path'] if row['downtime_sound_path'] else ''
            except (IndexError, KeyError):
                result['downtime_sound_path'] = ''
            try:
                result['downtime_notify_threshold'] = row['downtime_notify_threshold'] if row['downtime_notify_threshold'] else 300
            except (IndexError, KeyError):
                result['downtime_notify_threshold'] = 300
            try:
                result['switch_desktop'] = bool(row['switch_desktop'])
            except (IndexError, KeyError):
                result['switch_desktop'] = False
            try:
                result['work_desktop'] = row['work_desktop'] if row['work_desktop'] else 1
            except (IndexError, KeyError):
                result['work_desktop'] = 1
            try:
                result['break_desktop'] = row['break_desktop'] if row['break_desktop'] else 2
            except (IndexError, KeyError):
                result['break_desktop'] = 2
            return result
        return None
    
    def update_settings(self, settings: Dict[str, Any]):
        """Update settings."""
        cursor = self._connection.cursor()
        # Check which columns exist
        cursor.execute("PRAGMA table_info(settings)")
        columns = [col[1] for col in cursor.fetchall()]
        has_alarm = 'alarm_sound_path' in columns
        has_short_break_sound = 'short_break_sound_path' in columns
        has_long_break_sound = 'long_break_sound_path' in columns
        has_downtime_sound = 'downtime_sound_path' in columns
        has_notify_threshold = 'downtime_notify_threshold' in columns
        has_switch_desktop = 'switch_desktop' in columns
        
        has_work_desktop = 'work_desktop' in columns
        has_break_desktop = 'break_desktop' in columns
        
        if has_alarm and has_short_break_sound and has_long_break_sound and has_downtime_sound and has_notify_threshold:
            if has_switch_desktop and has_work_desktop and has_break_desktop:
                cursor.execute("""
                    UPDATE settings SET
                        work_time = ?,
                        short_break = ?,
                        long_break = ?,
                        downtime = ?,
                        auto_start = ?,
                        enable_downtime = ?,
                        alarm_sound_path = ?,
                        short_break_sound_path = ?,
                        long_break_sound_path = ?,
                        downtime_sound_path = ?,
                        downtime_notify_threshold = ?,
                        switch_desktop = ?,
                        work_desktop = ?,
                        break_desktop = ?
                    WHERE id = 1
                """, (
                    settings['work_time'],
                    settings['short_break'],
                    settings['long_break'],
                    settings['downtime'],
                    1 if settings['auto_start'] else 0,
                    1 if settings['enable_downtime'] else 0,
                    settings.get('alarm_sound_path', ''),
                    settings.get('short_break_sound_path', ''),
                    settings.get('long_break_sound_path', ''),
                    settings.get('downtime_sound_path', ''),
                    settings.get('downtime_notify_threshold', 300),
                    1 if settings.get('switch_desktop', False) else 0,
                    settings.get('work_desktop', 1),
                    settings.get('break_desktop', 2)
                ))
            elif has_switch_desktop:
                cursor.execute("""
                    UPDATE settings SET
                        work_time = ?,
                        short_break = ?,
                        long_break = ?,
                        downtime = ?,
                        auto_start = ?,
                        enable_downtime = ?,
                        alarm_sound_path = ?,
                        short_break_sound_path = ?,
                        long_break_sound_path = ?,
                        downtime_sound_path = ?,
                        downtime_notify_threshold = ?,
                        switch_desktop = ?
                    WHERE id = 1
                """, (
                    settings['work_time'],
                    settings['short_break'],
                    settings['long_break'],
                    settings['downtime'],
                    1 if settings['auto_start'] else 0,
                    1 if settings['enable_downtime'] else 0,
                    settings.get('alarm_sound_path', ''),
                    settings.get('short_break_sound_path', ''),
                    settings.get('long_break_sound_path', ''),
                    settings.get('downtime_sound_path', ''),
                    settings.get('downtime_notify_threshold', 300),
                    1 if settings.get('switch_desktop', False) else 0
                ))
            else:
                cursor.execute("""
                    UPDATE settings SET
                        work_time = ?,
                        short_break = ?,
                        long_break = ?,
                        downtime = ?,
                        auto_start = ?,
                        enable_downtime = ?,
                        alarm_sound_path = ?,
                        short_break_sound_path = ?,
                        long_break_sound_path = ?,
                        downtime_sound_path = ?,
                        downtime_notify_threshold = ?
                    WHERE id = 1
                """, (
                    settings['work_time'],
                    settings['short_break'],
                    settings['long_break'],
                    settings['downtime'],
                    1 if settings['auto_start'] else 0,
                    1 if settings['enable_downtime'] else 0,
                    settings.get('alarm_sound_path', ''),
                    settings.get('short_break_sound_path', ''),
                    settings.get('long_break_sound_path', ''),
                    settings.get('downtime_sound_path', ''),
                    settings.get('downtime_notify_threshold', 300)
                ))
        elif has_alarm:
            cursor.execute("""
                UPDATE settings SET
                    work_time = ?,
                    short_break = ?,
                    long_break = ?,
                    downtime = ?,
                    auto_start = ?,
                    enable_downtime = ?,
                    alarm_sound_path = ?
                WHERE id = 1
            """, (
                settings['work_time'],
                settings['short_break'],
                settings['long_break'],
                settings['downtime'],
                1 if settings['auto_start'] else 0,
                1 if settings['enable_downtime'] else 0,
                settings.get('alarm_sound_path', '')
            ))
        else:
            cursor.execute("""
                UPDATE settings SET
                    work_time = ?,
                    short_break = ?,
                    long_break = ?,
                    downtime = ?,
                    auto_start = ?,
                    enable_downtime = ?
                WHERE id = 1
            """, (
                settings['work_time'],
                settings['short_break'],
                settings['long_break'],
                settings['downtime'],
                1 if settings['auto_start'] else 0,
                1 if settings['enable_downtime'] else 0
            ))
        self._connection.commit()
    
    # Notes operations
    def get_note(self, date: str) -> Optional[str]:
        """Get note for a specific date."""
        cursor = self._connection.cursor()
        cursor.execute("SELECT note FROM notes WHERE date = ?", (date,))
        row = cursor.fetchone()
        return row['note'] if row else None
    
    def save_note(self, date: str, note: str):
        """Save or update note for a date."""
        cursor = self._connection.cursor()
        cursor.execute("""
            INSERT INTO notes (date, note)
            VALUES (?, ?)
            ON CONFLICT(date) DO UPDATE SET note = ?
        """, (date, note, note))
        self._connection.commit()
    
    def get_all_notes(self) -> List[Dict[str, Any]]:
        """Get all notes."""
        cursor = self._connection.cursor()
        cursor.execute("SELECT * FROM notes ORDER BY date DESC")
        return [dict(row) for row in cursor.fetchall()]
    
    # Todo operations
    def add_todo(self, task: str, date: str, priority: int = 1, 
                 is_repeatable: bool = False, repeat_type: str = '') -> int:
        """Add a new todo item."""
        cursor = self._connection.cursor()
        created_at = datetime.now().isoformat()
        
        # Check if priority and repeatable columns exist, add them if not
        cursor.execute("PRAGMA table_info(todos)")
        columns = [col[1] for col in cursor.fetchall()]
        has_priority = 'priority' in columns
        has_repeatable = 'is_repeatable' in columns
        
        # Add missing columns
        if not has_priority:
            try:
                cursor.execute("ALTER TABLE todos ADD COLUMN priority INTEGER NOT NULL DEFAULT 1")
            except sqlite3.OperationalError:
                pass
        if not has_repeatable:
            try:
                cursor.execute("ALTER TABLE todos ADD COLUMN is_repeatable BOOLEAN NOT NULL DEFAULT 0")
                cursor.execute("ALTER TABLE todos ADD COLUMN repeat_type TEXT DEFAULT ''")
                cursor.execute("ALTER TABLE todos ADD COLUMN last_repeated_date TEXT DEFAULT ''")
            except sqlite3.OperationalError:
                pass
        
        cursor.execute("""
            INSERT INTO todos (task, completed, date, created_at, priority, is_repeatable, repeat_type)
            VALUES (?, 0, ?, ?, ?, ?, ?)
        """, (task, date, created_at, priority, 1 if is_repeatable else 0, repeat_type))
        
        self._connection.commit()
        return cursor.lastrowid
    
    def get_todos(self, date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get todos, optionally filtered by date."""
        cursor = self._connection.cursor()
        
        # Check if priority column exists, add if not
        cursor.execute("PRAGMA table_info(todos)")
        columns = [col[1] for col in cursor.fetchall()]
        has_priority = 'priority' in columns
        
        if not has_priority:
            try:
                cursor.execute("ALTER TABLE todos ADD COLUMN priority INTEGER NOT NULL DEFAULT 1")
                cursor.execute("ALTER TABLE todos ADD COLUMN is_repeatable BOOLEAN NOT NULL DEFAULT 0")
                cursor.execute("ALTER TABLE todos ADD COLUMN repeat_type TEXT DEFAULT ''")
                cursor.execute("ALTER TABLE todos ADD COLUMN last_repeated_date TEXT DEFAULT ''")
                self._connection.commit()
            except sqlite3.OperationalError:
                pass
        
        # Build query based on available columns
        if has_priority or 'priority' in [col[1] for col in cursor.execute("PRAGMA table_info(todos)").fetchall()]:
            order_by = "ORDER BY priority DESC, date DESC, created_at DESC"
        else:
            order_by = "ORDER BY date DESC, created_at DESC"
        
        if date:
            cursor.execute(f"""
                SELECT * FROM todos WHERE date = ?
                {order_by}
            """, (date,))
        else:
            cursor.execute(f"""
                SELECT * FROM todos
                {order_by}
            """)
        
        todos = []
        for row in cursor.fetchall():
            todo_dict = dict(row)
            # Ensure priority and repeatable fields exist
            if 'priority' not in todo_dict:
                todo_dict['priority'] = 1
            if 'is_repeatable' not in todo_dict:
                todo_dict['is_repeatable'] = False
            if 'repeat_type' not in todo_dict:
                todo_dict['repeat_type'] = ''
            if 'last_repeated_date' not in todo_dict:
                todo_dict['last_repeated_date'] = ''
            todos.append(todo_dict)
        return todos
    
    def update_todo(self, todo_id: int, task: Optional[str] = None, 
                   completed: Optional[bool] = None, priority: Optional[int] = None,
                   is_repeatable: Optional[bool] = None, repeat_type: Optional[str] = None):
        """Update a todo item."""
        cursor = self._connection.cursor()
        
        # Check which columns exist
        cursor.execute("PRAGMA table_info(todos)")
        columns = [col[1] for col in cursor.fetchall()]
        has_priority = 'priority' in columns
        has_repeatable = 'is_repeatable' in columns
        
        updates = []
        values = []
        
        if task is not None:
            updates.append("task = ?")
            values.append(task)
        if completed is not None:
            updates.append("completed = ?")
            values.append(1 if completed else 0)
        if priority is not None and has_priority:
            updates.append("priority = ?")
            values.append(priority)
        if is_repeatable is not None and has_repeatable:
            updates.append("is_repeatable = ?")
            values.append(1 if is_repeatable else 0)
        if repeat_type is not None and has_repeatable:
            updates.append("repeat_type = ?")
            values.append(repeat_type)
        
        if updates:
            values.append(todo_id)
            query = f"UPDATE todos SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, values)
            self._connection.commit()
    
    def handle_repeatable_todos(self):
        """Handle repeating todos - create new instances for repeatable tasks."""
        from datetime import timedelta
        cursor = self._connection.cursor()
        today = datetime.now().date().strftime("%Y-%m-%d")
        
        # Check if repeatable columns exist
        cursor.execute("PRAGMA table_info(todos)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'is_repeatable' not in columns:
            return
        
        # Get all repeatable todos that are completed
        cursor.execute("""
            SELECT * FROM todos 
            WHERE is_repeatable = 1 AND completed = 1
        """)
        
        for row in cursor.fetchall():
            todo = dict(row)
            last_repeated = todo.get('last_repeated_date', '') or todo.get('date', '')
            repeat_type = todo.get('repeat_type', 'daily')
            
            if not last_repeated:
                last_repeated = todo.get('date', '')
            
            try:
                last_date = datetime.strptime(last_repeated, "%Y-%m-%d").date()
                today_date = datetime.strptime(today, "%Y-%m-%d").date()
                
                should_repeat = False
                if repeat_type == 'daily':
                    should_repeat = (today_date - last_date).days >= 1
                elif repeat_type == 'weekly':
                    should_repeat = (today_date - last_date).days >= 7
                elif repeat_type == 'monthly':
                    should_repeat = (today_date - last_date).days >= 30
                
                if should_repeat:
                    # Create new todo instance
                    new_date = today
                    cursor.execute("""
                        INSERT INTO todos (task, completed, date, created_at, priority, is_repeatable, repeat_type)
                        VALUES (?, 0, ?, ?, ?, 1, ?)
                    """, (todo['task'], new_date, datetime.now().isoformat(), 
                          todo.get('priority', 1), repeat_type))
                    
                    # Update last_repeated_date
                    cursor.execute("""
                        UPDATE todos SET last_repeated_date = ? WHERE id = ?
                    """, (today, todo['id']))
            except (ValueError, KeyError) as e:
                # Skip invalid dates or missing data
                continue
                    
        self._connection.commit()
    
    def delete_todo(self, todo_id: int):
        """Delete a todo item."""
        cursor = self._connection.cursor()
        cursor.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
        self._connection.commit()
    
    # Eisenhower matrix operations
    def add_eisenhower_task(self, task: str, quadrant: int) -> int:
        """Add a new Eisenhower matrix task. Quadrant: 1-4."""
        cursor = self._connection.cursor()
        created_at = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO eisenhower_tasks (task, quadrant, completed, created_at)
            VALUES (?, ?, 0, ?)
        """, (task, quadrant, created_at))
        self._connection.commit()
        return cursor.lastrowid
    
    def get_eisenhower_tasks(self, quadrant: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get Eisenhower tasks, optionally filtered by quadrant."""
        cursor = self._connection.cursor()
        if quadrant is not None:
            cursor.execute("""
                SELECT * FROM eisenhower_tasks WHERE quadrant = ?
                ORDER BY completed ASC, created_at DESC
            """, (quadrant,))
        else:
            cursor.execute("""
                SELECT * FROM eisenhower_tasks
                ORDER BY quadrant ASC, completed ASC, created_at DESC
            """)
        return [dict(row) for row in cursor.fetchall()]
    
    def update_eisenhower_task(self, task_id: int, task: Optional[str] = None,
                               quadrant: Optional[int] = None,
                               completed: Optional[bool] = None):
        """Update an Eisenhower task."""
        cursor = self._connection.cursor()
        updates = []
        values = []
        if task is not None:
            updates.append("task = ?")
            values.append(task)
        if quadrant is not None:
            updates.append("quadrant = ?")
            values.append(quadrant)
        if completed is not None:
            updates.append("completed = ?")
            values.append(1 if completed else 0)
        if updates:
            values.append(task_id)
            query = f"UPDATE eisenhower_tasks SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, values)
            self._connection.commit()
    
    def delete_eisenhower_task(self, task_id: int):
        """Delete an Eisenhower task."""
        cursor = self._connection.cursor()
        cursor.execute("DELETE FROM eisenhower_tasks WHERE id = ?", (task_id,))
        self._connection.commit()
    
    def close(self):
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

