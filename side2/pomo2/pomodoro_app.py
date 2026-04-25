"""
Main application window for Pomodoro app.

Tab keyboard shortcuts:  Ctrl+1 … Ctrl+7
Menu shortcuts:          Ctrl+,  (Settings)   Ctrl+Q (Quit)
                         Ctrl+/  (Keyboard shortcuts help)
"""
from PyQt6.QtWidgets import (QMainWindow, QTabWidget, QSystemTrayIcon,
                              QApplication, QMessageBox)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QIcon
import sys
from pathlib import Path
from timer_window import TimerWindow
from settings_dialog import SettingsDialog
from calendar_notes import CalendarNotesWidget
from todo_list import TodoListWidget
from eisenhower_matrix import EisenhowerMatrixWidget
from daily_schedule import DailyScheduleWidget
from super_focus import SuperFocusWidget
from stats import StatsWidget
from ai_assistant import AIAssistantWidget
from mini_window import MiniTimerWindow
from prayer_times import PrayerTimesWidget
from theme import COLORS, is_dark_mode, save_theme_pref, apply_theme, build_app_stylesheet


class PomodoroApp(QMainWindow):
    """Top-level application window containing all tabs."""

    def __init__(self):
        super().__init__()
        self.timer_window    = None
        self.settings_dialog = None
        self.super_focus_active = False
        self.mini_window     = None
        self._init_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        self.setWindowTitle("Pomodoro Timer")
        self.setMinimumSize(960, 720)
        self._create_menu_bar()

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Timer
        self.timer_window = TimerWindow()
        self.timer_window.timer_completed.connect(self._on_timer_completed)
        self.timer_window.windowIconChanged.connect(self.setWindowIcon)
        self.tabs.addTab(self.timer_window, "⏱  Timer")
        self.setWindowIcon(self.timer_window.windowIcon())

        # Mini window (PiP) — created once, shown/hidden on demand
        self.mini_window = MiniTimerWindow()
        self.timer_window.mini_tick.connect(self.mini_window.update_timer)
        self.timer_window.desktop_switched.connect(self._on_desktop_switched)
        self.mini_window.closed.connect(self._on_mini_closed)
        self.mini_window.play_pause_requested.connect(self._mini_play_pause)
        self.mini_window.skip_requested.connect(self.timer_window.skip_timer)

        # Notes
        self.calendar_notes = CalendarNotesWidget()
        self.tabs.addTab(self.calendar_notes, "📝  Notes")

        # Todos
        self.todo_list = TodoListWidget()
        self.tabs.addTab(self.todo_list, "✅  Todos")

        # Eisenhower
        self.eisenhower = EisenhowerMatrixWidget()
        self.tabs.addTab(self.eisenhower, "🎯  Eisenhower")

        # Schedule
        self.daily_schedule = DailyScheduleWidget()
        self.tabs.addTab(self.daily_schedule, "📅  Schedule")

        # Statistics
        self.stats = StatsWidget()
        self.tabs.addTab(self.stats, "📊  Stats")

        # AI Assistant
        self.ai_assistant = AIAssistantWidget()
        self.tabs.addTab(self.ai_assistant, "🤖  Claude AI")

        # Prayer Times
        self.prayer_times = PrayerTimesWidget()
        self.tabs.addTab(self.prayer_times, "🕌  Prayers")

        # Super Focus
        self.super_focus = SuperFocusWidget()
        self.super_focus.focus_state_changed.connect(self._on_super_focus_state_changed)
        self.tabs.addTab(self.super_focus, "🔒  Focus")

        self.tabs.currentChanged.connect(self._on_tab_changed)

        self.statusBar().showMessage("Ready")

        # Per-tab keyboard shortcuts Ctrl+1 … Ctrl+8
        for idx, shortcut in enumerate(["Ctrl+1", "Ctrl+2", "Ctrl+3",
                                         "Ctrl+4", "Ctrl+5", "Ctrl+6",
                                         "Ctrl+7", "Ctrl+8"]):
            action = QAction(self)
            action.setShortcut(shortcut)
            action.triggered.connect(lambda checked, i=idx: self._switch_tab(i))
            self.addAction(action)

    # ── Menu bar ──────────────────────────────────────────────────────────────

    def _create_menu_bar(self) -> None:
        menubar = self.menuBar()

        # ── File ─────────────────────────────────────────────────────────────
        file_menu = menubar.addMenu("File")

        settings_action = QAction("Settings…", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._show_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        dark_label = "Switch to Light Mode" if is_dark_mode() else "Switch to Dark Mode"
        self.theme_action = QAction(dark_label, self)
        self.theme_action.triggered.connect(self._toggle_theme)
        file_menu.addAction(self.theme_action)

        file_menu.addSeparator()

        self.startup_action = QAction("Launch at Startup", self)
        self.startup_action.setCheckable(True)
        self.startup_action.setChecked(self._is_startup_enabled())
        self.startup_action.triggered.connect(self._toggle_startup)
        file_menu.addAction(self.startup_action)

        file_menu.addSeparator()

        exit_action = QAction("Quit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # ── View ─────────────────────────────────────────────────────────────
        view_menu = menubar.addMenu("View")
        tab_entries = [
            ("Timer",        "Ctrl+1", 0),
            ("Notes",        "Ctrl+2", 1),
            ("Todos",        "Ctrl+3", 2),
            ("Eisenhower",   "Ctrl+4", 3),
            ("Schedule",     "Ctrl+5", 4),
            ("Statistics",   "Ctrl+6", 5),
            ("Claude AI",    "Ctrl+7", 6),
            ("Super Focus",  "Ctrl+8", 7),
        ]
        for label, shortcut, idx in tab_entries:
            action = QAction(label, self)
            action.setShortcut(shortcut)
            action.triggered.connect(lambda checked, i=idx: self._switch_tab(i))
            view_menu.addAction(action)

        view_menu.addSeparator()
        self.mini_action = QAction("Mini Timer  (PiP)", self)
        self.mini_action.setShortcut("Ctrl+P")
        self.mini_action.setCheckable(True)
        self.mini_action.triggered.connect(self._toggle_mini_window)
        view_menu.addAction(self.mini_action)

        # ── Help ─────────────────────────────────────────────────────────────
        help_menu = menubar.addMenu("Help")

        kb_action = QAction("Keyboard Shortcuts", self)
        kb_action.setShortcut("Ctrl+/")
        kb_action.triggered.connect(self._show_shortcuts)
        help_menu.addAction(kb_action)

        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

    # ── Tab helpers ───────────────────────────────────────────────────────────

    def _switch_tab(self, index: int) -> None:
        if self.super_focus_active:
            sf_idx = self.tabs.indexOf(self.super_focus)
            if index != sf_idx:
                return
        self.tabs.setCurrentIndex(index)

    def _on_tab_changed(self, index: int) -> None:
        if self.super_focus_active:
            sf_idx = self.tabs.indexOf(self.super_focus)
            if index != sf_idx:
                self.tabs.setCurrentIndex(sf_idx)
                return

        if index == 2:      # Todos
            from database import Database
            Database().handle_repeatable_todos()
            if self.todo_list:
                self.todo_list._load_todos()
        elif index == 3:    # Eisenhower
            if self.eisenhower:
                self.eisenhower.refresh()
        elif index == 4:    # Schedule
            if self.daily_schedule:
                self.daily_schedule._load_schedule()
        elif index == 5:    # Statistics
            if self.stats:
                self.stats.refresh()
        elif index == 7:    # Super Focus
            if self.super_focus:
                self.super_focus.refresh_settings()

        if index == 0 and self.timer_window:
            self.timer_window.setFocus()

    # ── Mini window (PiP) ─────────────────────────────────────────────────────

    def _toggle_mini_window(self) -> None:
        if self.mini_window.isVisible():
            self.mini_window.hide()
            self.mini_action.setChecked(False)
        else:
            self.mini_window.show()
            self.mini_action.setChecked(True)

    def _on_mini_closed(self) -> None:
        self.mini_action.setChecked(False)

    def _mini_play_pause(self) -> None:
        tw = self.timer_window
        if tw.is_downtime_active:
            return
        if tw.timer.isActive():
            tw.pause_timer()
        else:
            tw.start_timer()

    def _on_desktop_switched(self) -> None:
        """Auto-show the mini PiP window after a desktop switch so the timer stays visible."""
        if not self.mini_window.isVisible():
            self.mini_window.show()
            self.mini_action.setChecked(True)

    # ── Settings dialog ───────────────────────────────────────────────────────

    def _show_settings(self) -> None:
        if self.settings_dialog is None:
            self.settings_dialog = SettingsDialog(self)
        if self.settings_dialog.exec():
            if self.timer_window:
                self.timer_window.refresh_settings()
            if self.super_focus:
                self.super_focus.refresh_settings()
            self.statusBar().showMessage("Settings saved.", 3000)
        self.settings_dialog = None   # allow re-creation next time

    # ── Startup registration ──────────────────────────────────────────────────

    @staticmethod
    def _startup_lnk_path() -> Path:
        startup = (Path.home() /
                   "AppData" / "Roaming" /
                   "Microsoft" / "Windows" / "Start Menu" /
                   "Programs" / "Startup" / "Pomodoro Timer.lnk")
        return startup

    def _is_startup_enabled(self) -> bool:
        return self._startup_lnk_path().exists()

    def _toggle_startup(self) -> None:
        lnk = self._startup_lnk_path()
        if lnk.exists():
            try:
                lnk.unlink()
                self.startup_action.setChecked(False)
                self.statusBar().showMessage("Removed from startup.", 3000)
            except Exception as e:
                QMessageBox.warning(self, "Startup", f"Could not remove shortcut:\n{e}")
                self.startup_action.setChecked(True)
        else:
            try:
                self._create_startup_shortcut(lnk)
                self.startup_action.setChecked(True)
                self.statusBar().showMessage("Added to startup — launches on next login.", 4000)
            except Exception as e:
                QMessageBox.warning(self, "Startup", f"Could not create shortcut:\n{e}")
                self.startup_action.setChecked(False)

    def _create_startup_shortcut(self, lnk_path: Path) -> None:
        script_dir  = Path(__file__).parent.absolute()
        main_script = script_dir / "main.py"
        icon_file   = script_dir / "data" / "pomo.ico"

        # Find pythonw.exe
        pythonw = Path(sys.executable)
        for d in [pythonw.parent, *pythonw.parents]:
            pw = d / "pythonw.exe"
            if pw.exists():
                pythonw = pw
                break

        icon_loc = f"{icon_file},0" if icon_file.exists() else str(pythonw)

        try:
            import win32com.client
            sh  = win32com.client.Dispatch("WScript.Shell")
            s   = sh.CreateShortCut(str(lnk_path))
            s.Targetpath       = str(pythonw)
            s.Arguments        = f'"{main_script}"'
            s.WorkingDirectory = str(script_dir)
            s.IconLocation     = icon_loc
            s.Description      = "Pomodoro Timer"
            s.save()
        except ImportError:
            import subprocess
            ps = (
                f'$ws = New-Object -ComObject WScript.Shell; '
                f'$s = $ws.CreateShortcut("{lnk_path}"); '
                f'$s.TargetPath = "{pythonw}"; '
                f'$s.Arguments = \'"{main_script}"\'; '
                f'$s.WorkingDirectory = "{script_dir}"; '
                f'$s.IconLocation = "{icon_loc}"; '
                f'$s.Description = "Pomodoro Timer"; '
                f'$s.Save()'
            )
            subprocess.run(["powershell", "-Command", ps], check=True)

    # ── Theme toggle ──────────────────────────────────────────────────────────

    def _toggle_theme(self) -> None:
        QMessageBox.information(
            self,
            "Theme Change",
            "The theme will be applied the next time you start the app.\n\n"
            "The preference has been saved."
        )
        new_dark = not is_dark_mode()
        save_theme_pref(new_dark)
        label = "Switch to Light Mode" if new_dark else "Switch to Dark Mode"
        self.theme_action.setText(label)

    # ── Timer completion ──────────────────────────────────────────────────────

    def _on_timer_completed(self, state_name: str) -> None:
        messages = {
            "work":        "Work session complete — time for a break!",
            "short_break": "Break over — back to work!",
            "long_break":  "Long break done — ready to focus?",
            "downtime":    "Heads up: downtime threshold reached.",
        }
        msg = messages.get(state_name, "Timer complete!")
        self.statusBar().showMessage(msg, 4000)

        if QSystemTrayIcon.isSystemTrayAvailable():
            tray = QSystemTrayIcon(self)
            tray.showMessage("Pomodoro Timer", msg,
                             QSystemTrayIcon.MessageIcon.Information, 3000)

    # ── Super Focus lock / unlock ─────────────────────────────────────────────

    def _on_super_focus_state_changed(self, active: bool) -> None:
        self.super_focus_active = active
        sf_idx = self.tabs.indexOf(self.super_focus)

        if active:
            if self.timer_window and self.timer_window.timer.isActive():
                self.timer_window.pause_timer()
            for i in range(self.tabs.count()):
                self.tabs.setTabEnabled(i, i == sf_idx)
            self.tabs.setCurrentIndex(sf_idx)
            self.statusBar().showMessage(
                "Super Focus active — all other tabs are locked.", 0
            )
        else:
            for i in range(self.tabs.count()):
                self.tabs.setTabEnabled(i, True)
            self.statusBar().showMessage("Super Focus ended. Tabs unlocked.", 3000)

    # ── Help dialogs ──────────────────────────────────────────────────────────

    def _show_shortcuts(self) -> None:
        shortcuts = (
            "<h3 style='margin:0 0 12px'>Keyboard Shortcuts</h3>"
            "<table cellspacing='6'>"
            "<tr><td><b>Space</b></td><td>Start / Pause timer</td></tr>"
            "<tr><td><b>R</b></td><td>Reset current phase</td></tr>"
            "<tr><td><b>S</b></td><td>Skip to next phase</td></tr>"
            "<tr><td><b>M</b></td><td>Toggle mute</td></tr>"
            "<tr><td><b>Ctrl+1…8</b></td><td>Switch tabs</td></tr>"
            "<tr><td><b>Ctrl+P</b></td><td>Toggle Mini Timer (PiP)</td></tr>"
            "<tr><td><b>Ctrl+,</b></td><td>Open Settings</td></tr>"
            "<tr><td><b>Ctrl+Q</b></td><td>Quit</td></tr>"
            "<tr><td><b>Ctrl+S</b></td><td>Save note (Notes tab)</td></tr>"
            "<tr><td><b>Enter</b></td><td>Send AI message (AI tab)</td></tr>"
            "<tr><td><b>Shift+Enter</b></td><td>New line in AI input</td></tr>"
            "<tr><td><b>Ctrl+/</b></td><td>This help</td></tr>"
            "</table>"
        )
        msg = QMessageBox(self)
        msg.setWindowTitle("Keyboard Shortcuts")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(shortcuts)
        msg.exec()

    def _show_about(self) -> None:
        msg = QMessageBox(self)
        msg.setWindowTitle("About Pomodoro Timer")
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setText(
            "<b>Pomodoro Timer</b><br>"
            "A full-featured productivity app with:<br>"
            "• Pomodoro timer with session tracking<br>"
            "• Daily notes with auto-save<br>"
            "• Todo list with priorities &amp; recurrence<br>"
            "• Eisenhower priority matrix<br>"
            "• Daily schedule with Google Calendar export<br>"
            "• Statistics &amp; streaks<br>"
            "• Super Focus mode<br>"
        )
        msg.exec()

    # ── Window close ─────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:
        event.accept()
