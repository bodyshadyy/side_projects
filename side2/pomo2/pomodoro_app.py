"""
Main application class for Pomodoro app.
"""
from PyQt6.QtWidgets import (QMainWindow, QTabWidget, QMenuBar, QMenu,
                             QStatusBar, QSystemTrayIcon, QApplication)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QIcon
from timer_window import TimerWindow
from settings_dialog import SettingsDialog
from calendar_notes import CalendarNotesWidget
from todo_list import TodoListWidget
from eisenhower_matrix import EisenhowerMatrixWidget


class PomodoroApp(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.timer_window = None
        self.settings_dialog = None
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle("Pomodoro Timer")
        self.setMinimumSize(900, 700)
        
        # Apply modern styling
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QTabWidget::pane {
                border: 1px solid #ddd;
                background-color: white;
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                color: #555;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #4CAF50;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #bdbdbd;
            }
            QTabBar::tab:selected:hover {
                background-color: #45a049;
            }
            QMenuBar {
                background-color: #ffffff;
                border-bottom: 1px solid #e0e0e0;
            }
            QMenuBar::item {
                padding: 8px 15px;
                background-color: transparent;
            }
            QMenuBar::item:selected {
                background-color: #e3f2fd;
            }
            QMenu {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            QMenu::item:selected {
                background-color: #4CAF50;
                color: white;
            }
            QStatusBar {
                background-color: #f5f5f5;
                border-top: 1px solid #e0e0e0;
            }
        """)
        
        # Create menu bar
        self._create_menu_bar()
        
        # Create tabbed interface
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Timer tab
        self.timer_window = TimerWindow()
        self.timer_window.timer_completed.connect(self._on_timer_completed)
        self.tabs.addTab(self.timer_window, "Timer")
        
        # Set initial window icon from timer window
        self.setWindowIcon(self.timer_window.windowIcon())
        
        # Calendar/Notes tab
        self.calendar_notes = CalendarNotesWidget()
        self.tabs.addTab(self.calendar_notes, "Notes")
        
        # Todo List tab
        self.todo_list = TodoListWidget()
        self.tabs.addTab(self.todo_list, "Todos")
        
        # Eisenhower Matrix tab
        self.eisenhower = EisenhowerMatrixWidget()
        self.tabs.addTab(self.eisenhower, "Eisenhower")
        
        # Check for repeatable todos when switching to todos tab
        self.tabs.currentChanged.connect(self._on_tab_changed)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def _create_menu_bar(self):
        """Create the menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        settings_action = QAction("Settings", self)
        settings_action.setShortcut("Ctrl+S")
        settings_action.triggered.connect(self._show_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("View")
        
        timer_action = QAction("Timer", self)
        timer_action.triggered.connect(lambda: self.tabs.setCurrentIndex(0))
        view_menu.addAction(timer_action)
        
        notes_action = QAction("Notes", self)
        notes_action.triggered.connect(lambda: self.tabs.setCurrentIndex(1))
        view_menu.addAction(notes_action)
        
        todos_action = QAction("Todos", self)
        todos_action.triggered.connect(lambda: self.tabs.setCurrentIndex(2))
        view_menu.addAction(todos_action)
        
        eisenhower_action = QAction("Eisenhower", self)
        eisenhower_action.triggered.connect(lambda: self.tabs.setCurrentIndex(3))
        view_menu.addAction(eisenhower_action)
    
    def _show_settings(self):
        """Show settings dialog."""
        if self.settings_dialog is None:
            self.settings_dialog = SettingsDialog(self)
        
        if self.settings_dialog.exec():
            # Refresh timer window settings
            if self.timer_window:
                self.timer_window.refresh_settings()
            self.statusBar().showMessage("Settings updated", 2000)
    
    def _on_timer_completed(self, state_name: str):
        """Handle timer completion."""
        state_display = {
            'work': 'Work session completed!',
            'short_break': 'Short break completed!',
            'long_break': 'Long break completed!',
            'downtime': 'Downtime completed!'
        }
        message = state_display.get(state_name, 'Timer completed!')
        self.statusBar().showMessage(message, 3000)
        
        # Show system notification if available
        if QSystemTrayIcon.isSystemTrayAvailable():
            tray = QSystemTrayIcon(self)
            tray.showMessage("Pomodoro Timer", message, 
                           QSystemTrayIcon.MessageIcon.Information, 3000)
    
    def _on_tab_changed(self, index):
        """Handle tab change - check for repeatable todos when todos tab is selected."""
        if index == 2:  # Todos tab index
            from database import Database
            db = Database()
            db.handle_repeatable_todos()
            if self.todo_list:
                self.todo_list._load_todos()
        elif index == 3:  # Eisenhower tab index
            if self.eisenhower:
                self.eisenhower.refresh()
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Save any pending data
        event.accept()

