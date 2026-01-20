"""
Data models for Pomodoro app.
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class Settings:
    """Settings model. Times are stored in seconds."""
    work_time: int = 1500  # 25 minutes in seconds
    short_break: int = 300  # 5 minutes in seconds
    long_break: int = 900   # 15 minutes in seconds
    downtime: int = 0
    auto_start: bool = False
    enable_downtime: bool = True
    alarm_sound_path: str = ""  # Work time alarm
    short_break_sound_path: str = ""  # Short break alarm
    long_break_sound_path: str = ""  # Long break alarm
    downtime_sound_path: str = ""  # Downtime alarm
    downtime_notify_threshold: int = 300  # Notify when downtime exceeds this (seconds)
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'work_time': self.work_time,
            'short_break': self.short_break,
            'long_break': self.long_break,
            'downtime': self.downtime,
            'auto_start': self.auto_start,
            'enable_downtime': self.enable_downtime,
            'alarm_sound_path': self.alarm_sound_path,
            'short_break_sound_path': self.short_break_sound_path,
            'long_break_sound_path': self.long_break_sound_path,
            'downtime_sound_path': self.downtime_sound_path,
            'downtime_notify_threshold': self.downtime_notify_threshold
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Settings':
        """Create from dictionary."""
        # Values are already in seconds from the database
        work_time = data.get('work_time', 1500)
        short_break = data.get('short_break', 300)
        long_break = data.get('long_break', 900)
        downtime = data.get('downtime', 0)
        
        return cls(
            work_time=work_time,
            short_break=short_break,
            long_break=long_break,
            downtime=downtime,
            auto_start=bool(data.get('auto_start', False)),
            enable_downtime=bool(data.get('enable_downtime', True)),
            alarm_sound_path=data.get('alarm_sound_path', ''),
            short_break_sound_path=data.get('short_break_sound_path', ''),
            long_break_sound_path=data.get('long_break_sound_path', ''),
            downtime_sound_path=data.get('downtime_sound_path', ''),
            downtime_notify_threshold=data.get('downtime_notify_threshold', 300)
        )


@dataclass
class Note:
    """Note model."""
    date: str
    note: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'date': self.date,
            'note': self.note
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Note':
        """Create from dictionary."""
        return cls(
            date=data['date'],
            note=data.get('note', '')
        )


@dataclass
class Todo:
    """Todo model."""
    id: Optional[int] = None
    task: str = ""
    completed: bool = False
    date: str = ""
    created_at: Optional[str] = None
    priority: int = 1  # 1=Low, 2=Medium, 3=High
    is_repeatable: bool = False
    repeat_type: str = ""  # 'daily', 'weekly', 'monthly'
    last_repeated_date: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'task': self.task,
            'completed': self.completed,
            'date': self.date,
            'created_at': self.created_at,
            'priority': self.priority,
            'is_repeatable': self.is_repeatable,
            'repeat_type': self.repeat_type,
            'last_repeated_date': self.last_repeated_date
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Todo':
        """Create from dictionary."""
        return cls(
            id=data.get('id'),
            task=data.get('task', ''),
            completed=bool(data.get('completed', False)),
            date=data.get('date', ''),
            created_at=data.get('created_at'),
            priority=data.get('priority', 1),
            is_repeatable=bool(data.get('is_repeatable', False)),
            repeat_type=data.get('repeat_type', ''),
            last_repeated_date=data.get('last_repeated_date', '')
        )

