"""
Settings dialog for Pomodoro app.
"""
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QSpinBox, QCheckBox, QFormLayout,
                             QMessageBox, QFileDialog, QLineEdit, QGroupBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from database import Database
from models import Settings


class SettingsDialog(QDialog):
    """Settings configuration dialog."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = Database()
        self.settings = self._load_settings()
        self._init_ui()
    
    def _load_settings(self) -> Settings:
        """Load settings from database."""
        settings_data = self.db.get_settings()
        if settings_data:
            return Settings.from_dict(settings_data)
        return Settings()
    
    def _init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle("Settings")
        self.setMinimumSize(500, 600)
        
        # Apply modern styling
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton#cancelBtn {
                background-color: #f44336;
            }
            QPushButton#cancelBtn:hover {
                background-color: #da190b;
            }
            QLineEdit {
                padding: 5px;
                border: 1px solid #ddd;
                border-radius: 3px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Timer Settings Group
        timer_group = QGroupBox("Timer Settings")
        timer_layout = QFormLayout()
        timer_layout.setSpacing(12)
        
        # Work time (minutes and seconds)
        work_layout = QHBoxLayout()
        work_layout.setSpacing(5)
        self.work_min_spin = QSpinBox()
        self.work_min_spin.setRange(0, 120)
        self.work_min_spin.setValue(self.settings.work_time // 60)
        self.work_min_spin.setSuffix(" min")
        self.work_sec_spin = QSpinBox()
        self.work_sec_spin.setRange(0, 59)
        self.work_sec_spin.setValue(self.settings.work_time % 60)
        self.work_sec_spin.setSuffix(" sec")
        work_layout.addWidget(self.work_min_spin)
        work_layout.addWidget(self.work_sec_spin)
        work_layout.addStretch()
        timer_layout.addRow("Work Time:", work_layout)
        
        # Short break (minutes and seconds)
        short_layout = QHBoxLayout()
        short_layout.setSpacing(5)
        self.short_min_spin = QSpinBox()
        self.short_min_spin.setRange(0, 60)
        self.short_min_spin.setValue(self.settings.short_break // 60)
        self.short_min_spin.setSuffix(" min")
        self.short_sec_spin = QSpinBox()
        self.short_sec_spin.setRange(0, 59)
        self.short_sec_spin.setValue(self.settings.short_break % 60)
        self.short_sec_spin.setSuffix(" sec")
        short_layout.addWidget(self.short_min_spin)
        short_layout.addWidget(self.short_sec_spin)
        short_layout.addStretch()
        timer_layout.addRow("Short Break:", short_layout)
        
        # Long break (minutes and seconds)
        long_layout = QHBoxLayout()
        long_layout.setSpacing(5)
        self.long_min_spin = QSpinBox()
        self.long_min_spin.setRange(0, 120)
        self.long_min_spin.setValue(self.settings.long_break // 60)
        self.long_min_spin.setSuffix(" min")
        self.long_sec_spin = QSpinBox()
        self.long_sec_spin.setRange(0, 59)
        self.long_sec_spin.setValue(self.settings.long_break % 60)
        self.long_sec_spin.setSuffix(" sec")
        long_layout.addWidget(self.long_min_spin)
        long_layout.addWidget(self.long_sec_spin)
        long_layout.addStretch()
        timer_layout.addRow("Long Break:", long_layout)
        
        # Downtime (minutes and seconds)
        down_layout = QHBoxLayout()
        down_layout.setSpacing(5)
        self.down_min_spin = QSpinBox()
        self.down_min_spin.setRange(0, 60)
        self.down_min_spin.setValue(self.settings.downtime // 60)
        self.down_min_spin.setSuffix(" min")
        self.down_sec_spin = QSpinBox()
        self.down_sec_spin.setRange(0, 59)
        self.down_sec_spin.setValue(self.settings.downtime % 60)
        self.down_sec_spin.setSuffix(" sec")
        down_layout.addWidget(self.down_min_spin)
        down_layout.addWidget(self.down_sec_spin)
        down_layout.addStretch()
        timer_layout.addRow("Downtime:", down_layout)
        
        timer_group.setLayout(timer_layout)
        layout.addWidget(timer_group)
        
        # Options Group
        options_group = QGroupBox("Options")
        options_layout = QFormLayout()
        options_layout.setSpacing(12)
        
        # Auto-start checkbox
        self.auto_start_check = QCheckBox()
        self.auto_start_check.setChecked(self.settings.auto_start)
        options_layout.addRow("Auto Start:", self.auto_start_check)
        
        # Enable downtime checkbox
        self.enable_downtime_check = QCheckBox()
        self.enable_downtime_check.setChecked(self.settings.enable_downtime)
        options_layout.addRow("Enable Downtime:", self.enable_downtime_check)
        
        # Downtime notification threshold
        notify_layout = QHBoxLayout()
        notify_layout.setSpacing(5)
        self.notify_min_spin = QSpinBox()
        self.notify_min_spin.setRange(0, 120)
        threshold_value = self.settings.downtime_notify_threshold if self.settings.downtime_notify_threshold > 0 else 300
        self.notify_min_spin.setValue(threshold_value // 60)
        self.notify_min_spin.setSuffix(" min")
        notify_layout.addWidget(self.notify_min_spin)
        
        self.notify_sec_spin = QSpinBox()
        self.notify_sec_spin.setRange(0, 59)
        self.notify_sec_spin.setValue(threshold_value % 60)
        self.notify_sec_spin.setSuffix(" sec")
        notify_layout.addWidget(self.notify_sec_spin)
        notify_layout.addStretch()
        
        options_layout.addRow("Notify After Downtime:", notify_layout)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Alarm Sounds Group
        sound_group = QGroupBox("Alarm Sounds")
        sound_layout = QVBoxLayout()
        sound_layout.setSpacing(15)
        
        # Work Time Sound
        work_sound_layout = QHBoxLayout()
        work_sound_label = QLabel("Work Time:")
        work_sound_label.setMinimumWidth(100)
        work_sound_layout.addWidget(work_sound_label)
        
        self.work_sound_edit = QLineEdit()
        self.work_sound_edit.setPlaceholderText("No sound file selected")
        if self.settings.alarm_sound_path:
            self.work_sound_edit.setText(self.settings.alarm_sound_path)
        self.work_sound_edit.setReadOnly(True)
        work_sound_layout.addWidget(self.work_sound_edit)
        
        work_browse = QPushButton("Browse...")
        work_browse.clicked.connect(lambda: self._browse_sound_file(self.work_sound_edit))
        work_browse.setMaximumWidth(100)
        work_sound_layout.addWidget(work_browse)
        
        work_clear = QPushButton("Clear")
        work_clear.clicked.connect(lambda: self.work_sound_edit.clear())
        work_clear.setMaximumWidth(80)
        work_sound_layout.addWidget(work_clear)
        
        sound_layout.addLayout(work_sound_layout)
        
        # Short Break Sound
        short_sound_layout = QHBoxLayout()
        short_sound_label = QLabel("Short Break:")
        short_sound_label.setMinimumWidth(100)
        short_sound_layout.addWidget(short_sound_label)
        
        self.short_sound_edit = QLineEdit()
        self.short_sound_edit.setPlaceholderText("No sound file selected")
        if self.settings.short_break_sound_path:
            self.short_sound_edit.setText(self.settings.short_break_sound_path)
        self.short_sound_edit.setReadOnly(True)
        short_sound_layout.addWidget(self.short_sound_edit)
        
        short_browse = QPushButton("Browse...")
        short_browse.clicked.connect(lambda: self._browse_sound_file(self.short_sound_edit))
        short_browse.setMaximumWidth(100)
        short_sound_layout.addWidget(short_browse)
        
        short_clear = QPushButton("Clear")
        short_clear.clicked.connect(lambda: self.short_sound_edit.clear())
        short_clear.setMaximumWidth(80)
        short_sound_layout.addWidget(short_clear)
        
        sound_layout.addLayout(short_sound_layout)
        
        # Long Break Sound
        long_sound_layout = QHBoxLayout()
        long_sound_label = QLabel("Long Break:")
        long_sound_label.setMinimumWidth(100)
        long_sound_layout.addWidget(long_sound_label)
        
        self.long_sound_edit = QLineEdit()
        self.long_sound_edit.setPlaceholderText("No sound file selected")
        if self.settings.long_break_sound_path:
            self.long_sound_edit.setText(self.settings.long_break_sound_path)
        self.long_sound_edit.setReadOnly(True)
        long_sound_layout.addWidget(self.long_sound_edit)
        
        long_browse = QPushButton("Browse...")
        long_browse.clicked.connect(lambda: self._browse_sound_file(self.long_sound_edit))
        long_browse.setMaximumWidth(100)
        long_sound_layout.addWidget(long_browse)
        
        long_clear = QPushButton("Clear")
        long_clear.clicked.connect(lambda: self.long_sound_edit.clear())
        long_clear.setMaximumWidth(80)
        long_sound_layout.addWidget(long_clear)
        
        sound_layout.addLayout(long_sound_layout)

        # Downtime Sound
        downtime_sound_layout = QHBoxLayout()
        downtime_sound_label = QLabel("Downtime:")
        downtime_sound_label.setMinimumWidth(100)
        downtime_sound_layout.addWidget(downtime_sound_label)
        
        self.downtime_sound_edit = QLineEdit()
        self.downtime_sound_edit.setPlaceholderText("No sound file selected")
        if self.settings.downtime_sound_path:
            self.downtime_sound_edit.setText(self.settings.downtime_sound_path)
        self.downtime_sound_edit.setReadOnly(True)
        downtime_sound_layout.addWidget(self.downtime_sound_edit)
        
        downtime_browse = QPushButton("Browse...")
        downtime_browse.clicked.connect(lambda: self._browse_sound_file(self.downtime_sound_edit))
        downtime_browse.setMaximumWidth(100)
        downtime_sound_layout.addWidget(downtime_browse)
        
        downtime_clear = QPushButton("Clear")
        downtime_clear.clicked.connect(lambda: self.downtime_sound_edit.clear())
        downtime_clear.setMaximumWidth(80)
        downtime_sound_layout.addWidget(downtime_clear)
        
        sound_layout.addLayout(downtime_sound_layout)
        
        sound_group.setLayout(sound_layout)
        layout.addWidget(sound_group)
        
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_settings)
        save_button.setMinimumWidth(100)
        save_button.setMinimumHeight(35)
        button_layout.addWidget(save_button)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("cancelBtn")
        cancel_button.clicked.connect(self.reject)
        cancel_button.setMinimumWidth(100)
        cancel_button.setMinimumHeight(35)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _browse_sound_file(self, line_edit):
        """Browse for MP3 sound file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Alarm Sound File",
            "",
            "Audio Files (*.mp3 *.wav *.ogg);;All Files (*)"
        )
        if file_path:
            line_edit.setText(file_path)
    
    def save_settings(self):
        """Save settings to database."""
        try:
            # Convert minutes and seconds to total seconds
            self.settings.work_time = (self.work_min_spin.value() * 60) + self.work_sec_spin.value()
            self.settings.short_break = (self.short_min_spin.value() * 60) + self.short_sec_spin.value()
            self.settings.long_break = (self.long_min_spin.value() * 60) + self.long_sec_spin.value()
            self.settings.downtime = (self.down_min_spin.value() * 60) + self.down_sec_spin.value()
            self.settings.auto_start = self.auto_start_check.isChecked()
            self.settings.enable_downtime = self.enable_downtime_check.isChecked()
            
            # Calculate downtime notification threshold
            notify_threshold = (self.notify_min_spin.value() * 60) + self.notify_sec_spin.value()
            # Ensure minimum of 1 second if both are 0
            if notify_threshold == 0:
                notify_threshold = 1
            self.settings.downtime_notify_threshold = notify_threshold
            
            self.settings.alarm_sound_path = self.work_sound_edit.text().strip()
            self.settings.short_break_sound_path = self.short_sound_edit.text().strip()
            self.settings.long_break_sound_path = self.long_sound_edit.text().strip()
            self.settings.downtime_sound_path = self.downtime_sound_edit.text().strip()
            
            # Validate that at least one timer has a duration
            if self.settings.work_time == 0 and self.settings.short_break == 0 and \
               self.settings.long_break == 0:
                QMessageBox.warning(self, "Validation Error", 
                                   "At least one timer must have a duration greater than 0.")
                return
            
            # Validate downtime notification threshold
            if self.settings.enable_downtime and self.settings.downtime_notify_threshold < 1:
                QMessageBox.warning(self, "Validation Error",
                                   "Downtime notification threshold must be at least 1 second.")
                return
            
            self.db.update_settings(self.settings.to_dict())
            
            QMessageBox.information(self, "Settings", "Settings saved successfully!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings: {str(e)}")
    
    def get_settings(self) -> Settings:
        """Get current settings."""
        return self.settings

