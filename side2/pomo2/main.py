"""
Main entry point for Pomodoro app.
"""
import sys
import platform
import ctypes
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

# Apply theme before any widgets are constructed so all stylesheet references
# to COLORS pick up the correct palette.
from theme import apply_theme, is_dark_mode, build_app_stylesheet
apply_theme(is_dark_mode())

from pomodoro_app import PomodoroApp


def main():
    if platform.system() == "Windows":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "PomodoroApp.Timer"
            )
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("Pomodoro Timer")
    app.setOrganizationName("PomodoroApp")

    # Apply the global stylesheet (covers common widgets app-wide).
    app.setStyleSheet(build_app_stylesheet())

    window = PomodoroApp()
    app.setWindowIcon(window.windowIcon())
    window.show()

    # Re-apply once the window is fully shown to make taskbar icon stick on Windows.
    QTimer.singleShot(100, lambda: app.setWindowIcon(window.windowIcon()))

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
