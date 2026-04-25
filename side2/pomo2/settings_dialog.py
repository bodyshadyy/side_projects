"""
Settings dialog for Pomodoro app.
"""
import json
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QSpinBox, QCheckBox, QFormLayout,
                              QMessageBox, QFileDialog, QLineEdit, QGroupBox,
                              QWidget, QTabWidget, QComboBox, QInputDialog,
                              QFrame)
from PyQt6.QtCore import Qt
from database import Database
from models import Settings
from theme import COLORS


class SettingsDialog(QDialog):
    """Settings configuration dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = Database()
        self.settings = self._load_settings()
        self.super_focus_settings = self.db.get_super_focus_settings()
        self.presets_store = self._load_presets_store()
        self._init_ui()

    # ── Data helpers ──────────────────────────────────────────────────────────

    def _load_settings(self) -> Settings:
        data = self.db.get_settings()
        return Settings.from_dict(data) if data else Settings()

    def _presets_file_path(self) -> Path:
        d = Path(__file__).parent / "data"
        d.mkdir(exist_ok=True)
        return d / "timer_presets.json"

    def _default_presets_store(self) -> dict:
        return {
            "presets": {
                "Weekday": {
                    "work_time": 25 * 60, "short_break": 5 * 60,
                    "long_break": 15 * 60, "downtime": 0,
                    "downtime_notify_threshold": 5 * 60,
                },
                "Weekend": {
                    "work_time": 50 * 60, "short_break": 10 * 60,
                    "long_break": 20 * 60, "downtime": 0,
                    "downtime_notify_threshold": 8 * 60,
                },
            },
            "auto_apply": False,
            "weekday_preset": "Weekday",
            "weekend_preset": "Weekend",
        }

    def _load_presets_store(self) -> dict:
        path = self._presets_file_path()
        default = self._default_presets_store()
        if not path.exists():
            path.write_text(json.dumps(default, indent=2))
            return default
        try:
            loaded = json.loads(path.read_text())
            if not isinstance(loaded, dict):
                return default
            merged = default.copy()
            merged.update(loaded)
            if not isinstance(merged.get("presets"), dict):
                merged["presets"] = default["presets"].copy()
            return merged
        except Exception:
            return default

    def _save_presets_store(self):
        self._presets_file_path().write_text(json.dumps(self.presets_store, indent=2))

    # ── UI ────────────────────────────────────────────────────────────────────

    def _init_ui(self):
        self.setWindowTitle("Settings")
        self.setMinimumSize(760, 620)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {COLORS['bg']}; }}
            QLabel  {{ color: {COLORS['text']}; }}
            QGroupBox {{
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                margin-top: 12px;
                background-color: {COLORS['surface']};
                font-weight: 700;
                padding-top: 10px;
                color: {COLORS['text']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin; left: 12px;
                padding: 0 6px; color: {COLORS['text_sec']};
            }}
            QTabWidget::pane {{
                border: 1px solid {COLORS['border']};
                border-radius: 10px;
                background: {COLORS['surface']};
            }}
            QTabBar::tab {{
                background: {COLORS['surface_alt']};
                color: {COLORS['text_sec']};
                border: 1px solid {COLORS['border']};
                padding: 9px 16px; margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                background: {COLORS['accent']};
                color: white; border-color: {COLORS['accent']};
            }}
            QSpinBox, QLineEdit, QComboBox {{
                border: 1px solid {COLORS['border']};
                border-radius: 8px; padding: 6px 10px;
                background-color: {COLORS['input_bg']};
                min-height: 20px;
                color: {COLORS['text']};
            }}
            QSpinBox:focus, QLineEdit:focus, QComboBox:focus {{
                border-color: {COLORS['accent']};
            }}
            QCheckBox {{ color: {COLORS['text']}; spacing: 8px; }}
            QCheckBox::indicator {{
                width: 18px; height: 18px; border-radius: 4px;
                border: 2px solid {COLORS['border']};
                background: {COLORS['input_bg']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLORS['accent']};
                border-color: {COLORS['accent']};
            }}
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white; border: none; border-radius: 8px;
                padding: 8px 14px; font-weight: 600;
            }}
            QPushButton:hover {{ background-color: {COLORS['accent_hover']}; }}
            QPushButton#secondaryBtn {{
                background-color: {COLORS['surface_alt']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
            }}
            QPushButton#secondaryBtn:hover {{ background-color: {COLORS['border']}; }}
            QPushButton#dangerBtn {{ background-color: {COLORS['danger']}; }}
            QPushButton#dangerBtn:hover {{ background-color: #dc2626; }}
        """)

        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(20, 20, 20, 20)

        title = QLabel("Settings")
        title.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {COLORS['text']};")
        sub = QLabel("Configure timer durations, presets, sounds, and behavior.")
        sub.setStyleSheet(f"font-size: 12px; color: {COLORS['text_sec']};")
        root.addWidget(title)
        root.addWidget(sub)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_timer_tab(),    "Timer & Presets")
        self.tabs.addTab(self._build_behavior_tab(), "Behavior")
        self.tabs.addTab(self._build_sounds_tab(),   "Sounds")
        root.addWidget(self.tabs, 1)

        footer = QHBoxLayout()
        footer.addStretch()
        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryBtn")
        cancel.clicked.connect(self.reject)
        cancel.setMinimumWidth(110)
        save = QPushButton("Save Settings")
        save.clicked.connect(self.save_settings)
        save.setMinimumWidth(140)
        footer.addWidget(cancel)
        footer.addWidget(save)
        root.addLayout(footer)

    # ── Time row helper ───────────────────────────────────────────────────────

    def _make_time_row(self, min_val, sec_val, min_max):
        row  = QHBoxLayout()
        mins = QSpinBox(); mins.setRange(0, min_max); mins.setValue(min_val); mins.setSuffix(" min")
        secs = QSpinBox(); secs.setRange(0, 59);      secs.setValue(sec_val); secs.setSuffix(" sec")
        row.addWidget(mins); row.addWidget(secs); row.addStretch()
        return row, mins, secs

    # ── Timer & Presets tab ───────────────────────────────────────────────────

    def _build_timer_tab(self) -> QWidget:
        page   = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        # Presets
        presets_group = QGroupBox("Presets")
        pg = QVBoxLayout()

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Preset"))
        self.preset_combo = QComboBox()
        row1.addWidget(self.preset_combo, 1)
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._apply_selected_preset)
        row1.addWidget(apply_btn)
        pg.addLayout(row1)

        row2 = QHBoxLayout()
        save_as_btn = QPushButton("Save As New"); save_as_btn.setObjectName("secondaryBtn")
        save_as_btn.clicked.connect(self._save_as_new_preset)
        update_btn  = QPushButton("Update Selected"); update_btn.setObjectName("secondaryBtn")
        update_btn.clicked.connect(self._update_selected_preset)
        delete_btn  = QPushButton("Delete"); delete_btn.setObjectName("dangerBtn")
        delete_btn.clicked.connect(self._delete_selected_preset)
        row2.addWidget(save_as_btn); row2.addWidget(update_btn)
        row2.addWidget(delete_btn); row2.addStretch()
        pg.addLayout(row2)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {COLORS['border']};")
        pg.addWidget(sep)

        self.auto_apply_check = QCheckBox("Auto-apply preset by day of week")
        self.auto_apply_check.setChecked(bool(self.presets_store.get("auto_apply", False)))
        pg.addWidget(self.auto_apply_check)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Weekday Preset"))
        self.weekday_preset_combo = QComboBox()
        row3.addWidget(self.weekday_preset_combo, 1)
        row3.addWidget(QLabel("Weekend Preset"))
        self.weekend_preset_combo = QComboBox()
        row3.addWidget(self.weekend_preset_combo, 1)
        pg.addLayout(row3)

        presets_group.setLayout(pg)
        layout.addWidget(presets_group)

        # Timer values
        timer_group = QGroupBox("Current Timer Values")
        form = QFormLayout(); form.setSpacing(10)

        s = self.settings
        work_row,   self.work_min_spin,   self.work_sec_spin   = self._make_time_row(s.work_time // 60,   s.work_time % 60,   180)
        short_row,  self.short_min_spin,  self.short_sec_spin  = self._make_time_row(s.short_break // 60, s.short_break % 60,  90)
        long_row,   self.long_min_spin,   self.long_sec_spin   = self._make_time_row(s.long_break // 60,  s.long_break % 60,  180)
        down_row,   self.down_min_spin,   self.down_sec_spin   = self._make_time_row(s.downtime // 60,    s.downtime % 60,    120)
        nt = s.downtime_notify_threshold or 300
        notify_row, self.notify_min_spin, self.notify_sec_spin = self._make_time_row(nt // 60, nt % 60, 180)

        form.addRow("Work",                work_row)
        form.addRow("Short Break",         short_row)
        form.addRow("Long Break",          long_row)
        form.addRow("Downtime",            down_row)
        form.addRow("Downtime Notify After", notify_row)
        timer_group.setLayout(form)
        layout.addWidget(timer_group)
        layout.addStretch()

        self._refresh_preset_controls()
        return page

    # ── Behavior tab ──────────────────────────────────────────────────────────

    def _build_behavior_tab(self) -> QWidget:
        page   = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        general_group = QGroupBox("General")
        form = QFormLayout()
        self.auto_start_check = QCheckBox()
        self.auto_start_check.setChecked(self.settings.auto_start)
        self.enable_downtime_check = QCheckBox()
        self.enable_downtime_check.setChecked(self.settings.enable_downtime)
        form.addRow("Auto-start next phase", self.auto_start_check)
        form.addRow("Enable Downtime tracking", self.enable_downtime_check)
        general_group.setLayout(form)
        layout.addWidget(general_group)

        focus_group = QGroupBox("Super Focus")
        ff = QFormLayout()
        self.super_focus_mode_check = QCheckBox()
        self.super_focus_mode_check.setChecked(self.super_focus_settings.get("enabled", False))
        self.super_focus_duration_spin = QSpinBox()
        self.super_focus_duration_spin.setRange(1, 240)
        self.super_focus_duration_spin.setValue(self.super_focus_settings.get("duration_minutes", 60))
        self.super_focus_duration_spin.setSuffix(" min")
        ff.addRow("Enabled", self.super_focus_mode_check)
        ff.addRow("Default Duration", self.super_focus_duration_spin)
        focus_group.setLayout(ff)
        layout.addWidget(focus_group)

        desktop_group = QGroupBox("Virtual Desktop Switching (Windows)")
        df = QFormLayout()

        self.switch_desktop_check = QCheckBox()
        self.switch_desktop_check.setChecked(self.settings.switch_desktop)
        self.switch_desktop_check.stateChanged.connect(self._toggle_desktop_options)

        self.work_desktop_spin = QSpinBox()
        self.work_desktop_spin.setRange(1, 10)
        self.work_desktop_spin.setValue(self.settings.work_desktop)

        self.break_desktop_spin = QSpinBox()
        self.break_desktop_spin.setRange(1, 10)
        self.break_desktop_spin.setValue(self.settings.break_desktop)

        hint = QLabel(
            "When the timer starts, Windows switches to the selected desktop.\n"
            "Put your work apps on the Work desktop and distractions on the Break desktop — "
            "the timer will swap between them automatically.\n"
            "The mini PiP window (Ctrl+P) floats above all desktops so you always see the timer."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {COLORS.get('text_sec', '#64748b')}; font-size: 11px;")

        df.addRow("Enable", self.switch_desktop_check)
        df.addRow("Work desktop #",  self.work_desktop_spin)
        df.addRow("Break desktop #", self.break_desktop_spin)
        df.addRow("", hint)
        desktop_group.setLayout(df)
        layout.addWidget(desktop_group)
        self._toggle_desktop_options(self.switch_desktop_check.checkState().value)

        note = QLabel("💡 Theme (dark/light) can be toggled from File → Switch to Dark/Light Mode.")
        note.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        note.setWordWrap(True)
        layout.addWidget(note)

        layout.addStretch()
        return page

    # ── Sounds tab ────────────────────────────────────────────────────────────

    def _build_sounds_tab(self) -> QWidget:
        page   = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        sounds_group = QGroupBox("Alarm Sounds")
        gl = QVBoxLayout(); gl.setSpacing(10)
        self.work_sound_edit     = self._build_sound_row(gl, "Work Time",   self.settings.alarm_sound_path)
        self.short_sound_edit    = self._build_sound_row(gl, "Short Break", self.settings.short_break_sound_path)
        self.long_sound_edit     = self._build_sound_row(gl, "Long Break",  self.settings.long_break_sound_path)
        self.downtime_sound_edit = self._build_sound_row(gl, "Downtime",    self.settings.downtime_sound_path)
        sounds_group.setLayout(gl)
        layout.addWidget(sounds_group)

        note = QLabel(
            "Supported formats: .mp3  .wav  .ogg\n"
            "Leave a field empty to use the built-in tick sound."
        )
        note.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        layout.addWidget(note)
        layout.addStretch()
        return page

    def _build_sound_row(self, container, label_text, value):
        row = QHBoxLayout()
        lbl = QLabel(label_text); lbl.setMinimumWidth(100)
        row.addWidget(lbl)
        edit = QLineEdit(); edit.setReadOnly(True)
        edit.setPlaceholderText("No sound file selected")
        if value:
            edit.setText(value)
        row.addWidget(edit, 1)
        browse = QPushButton("Browse"); browse.setObjectName("secondaryBtn")
        browse.clicked.connect(lambda: self._browse_sound_file(edit))
        clear = QPushButton("Clear"); clear.setObjectName("secondaryBtn")
        clear.clicked.connect(lambda: edit.clear())
        row.addWidget(browse); row.addWidget(clear)
        container.addLayout(row)
        return edit

    # ── Preset helpers ────────────────────────────────────────────────────────

    def _timer_values_from_form(self) -> dict:
        return {
            "work_time":                 self.work_min_spin.value()  * 60 + self.work_sec_spin.value(),
            "short_break":               self.short_min_spin.value() * 60 + self.short_sec_spin.value(),
            "long_break":                self.long_min_spin.value()  * 60 + self.long_sec_spin.value(),
            "downtime":                  self.down_min_spin.value()  * 60 + self.down_sec_spin.value(),
            "downtime_notify_threshold": max(1, self.notify_min_spin.value() * 60 + self.notify_sec_spin.value()),
        }

    def _apply_timer_values_to_form(self, payload: dict):
        s = self.settings
        def v(key, default): return int(payload.get(key, getattr(s, key, default)))
        wt = v("work_time", 1500);   self.work_min_spin.setValue(wt // 60);   self.work_sec_spin.setValue(wt % 60)
        sb = v("short_break", 300);  self.short_min_spin.setValue(sb // 60);  self.short_sec_spin.setValue(sb % 60)
        lb = v("long_break", 900);   self.long_min_spin.setValue(lb // 60);   self.long_sec_spin.setValue(lb % 60)
        dt = v("downtime", 0);       self.down_min_spin.setValue(dt // 60);   self.down_sec_spin.setValue(dt % 60)
        nt = v("downtime_notify_threshold", 300)
        self.notify_min_spin.setValue(nt // 60); self.notify_sec_spin.setValue(nt % 60)

    def _refresh_preset_controls(self):
        presets = sorted(self.presets_store.get("presets", {}).keys())
        for combo in (self.preset_combo, self.weekday_preset_combo, self.weekend_preset_combo):
            combo.clear(); combo.addItems(presets)
        wd = self.presets_store.get("weekday_preset", "Weekday")
        we = self.presets_store.get("weekend_preset", "Weekend")
        if wd in presets: self.weekday_preset_combo.setCurrentText(wd)
        if we in presets: self.weekend_preset_combo.setCurrentText(we)

    def _apply_selected_preset(self):
        name = self.preset_combo.currentText().strip()
        payload = self.presets_store.get("presets", {}).get(name)
        if not payload:
            return
        self._apply_timer_values_to_form(payload)
        self.statusBar_msg(f"Applied preset: {name}")

    def _save_as_new_preset(self):
        name, ok = QInputDialog.getText(self, "Save Preset", "Preset name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        presets = self.presets_store.setdefault("presets", {})
        if name in presets:
            QMessageBox.warning(self, "Preset Exists", "A preset with that name already exists.")
            return
        presets[name] = self._timer_values_from_form()
        self._save_presets_store(); self._refresh_preset_controls()
        self.preset_combo.setCurrentText(name)
        self.statusBar_msg(f"Saved preset: {name}")

    def _update_selected_preset(self):
        name = self.preset_combo.currentText().strip()
        if not name:
            return
        self.presets_store.setdefault("presets", {})[name] = self._timer_values_from_form()
        self._save_presets_store()
        self.statusBar_msg(f"Updated preset: {name}")

    def _delete_selected_preset(self):
        name = self.preset_combo.currentText().strip()
        if not name:
            return
        if name in ("Weekday", "Weekend"):
            QMessageBox.warning(self, "Protected Preset", "Default presets cannot be deleted.")
            return
        reply = QMessageBox.question(self, "Delete Preset", f"Delete preset '{name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.presets_store.get("presets", {}).pop(name, None)
        self._save_presets_store(); self._refresh_preset_controls()

    def statusBar_msg(self, msg: str):
        """Show a temporary status in a small QMessageBox (dialog has no status bar)."""
        QMessageBox.information(self, "Info", msg)

    def _toggle_desktop_options(self, state):
        enabled = (state == 2)
        self.work_desktop_spin.setEnabled(enabled)
        self.break_desktop_spin.setEnabled(enabled)

    def _browse_sound_file(self, line_edit):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Alarm Sound File", "",
            "Audio Files (*.mp3 *.wav *.ogg);;All Files (*)"
        )
        if path:
            line_edit.setText(path)

    # ── Save ─────────────────────────────────────────────────────────────────

    def save_settings(self):
        try:
            tv = self._timer_values_from_form()
            self.settings.work_time = tv["work_time"]
            self.settings.short_break = tv["short_break"]
            self.settings.long_break = tv["long_break"]
            self.settings.downtime = tv["downtime"]
            self.settings.downtime_notify_threshold = tv["downtime_notify_threshold"]
            self.settings.auto_start = self.auto_start_check.isChecked()
            self.settings.enable_downtime = self.enable_downtime_check.isChecked()
            self.settings.switch_desktop = self.switch_desktop_check.isChecked()
            self.settings.work_desktop = self.work_desktop_spin.value()
            self.settings.break_desktop = self.break_desktop_spin.value()
            self.settings.alarm_sound_path = self.work_sound_edit.text().strip()
            self.settings.short_break_sound_path = self.short_sound_edit.text().strip()
            self.settings.long_break_sound_path = self.long_sound_edit.text().strip()
            self.settings.downtime_sound_path = self.downtime_sound_edit.text().strip()

            if (self.settings.work_time == 0 and
                    self.settings.short_break == 0 and
                    self.settings.long_break == 0):
                QMessageBox.warning(
                    self, "Validation Error",
                    "At least one timer must have a duration greater than 0."
                )
                return

            self.presets_store["auto_apply"] = self.auto_apply_check.isChecked()
            self.presets_store["weekday_preset"] = self.weekday_preset_combo.currentText()
            self.presets_store["weekend_preset"] = self.weekend_preset_combo.currentText()
            self._save_presets_store()

            self.db.update_settings(self.settings.to_dict())
            self.db.update_super_focus_settings(
                enabled=self.super_focus_mode_check.isChecked(),
                duration_minutes=self.super_focus_duration_spin.value(),
            )
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save settings:\n{e}")

    def get_settings(self) -> Settings:
        return self.settings
