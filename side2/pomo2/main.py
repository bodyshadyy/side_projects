"""
Main entry point for Pomodoro app.
"""
import sys
from PyQt6.QtWidgets import QApplication
from pomodoro_app import PomodoroApp


def main():
    """Main function to run the application."""
    app = QApplication(sys.argv)
    app.setApplicationName("Pomodoro Timer")
    app.setOrganizationName("PomodoroApp")
    
    # Create and show main window
    window = PomodoroApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

