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
    switch_desktop: bool = False  # Switch virtual desktop when timer finishes
    work_desktop: int = 1  # Which virtual desktop is for work (1-based)
    break_desktop: int = 2  # Which virtual desktop is for breaks (1-based)
    
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
            'downtime_notify_threshold': self.downtime_notify_threshold,
            'switch_desktop': self.switch_desktop,
            'work_desktop': self.work_desktop,
            'break_desktop': self.break_desktop
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
            downtime_notify_threshold=data.get('downtime_notify_threshold', 300),
            switch_desktop=bool(data.get('switch_desktop', False)),
            work_desktop=data.get('work_desktop', 1),
            break_desktop=data.get('break_desktop', 2)
        )


@dataclass
class ScheduleTask:
    """Daily schedule task model."""
    id: Optional[int] = None
    task: str = ""
    duration_minutes: int = 30        # how long the task takes (used for relative tasks)
    is_fixed_time: bool = False       # True = fixed clock time, False = relative to wake up
    fixed_time: str = ""              # "HH:MM" start time, used when is_fixed_time=True
    fixed_time_end: str = ""          # "HH:MM" end time, used when is_fixed_time=True
    offset_minutes: int = 0           # minutes after wake up, used when is_fixed_time=False
    anchor_type: str = "wake_up"      # wake_up | task_start | task_end
    anchor_task_id: Optional[int] = None
    sort_order: int = 0               # for ordering tasks in the list

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'task': self.task,
            'duration_minutes': self.duration_minutes,
            'is_fixed_time': self.is_fixed_time,
            'fixed_time': self.fixed_time,
            'fixed_time_end': self.fixed_time_end,
            'offset_minutes': self.offset_minutes,
            'anchor_type': self.anchor_type,
            'anchor_task_id': self.anchor_task_id,
            'sort_order': self.sort_order,
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ScheduleTask':
        return cls(
            id=data.get('id'),
            task=data.get('task', ''),
            duration_minutes=data.get('duration_minutes', 30),
            is_fixed_time=bool(data.get('is_fixed_time', False)),
            fixed_time=data.get('fixed_time', ''),
            fixed_time_end=data.get('fixed_time_end', ''),
            offset_minutes=data.get('offset_minutes', 0),
            anchor_type=data.get('anchor_type', 'wake_up'),
            anchor_task_id=data.get('anchor_task_id'),
            sort_order=data.get('sort_order', 0),
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

