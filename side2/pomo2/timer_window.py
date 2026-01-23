"""
Main timer window for Pomodoro app.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QSystemTrayIcon, QMenu, QApplication,
                             QDialog, QMessageBox)
from PyQt6.QtCore import QTimer, Qt, pyqtSignal, QUrl, QSize
from PyQt6.QtGui import QIcon, QFont, QAction, QPixmap, QPainter, QColor
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from enum import Enum
import os
from database import Database
from models import Settings


class TimerState(Enum):
    """Timer state enumeration."""
    WORK = "work"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"
    DOWNTIME = "downtime"
    PAUSED = "paused"


class AlarmDialog(QDialog):
    """Dialog that appears when timer completes to stop the alarm."""
    
    def __init__(self, parent=None, timer_name: str = "Timer", media_player=None):
        super().__init__(parent)
        self.media_player = media_player
        self.setWindowTitle("Timer Complete!")
        self.setModal(True)
        self.setMinimumSize(400, 200)
        
        # Make dialog appear on top and bring window to front
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowCloseButtonHint
        )
        
        # Apply styling
        self.setStyleSheet("""
            QDialog {
                background-color: #ffffff;
                border: 3px solid #4CAF50;
                border-radius: 10px;
            }
            QLabel {
                color: #333;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Title
        title_label = QLabel(f"{timer_name} Complete!")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #4CAF50;")
        layout.addWidget(title_label)
        
        # Message
        message_label = QLabel("Your timer has finished!")
        message_font = QFont()
        message_font.setPointSize(14)
        message_label.setFont(message_font)
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message_label)
        
        # Stop button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        stop_button = QPushButton("🔇 Stop Alarm")
        stop_button.clicked.connect(self._stop_alarm)
        stop_button.setMinimumWidth(150)
        stop_button.setMinimumHeight(45)
        button_layout.addWidget(stop_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Bring window to front
        self.raise_()
        self.activateWindow()
    
    def _stop_alarm(self):
        """Stop the alarm sound and close dialog."""
        if self.media_player:
            self.media_player.stop()
        self.accept()


class TimerWindow(QWidget):
    """Main timer window."""
    
    # Signal emitted when timer completes
    timer_completed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = Database()
        self.settings = self._load_settings()
        self.state = TimerState.WORK
        self.previous_state = TimerState.WORK  # Store state before pause
        self.remaining_seconds = 0
        self.work_sessions = 0
        self.downtime_seconds = 0  # Track downtime duration
        self.last_notification_time = 0  # Track last notification time
        self.is_downtime_active = False  # Track if downtime is currently being tracked
        self.muted = False  # Track mute state
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_timer)
        self.tray_icon = None
        self.alarm_dialog = None
        
        # Setup audio player for alarm sound
        self.audio_output = QAudioOutput(self)
        self.media_player = QMediaPlayer(self)
        self.media_player.setAudioOutput(self.audio_output)
        
        self._init_ui()
        self._setup_tray()
        self._load_state()
    
    def _load_settings(self) -> Settings:
        """Load settings from database."""
        settings_data = self.db.get_settings()
        if settings_data:
            return Settings.from_dict(settings_data)
        return Settings()
    
    def _init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle("Pomodoro Timer")
        self.setMinimumSize(500, 600)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setSpacing(25)
        main_layout.setContentsMargins(40, 40, 40, 40)
        
        # State label
        self.state_label = QLabel("⏱ Work Time")
        self.state_label.setObjectName("state_label")
        self.state_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(20)
        font.setBold(True)
        self.state_label.setFont(font)
        main_layout.addWidget(self.state_label)
        
        # Timer display
        self.timer_label = QLabel("00:00")
        self.timer_label.setObjectName("timer_label")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        timer_font = QFont()
        timer_font.setPointSize(72)
        timer_font.setBold(True)
        self.timer_label.setFont(timer_font)
        main_layout.addWidget(self.timer_label)
        
        # Work sessions counter
        self.sessions_label = QLabel("Work Sessions: 0")
        self.sessions_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sessions_font = QFont()
        sessions_font.setPointSize(14)
        self.sessions_label.setFont(sessions_font)
        self.sessions_label.setStyleSheet("color: #666;")
        main_layout.addWidget(self.sessions_label)
        
        # Downtime timer display (separate, smaller)
        downtime_container = QWidget()
        downtime_layout = QVBoxLayout()
        downtime_layout.setSpacing(5)
        downtime_layout.setContentsMargins(0, 15, 0, 0)
        
        downtime_title = QLabel("💤 Downtime")
        downtime_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        downtime_title_font = QFont()
        downtime_title_font.setPointSize(11)
        downtime_title.setFont(downtime_title_font)
        downtime_title.setStyleSheet("color: #999;")
        downtime_layout.addWidget(downtime_title)
        
        self.downtime_label = QLabel("00:00")
        self.downtime_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        downtime_font = QFont()
        downtime_font.setPointSize(24)
        downtime_font.setBold(True)
        self.downtime_label.setFont(downtime_font)
        self.downtime_label.setStyleSheet("color: #9e9e9e;")
        downtime_layout.addWidget(self.downtime_label)
        
        downtime_container.setLayout(downtime_layout)
        self.downtime_container = downtime_container  # Store reference
        main_layout.addWidget(downtime_container)
        
        # Set initial visibility
        if self.settings.enable_downtime:
            downtime_container.setVisible(True)
        else:
            downtime_container.setVisible(False)
        
        # Control buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.start_button = QPushButton("▶ Start")
        self.start_button.clicked.connect(self.start_timer)
        self.start_button.setMinimumHeight(45)
        self.start_button.setMinimumWidth(120)
        button_layout.addWidget(self.start_button)
        
        self.pause_button = QPushButton("⏸ Pause")
        self.pause_button.setObjectName("pauseBtn")
        self.pause_button.clicked.connect(self.pause_timer)
        self.pause_button.setMinimumHeight(45)
        self.pause_button.setMinimumWidth(120)
        self.pause_button.setEnabled(False)
        button_layout.addWidget(self.pause_button)
        
        self.reset_button = QPushButton("⏹ Reset")
        self.reset_button.setObjectName("resetBtn")
        self.reset_button.clicked.connect(self.reset_timer)
        self.reset_button.setMinimumHeight(45)
        self.reset_button.setMinimumWidth(120)
        button_layout.addWidget(self.reset_button)
        
        self.skip_button = QPushButton("⏭ Skip")
        self.skip_button.setObjectName("skipBtn")
        self.skip_button.clicked.connect(self.skip_timer)
        self.skip_button.setMinimumHeight(45)
        self.skip_button.setMinimumWidth(120)
        button_layout.addWidget(self.skip_button)
        
        main_layout.addLayout(button_layout)
        
        # Mute button
        mute_layout = QHBoxLayout()
        mute_layout.addStretch()
        self.mute_button = QPushButton("🔊 Mute")
        self.mute_button.setObjectName("muteBtn")
        self.mute_button.clicked.connect(self.toggle_mute)
        self.mute_button.setMinimumHeight(35)
        self.mute_button.setMinimumWidth(100)
        mute_layout.addWidget(self.mute_button)
        mute_layout.addStretch()
        main_layout.addLayout(mute_layout)
        
        # Spacer
        main_layout.addStretch()
        
        self.setLayout(main_layout)
        self._update_display()
        self._apply_state_colors()
        self._update_icon()  # Set initial icon
    
    def _create_emoji_icon(self, emoji: str) -> QIcon:
        """Create an icon from an emoji."""
        # Create a pixmap
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background
        
        # Draw emoji on pixmap
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        font = QFont()
        font.setPointSize(20)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, emoji)
        painter.end()
        
        return QIcon(pixmap)
    
    def _update_icon(self):
        """Update the app icon based on current timer state."""
        # Map states to emojis
        state_emojis = {
            TimerState.WORK: "⏱️",
            TimerState.SHORT_BREAK: "☕",
            TimerState.LONG_BREAK: "🌴",
            TimerState.PAUSED: "⏸️"
        }
        
        emoji = state_emojis.get(self.state, "⏱️")
        icon = self._create_emoji_icon(emoji)
        
        # Update window icon
        self.setWindowIcon(icon)
        
        # Update tray icon if available
        if self.tray_icon:
            self.tray_icon.setIcon(icon)
    
    def _setup_tray(self):
        """Setup system tray icon."""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            
            # Create tray menu
            tray_menu = QMenu()
            
            show_action = QAction("Show", self)
            show_action.triggered.connect(self.show)
            tray_menu.addAction(show_action)
            
            quit_action = QAction("Quit", self)
            quit_action.triggered.connect(QApplication.instance().quit)
            tray_menu.addAction(quit_action)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(self._tray_icon_activated)
            self.tray_icon.show()
            
            # Set initial icon
            self._update_icon()
    
    def _tray_icon_activated(self, reason):
        """Handle tray icon activation."""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.raise_()
            self.activateWindow()
    
    def _update_display(self):
        """Update the timer display."""
        # Update main timer
        minutes = self.remaining_seconds // 60
        seconds = self.remaining_seconds % 60
        self.timer_label.setText(f"{minutes:02d}:{seconds:02d}")
        
        # Update work sessions
        self.sessions_label.setText(f"Work Sessions: {self.work_sessions}")
        
        # Update downtime timer (always visible if downtime is enabled)
        if hasattr(self, 'downtime_label'):
            if self.settings.enable_downtime:
                downtime_minutes = self.downtime_seconds // 60
                downtime_seconds = self.downtime_seconds % 60
                self.downtime_label.setText(f"{downtime_minutes:02d}:{downtime_seconds:02d}")
                
                # Highlight if downtime exceeds threshold
                if self.downtime_seconds >= self.settings.downtime_notify_threshold:
                    self.downtime_label.setStyleSheet("color: #ff9800; font-weight: bold;")
                else:
                    self.downtime_label.setStyleSheet("color: #9e9e9e;")
            else:
                self.downtime_label.setText("--:--")
                self.downtime_label.setStyleSheet("color: #ccc;")
    
    def _apply_state_colors(self):
        """Apply color coding based on timer state."""
        base_style = """
            QWidget {
                background-color: #ffffff;
            }
            QLabel#state_label {
                padding: 15px;
                border-radius: 10px;
                font-weight: bold;
            }
            QLabel#timer_label {
                padding: 20px;
                border-radius: 15px;
                background-color: #f8f9fa;
                border: 3px solid #e0e0e0;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
            QPushButton#pauseBtn {
                background-color: #ff9800;
            }
            QPushButton#pauseBtn:hover {
                background-color: #e68900;
            }
            QPushButton#resetBtn {
                background-color: #f44336;
            }
            QPushButton#resetBtn:hover {
                background-color: #da190b;
            }
            QPushButton#skipBtn {
                background-color: #2196F3;
            }
            QPushButton#skipBtn:hover {
                background-color: #0b7dda;
            }
            QPushButton#muteBtn {
                background-color: #757575;
            }
            QPushButton#muteBtn:hover {
                background-color: #616161;
            }
            QPushButton#muteBtn:pressed {
                background-color: #424242;
            }
        """
        
        if self.state == TimerState.WORK:
            state_style = base_style + """
                QLabel#state_label {
                    background-color: #ffebee;
                    color: #c62828;
                    border: 2px solid #ef5350;
                }
                QLabel#timer_label {
                    color: #c62828;
                    border-color: #ef5350;
                }
            """
            self.setStyleSheet(state_style)
            self.state_label.setText("⏱ Work Time")
            # Show downtime timer (it tracks in background)
            if hasattr(self, 'downtime_container'):
                self.downtime_container.setVisible(self.settings.enable_downtime)
        elif self.state == TimerState.SHORT_BREAK:
            state_style = base_style + """
                QLabel#state_label {
                    background-color: #e3f2fd;
                    color: #1565c0;
                    border: 2px solid #42a5f5;
                }
                QLabel#timer_label {
                    color: #1565c0;
                    border-color: #42a5f5;
                }
            """
            self.setStyleSheet(state_style)
            self.state_label.setText("☕ Short Break")
            # Show downtime timer (it tracks in background)
            if hasattr(self, 'downtime_container'):
                self.downtime_container.setVisible(self.settings.enable_downtime)
        elif self.state == TimerState.LONG_BREAK:
            state_style = base_style + """
                QLabel#state_label {
                    background-color: #e8f5e9;
                    color: #2e7d32;
                    border: 2px solid #66bb6a;
                }
                QLabel#timer_label {
                    color: #2e7d32;
                    border-color: #66bb6a;
                }
            """
            self.setStyleSheet(state_style)
            self.state_label.setText("🌴 Long Break")
            # Show downtime timer (it tracks in background)
            if hasattr(self, 'downtime_container'):
                self.downtime_container.setVisible(self.settings.enable_downtime)
        else:
            state_style = base_style + """
                QLabel#state_label {
                    background-color: #f5f5f5;
                    color: #616161;
                    border: 2px solid #9e9e9e;
                }
                QLabel#timer_label {
                    color: #616161;
                    border-color: #9e9e9e;
                }
            """
            self.setStyleSheet(state_style)
            self.state_label.setText("⏸ Paused")
            # Show downtime timer if enabled
            if hasattr(self, 'downtime_container'):
                self.downtime_container.setVisible(self.settings.enable_downtime)
        
        # Update icon when state changes
        self._update_icon()
    
    def _get_timer_duration(self) -> int:
        """Get timer duration in seconds for current state."""
        if self.state == TimerState.WORK:
            return self.settings.work_time
        elif self.state == TimerState.SHORT_BREAK:
            return self.settings.short_break
        elif self.state == TimerState.LONG_BREAK:
            return self.settings.long_break
        return 0
    
    def _get_next_state(self):
        """Get the next timer state without changing current state."""
        if self.state == TimerState.WORK:
            # Calculate what the next break will be after incrementing work_sessions
            next_session_count = self.work_sessions + 1
            if next_session_count % 4 == 0:
                return 'long_break'
            else:
                return 'short_break'
        elif self.state in [TimerState.SHORT_BREAK, TimerState.LONG_BREAK]:
            return 'work'
        return 'work'
    
    def _next_state(self):
        """Move to the next timer state."""
        if self.state == TimerState.WORK:
            self.work_sessions += 1
            if self.work_sessions % 4 == 0:
                self.state = TimerState.LONG_BREAK
            else:
                self.state = TimerState.SHORT_BREAK
        elif self.state in [TimerState.SHORT_BREAK, TimerState.LONG_BREAK]:
            self.state = TimerState.WORK
        
        self.remaining_seconds = self._get_timer_duration()
        self._update_display()
        self._apply_state_colors()
    
    def _has_sound_for_state(self, state_name: str) -> bool:
        """Check if there's a sound configured for the given state."""
        if state_name == 'work':
            return bool(self.settings.alarm_sound_path and os.path.exists(self.settings.alarm_sound_path))
        elif state_name == 'short_break':
            return bool(self.settings.short_break_sound_path and os.path.exists(self.settings.short_break_sound_path))
        elif state_name == 'long_break':
            return bool(self.settings.long_break_sound_path and os.path.exists(self.settings.long_break_sound_path))
        return False
    
    def start_timer(self):
        """Start the timer."""
        # Stop downtime tracking when starting timer
        if self.is_downtime_active:
            self._stop_downtime()
        
        # Resume from pause
        if self.state == TimerState.PAUSED:
            self.state = self.previous_state
        
        # Reset if timer is at zero
        if self.remaining_seconds == 0:
            self.remaining_seconds = self._get_timer_duration()
        
        self.timer.start(1000)
        self.start_button.setEnabled(False)
        self.pause_button.setEnabled(True)
        self._apply_state_colors()
    
    def pause_timer(self):
        """Pause the timer."""
        self.timer.stop()
        self.previous_state = self.state
        self.state = TimerState.PAUSED
        
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self._apply_state_colors()
    
    def reset_timer(self):
        """Reset the timer."""
        self.timer.stop()
        self._stop_downtime()
        
        self.state = TimerState.WORK
        self.remaining_seconds = self._get_timer_duration()
        
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        self._update_display()
        self._apply_state_colors()
    
    def skip_timer(self):
        """Skip to the next timer state."""
        self.timer.stop()
        self._stop_downtime()
        self._next_state()
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        
        # Auto-start if enabled
        if self.settings.auto_start:
            self.start_timer()
    
    def toggle_mute(self):
        """Toggle mute state for all alarms."""
        self.muted = not self.muted
        if self.muted:
            self.mute_button.setText("🔇 Unmute")
            # Stop any currently playing alarm
            if self.media_player and self.media_player.isPlaying():
                self.media_player.stop()
        else:
            self.mute_button.setText("🔊 Mute")
    
    def _update_timer(self):
        """Update timer countdown."""
        # Track downtime in background if active
        if self.is_downtime_active:
            self.downtime_seconds += 1
            self._check_downtime_notification()
            self._update_display()
        
        # Handle regular timer countdown
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self._update_display()
            return
        
        # Timer completed - handle completion
        if not self.is_downtime_active:
            self._handle_timer_completion()
    
    def _check_downtime_notification(self):
        """Check if downtime exceeds threshold and notify if needed."""
        if not (self.settings.enable_downtime and self.settings.downtime_notify_threshold > 0):
            return
        
        intervals_passed = self.downtime_seconds // self.settings.downtime_notify_threshold
        threshold_time = intervals_passed * self.settings.downtime_notify_threshold
        
        if intervals_passed > 0 and threshold_time > self.last_notification_time:
            self.last_notification_time = threshold_time
            self._notify_downtime_exceeded()
    
    def _notify_downtime_exceeded(self):
        """Show notification when downtime exceeds threshold."""
        has_sound = (self.settings.downtime_sound_path and 
                    os.path.exists(self.settings.downtime_sound_path))
        self._show_alarm_dialog('downtime', play_sound=has_sound and not self.muted)
    
    def _handle_timer_completion(self):
        """Handle timer completion - show alarm and transition to next state."""
        self.timer_completed.emit(self.state.value)
        
        # Show alarm for next state
        next_state = self._get_next_state()
        has_sound = self._has_sound_for_state(next_state)
        self._show_alarm_dialog(next_state, play_sound=has_sound and not self.muted)
        
        # Move to next state
        self._next_state()
        self.start_button.setEnabled(True)
        self.pause_button.setEnabled(False)
        
        # Auto-start or start downtime tracking
        if self.settings.auto_start:
            self.start_timer()
        elif self.settings.enable_downtime:
            self._start_downtime()
        else:
            self.timer.stop()
    
    def _get_sound_path(self, state_name: str) -> str:
        """Get sound path for given state."""
        sound_map = {
            'work': self.settings.alarm_sound_path,
            'short_break': self.settings.short_break_sound_path,
            'long_break': self.settings.long_break_sound_path,
            'downtime': self.settings.downtime_sound_path
        }
        sound_path = sound_map.get(state_name)
        
        # Fallback to work sound if specific sound not set
        if not sound_path:
            sound_path = self.settings.alarm_sound_path
        
        return sound_path if (sound_path and os.path.exists(sound_path)) else None
    
    def _show_alarm_dialog(self, state_name: str, play_sound: bool = True):
        """Show alarm dialog and play sound."""
        state_display = {
            'work': '⏱ Work Time',
            'short_break': '☕ Short Break',
            'long_break': '🌴 Long Break',
            'downtime': '💤 Downtime'
        }
        display_name = state_display.get(state_name, 'Timer')
        
        # Play sound if requested
        if play_sound:
            sound_path = self._get_sound_path(state_name)
            if sound_path:
                try:
                    self.media_player.setSource(QUrl.fromLocalFile(sound_path))
                    self.media_player.play()
                except Exception as e:
                    print(f"Error playing alarm sound: {e}")
        
        # Bring window to front
        if self.isMinimized():
            self.showNormal()
        self.raise_()
        self.activateWindow()
        
        # Show dialog
        self.alarm_dialog = AlarmDialog(self, display_name, self.media_player)
        self.alarm_dialog.exec()
        
        # Stop alarm after dialog closes
        if self.media_player:
            self.media_player.stop()
    
    def _start_downtime(self):
        """Start downtime tracking in background."""
        self.is_downtime_active = True
        self.downtime_seconds = 0
        self.last_notification_time = 0
        self.remaining_seconds = 0
        # Keep timer running to track downtime
        if not self.timer.isActive():
            self.timer.start(1000)
    
    def _stop_downtime(self):
        """Stop downtime tracking."""
        self.is_downtime_active = False
        self.downtime_seconds = 0
        self.last_notification_time = 0
    
    def _load_state(self):
        """Load timer state from settings."""
        self.state = TimerState.WORK
        self.remaining_seconds = self._get_timer_duration()
        self.previous_state = self.state
        self._update_display()
        self._apply_state_colors()
    
    def refresh_settings(self):
        """Refresh settings from database."""
        self.settings = self._load_settings()
        # Update downtime container visibility
        if hasattr(self, 'downtime_container'):
            self.downtime_container.setVisible(self.settings.enable_downtime)
        if not self.timer.isActive():
            self._load_state()
    
    def closeEvent(self, event):
        """Handle window close event."""
        if self.tray_icon and self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()

