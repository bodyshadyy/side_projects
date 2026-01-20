"""
Calendar and notes interface for Pomodoro app.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QCalendarWidget, QTextEdit, QPushButton)
from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtGui import QFont
from datetime import datetime
from database import Database


class CalendarNotesWidget(QWidget):
    """Calendar and notes widget."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = Database()
        self.current_date = datetime.now().date()
        self._init_ui()
        self._load_note_for_date()
    
    def _init_ui(self):
        """Initialize the UI."""
        self.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
            }
            QLabel {
                color: #333;
            }
            QCalendarWidget {
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
            }
            QCalendarWidget QTableView {
                selection-background-color: #4CAF50;
                selection-color: white;
            }
            QTextEdit {
                border: 2px solid #e0e0e0;
                border-radius: 5px;
                padding: 10px;
                font-size: 12px;
                background-color: #fafafa;
            }
            QTextEdit:focus {
                border-color: #4CAF50;
                background-color: white;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 13px;
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
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Title
        title = QLabel("📝 Daily Notes")
        title_font = QFont()
        title_font.setPointSize(22)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Calendar widget
        self.calendar = QCalendarWidget()
        self.calendar.setSelectedDate(QDate.currentDate())
        self.calendar.selectionChanged.connect(self._on_date_selected)
        layout.addWidget(self.calendar)
        
        # Selected date label
        self.date_label = QLabel()
        self._update_date_label()
        date_font = QFont()
        date_font.setPointSize(14)
        date_font.setBold(True)
        self.date_label.setFont(date_font)
        self.date_label.setStyleSheet("color: #4CAF50; padding: 10px; background-color: #e8f5e9; border-radius: 5px;")
        layout.addWidget(self.date_label)
        
        # Notes editor
        notes_label = QLabel("Notes:")
        notes_label.setFont(QFont("", 13, QFont.Weight.Bold))
        notes_label.setStyleSheet("color: #555; margin-top: 10px;")
        layout.addWidget(notes_label)
        
        self.notes_editor = QTextEdit()
        self.notes_editor.setPlaceholderText("Enter your notes for this day...")
        self.notes_editor.setMinimumHeight(250)
        layout.addWidget(self.notes_editor)
        
        # Save button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.save_button = QPushButton("💾 Save Note")
        self.save_button.clicked.connect(self._save_note)
        self.save_button.setMinimumWidth(140)
        self.save_button.setMinimumHeight(40)
        button_layout.addWidget(self.save_button)
        
        layout.addLayout(button_layout)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def _update_date_label(self):
        """Update the date label."""
        date_str = self.current_date.strftime("%A, %B %d, %Y")
        self.date_label.setText(f"Selected Date: {date_str}")
    
    def _on_date_selected(self):
        """Handle date selection change."""
        selected_date = self.calendar.selectedDate()
        self.current_date = selected_date.toPyDate()
        self._update_date_label()
        self._load_note_for_date()
    
    def _load_note_for_date(self):
        """Load note for the current selected date."""
        date_str = self.current_date.strftime("%Y-%m-%d")
        note = self.db.get_note(date_str)
        if note:
            self.notes_editor.setPlainText(note)
        else:
            self.notes_editor.clear()
    
    def _save_note(self):
        """Save the current note."""
        date_str = self.current_date.strftime("%Y-%m-%d")
        note_text = self.notes_editor.toPlainText()
        self.db.save_note(date_str, note_text)
        
        # Visual feedback
        original_text = self.save_button.text()
        self.save_button.setText("Saved!")
        self.save_button.setEnabled(False)
        
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: (
            self.save_button.setText(original_text),
            self.save_button.setEnabled(True)
        ))

