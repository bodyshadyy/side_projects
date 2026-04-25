"""
AI Assistant tab — powered by the Claude CLI (claude -p).

No API key needed: auth is handled by the installed Claude Code CLI.
Each message builds a full prompt (context + conversation history) and
runs `claude --output-format stream-json -p "..."` in a background thread,
streaming JSON chunks back to the chat UI as they arrive.
"""
import json
import shutil
import subprocess
from pathlib import Path

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QTextEdit, QScrollArea,
                              QFrame, QGraphicsDropShadowEffect, QSizePolicy,
                              QApplication)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor
from database import Database
from theme import COLORS


# ── Context builder (pulled from DB for every message) ────────────────────────

def _build_context(db: Database) -> str:
    from datetime import date, datetime
    today = date.today().isoformat()
    lines = [f"Today is {today}."]

    # Todos
    try:
        todos = [t for t in db.get_todos() if not t.get("completed")]
        if todos:
            lines.append("\nPending todos:")
            for t in todos[:10]:
                pri = {3: "High", 2: "Med", 1: "Low"}.get(t.get("priority", 1), "Low")
                lines.append(f"  [{pri}] {t['task']}")
    except Exception:
        pass

    # Schedule
    try:
        wake = db.get_wakeup_time(today)
        tasks = db.get_schedule_tasks()
        if tasks:
            lines.append("\nToday's schedule:")
            for t in tasks[:8]:
                time_info = t.get("fixed_time", "") or "flexible"
                lines.append(f"  {time_info} — {t['task']} ({t.get('duration_minutes', 30)} min)")
        if wake:
            lines.append(f"Wake-up time: {wake}")
    except Exception:
        pass

    # Sessions
    try:
        stats = db.get_sessions_for_date(today)
        work_done = sum(1 for s in stats if s.get("state") == "work")
        if work_done:
            lines.append(f"\nPomodoros completed today: {work_done}")
    except Exception:
        pass

    # Streak
    try:
        streak = db.get_streak_days()
        if streak:
            lines.append(f"Current streak: {streak} day(s)")
    except Exception:
        pass

    return "\n".join(lines)


# ── Quick prompts ─────────────────────────────────────────────────────────────

QUICK_PROMPTS = {
    "morning":    "Give me a motivating morning briefing based on my todos and schedule. What should I focus on today?",
    "plan":       "Generate a detailed hourly day plan for me based on my todos and schedule. Include time blocks.",
    "prioritize": "Looking at my pending todos, tell me the top 3 highest-impact tasks I should do today and why.",
    "reflect":    "Give me an end-of-day reflection based on my Pomodoros completed. What went well? What should I do tomorrow?",
    "routine":    "Based on my schedule and todos, suggest a sustainable daily routine template I can follow.",
}


# ── CLI worker ────────────────────────────────────────────────────────────────

class CLIWorker(QThread):
    """
    Runs `claude --output-format stream-json -p <prompt>` in a background thread.
    Parses stream-json chunks and emits text incrementally.
    Falls back to plain-text parsing if stream-json is unavailable.
    """

    chunk = pyqtSignal(str)
    done  = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, prompt: str):
        super().__init__()
        self._prompt = prompt
        self._cancel = False
        self._proc: subprocess.Popen | None = None

    def run(self) -> None:
        claude_cmd = self._find_claude()
        if not claude_cmd:
            self.error.emit(
                "Claude CLI not found in PATH.\n\n"
                "Install Claude Code: https://claude.ai/code\n"
                "Then restart the app."
            )
            return

        try:
            self._proc = subprocess.Popen(
                [claude_cmd, "--output-format", "stream-json", "-p", self._prompt],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            plain_fallback = []

            for raw_line in self._proc.stdout:
                if self._cancel:
                    self._proc.terminate()
                    break
                line = raw_line.strip()
                if not line:
                    continue

                text = self._parse_stream_line(line)
                if text is not None:
                    if text:
                        self.chunk.emit(text)
                else:
                    # Unrecognised line — accumulate as fallback plain text
                    plain_fallback.append(line)

            self._proc.wait()

            if plain_fallback and not self._cancel:
                # Emit any plain text that didn't parse as stream-json
                self.chunk.emit("\n".join(plain_fallback))

            rc = self._proc.returncode
            if rc not in (0, None) and not self._cancel:
                stderr = self._proc.stderr.read().strip()
                if stderr:
                    self.error.emit(stderr)
                    return

            if not self._cancel:
                self.done.emit()

        except Exception as exc:
            self.error.emit(str(exc))

    def cancel(self) -> None:
        self._cancel = True
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _find_claude() -> str | None:
        """Locate the claude binary in PATH and common install locations."""
        cmd = shutil.which("claude")
        if cmd:
            return cmd
        candidates = [
            Path.home() / ".claude" / "local" / "claude",
            Path.home() / "AppData" / "Roaming" / "npm" / "claude.cmd",
            Path.home() / "AppData" / "Roaming" / "npm" / "claude",
            Path("/usr/local/bin/claude"),
        ]
        for p in candidates:
            if p.exists():
                return str(p)
        return None

    @staticmethod
    def _parse_stream_line(line: str) -> str | None:
        """
        Parse one stream-json line.
        Returns the text string to emit, "" to skip silently, or None if not JSON.
        """
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            return None   # not JSON → caller handles as plain text

        kind = obj.get("type", "")

        if kind == "assistant":
            text_parts = []
            content = obj.get("message", {}).get("content", [])
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            return "".join(text_parts)

        if kind in ("system", "result", "user"):
            return ""   # skip silently

        return ""   # unknown type — skip


# ── Chat bubble ───────────────────────────────────────────────────────────────

def _shadow(blur=16, dy=3, alpha=20):
    fx = QGraphicsDropShadowEffect()
    fx.setBlurRadius(blur)
    fx.setXOffset(0)
    fx.setYOffset(dy)
    fx.setColor(QColor(0, 0, 0, alpha))
    return fx


class ChatBubble(QFrame):
    """A single message rendered as a rounded bubble."""

    def __init__(self, text: str, role: str, parent=None):
        super().__init__(parent)
        self.role = role
        self._full_text = text
        self._setup(text)

    def _setup(self, text: str) -> None:
        is_user = (self.role == "user")
        bg     = COLORS["accent"]      if is_user else COLORS["surface"]
        fg     = "white"               if is_user else COLORS["text"]
        border = COLORS["accent"]      if is_user else COLORS["border"]
        radius = "14px 14px 4px 14px" if is_user else "14px 14px 14px 4px"

        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: {radius};
            }}
        """)
        if not is_user:
            self.setGraphicsEffect(_shadow(blur=12, dy=2, alpha=15))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(0)

        self._label = QLabel(text)
        self._label.setWordWrap(True)
        self._label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self._label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        f = QFont()
        f.setPointSize(12)
        self._label.setFont(f)
        self._label.setStyleSheet(f"color: {fg}; background: transparent;")
        layout.addWidget(self._label)

    def append_text(self, chunk: str) -> None:
        self._full_text += chunk
        self._label.setText(self._full_text)


# ── Main widget ───────────────────────────────────────────────────────────────

class AIAssistantWidget(QWidget):
    """Claude-powered productivity assistant — uses the Claude CLI."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = Database()
        self._history: list[dict] = []   # {"role": "user"|"assistant", "content": str}
        self._worker: CLIWorker | None = None
        self._current_bubble: ChatBubble | None = None
        self._init_ui()
        QTimer.singleShot(400, self._welcome)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _init_ui(self) -> None:
        self.setStyleSheet(f"QWidget {{ background-color: {COLORS['bg']}; }}")
        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # Header
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        header.setGraphicsEffect(_shadow())
        hb = QVBoxLayout(header)
        hb.setContentsMargins(28, 18, 28, 14)
        hb.setSpacing(4)

        title_row = QHBoxLayout()
        title = QLabel("AI Assistant")
        tf = QFont(); tf.setPointSize(22); tf.setBold(True)
        title.setFont(tf)
        title.setStyleSheet(f"color: {COLORS['text']};")
        title_row.addWidget(title)
        title_row.addStretch()

        badge = QLabel("Claude CLI")
        badge.setStyleSheet(f"""
            background-color: {COLORS['accent_light']};
            color: {COLORS['accent']};
            border: 1px solid {COLORS['accent_border']};
            border-radius: 10px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: 700;
        """)
        title_row.addWidget(badge)
        hb.addLayout(title_row)

        subtitle = QLabel(
            "Powered by your local Claude CLI — no API key required. "
            "Your todos, schedule, and session data are included automatically."
        )
        subtitle.setStyleSheet(f"color: {COLORS['text_sec']}; font-size: 12px;")
        hb.addWidget(subtitle)
        root.addWidget(header)

        # Quick actions
        quick_bar = QFrame()
        quick_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface_alt']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        qb = QHBoxLayout(quick_bar)
        qb.setContentsMargins(20, 10, 20, 10)
        qb.setSpacing(8)

        for label, key in [
            ("☀️  Morning Briefing",  "morning"),
            ("📋  Generate Day Plan", "plan"),
            ("🎯  Prioritize Tasks",  "prioritize"),
            ("🌙  Daily Reflection",  "reflect"),
            ("🔁  Build My Routine",  "routine"),
        ]:
            btn = QPushButton(label)
            btn.setMinimumHeight(34)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['surface']};
                    color: {COLORS['text']};
                    border: 1.5px solid {COLORS['border']};
                    border-radius: 17px;
                    padding: 0 14px;
                    font-size: 12px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['accent_light']};
                    border-color: {COLORS['accent_border']};
                    color: {COLORS['accent']};
                }}
                QPushButton:pressed {{
                    background-color: {COLORS['accent']};
                    color: white;
                }}
                QPushButton:disabled {{
                    color: {COLORS['text_muted']};
                    border-color: {COLORS['border']};
                }}
            """)
            btn.clicked.connect(lambda checked, k=key: self._send_quick(k))
            qb.addWidget(btn)

        qb.addStretch()

        clear_btn = QPushButton("Clear Chat")
        clear_btn.setMinimumHeight(34)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text_muted']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                padding: 0 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['danger']};
                color: white;
                border-color: {COLORS['danger']};
            }}
        """)
        clear_btn.clicked.connect(self._clear_chat)
        qb.addWidget(clear_btn)
        root.addWidget(quick_bar)

        # Scroll area for chat bubbles
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("border: none;")

        self._bubble_container = QWidget()
        self._bubble_container.setStyleSheet(f"background-color: {COLORS['bg']};")
        self._bubble_layout = QVBoxLayout(self._bubble_container)
        self._bubble_layout.setSpacing(10)
        self._bubble_layout.setContentsMargins(24, 16, 24, 16)
        self._bubble_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._bubble_layout.addStretch()

        self._scroll.setWidget(self._bubble_container)
        root.addWidget(self._scroll, 1)

        # Input area
        input_frame = QFrame()
        input_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-top: 1px solid {COLORS['border']};
            }}
        """)
        input_frame.setGraphicsEffect(_shadow(blur=12, dy=-2, alpha=15))
        il = QHBoxLayout(input_frame)
        il.setContentsMargins(16, 12, 16, 12)
        il.setSpacing(10)

        self._input = QTextEdit()
        self._input.setPlaceholderText(
            "Ask about your schedule, priorities, or productivity…  "
            "(Enter to send, Shift+Enter for newline)"
        )
        self._input.setFixedHeight(56)
        self._input.setStyleSheet(f"""
            QTextEdit {{
                border: 1.5px solid {COLORS['border']};
                border-radius: 10px;
                padding: 8px 12px;
                font-size: 13px;
                background-color: {COLORS['input_bg']};
                color: {COLORS['text']};
            }}
            QTextEdit:focus {{
                border-color: {COLORS['accent']};
                background-color: {COLORS['surface']};
            }}
        """)
        self._input.installEventFilter(self)
        il.addWidget(self._input, 1)

        self._send_btn = QPushButton("Send")
        self._send_btn.setFixedSize(80, 40)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white; border: none;
                border-radius: 8px; font-weight: 700; font-size: 13px;
            }}
            QPushButton:hover {{ background-color: {COLORS['accent_hover']}; }}
            QPushButton:disabled {{
                background-color: {COLORS['border']};
                color: {COLORS['text_muted']};
            }}
        """)
        self._send_btn.clicked.connect(self._send_user_message)
        il.addWidget(self._send_btn)

        self._stop_btn = QPushButton("Stop")
        self._stop_btn.setFixedSize(70, 40)
        self._stop_btn.setVisible(False)
        self._stop_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white; border: none;
                border-radius: 8px; font-weight: 600; font-size: 13px;
            }}
            QPushButton:hover {{ background-color: #dc2626; }}
        """)
        self._stop_btn.clicked.connect(self._stop)
        il.addWidget(self._stop_btn)

        root.addWidget(input_frame)

    def _welcome(self) -> None:
        self._add_assistant_bubble(
            "Hi! I'm your Claude-powered productivity coach.\n\n"
            "I can see your todos, schedule, and Pomodoro history — no API key needed, "
            "I run through your local Claude CLI.\n\n"
            "Try a quick action above or ask me anything about your day!"
        )

    # ── Event filter (Enter to send) ──────────────────────────────────────────

    def eventFilter(self, obj, event):
        from PyQt6.QtCore import QEvent
        if obj is self._input and event.type() == QEvent.Type.KeyPress:
            if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                if not (event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
                    self._send_user_message()
                    return True
        return super().eventFilter(obj, event)

    # ── Sending ───────────────────────────────────────────────────────────────

    def _send_quick(self, key: str) -> None:
        prompt = QUICK_PROMPTS.get(key, "")
        if prompt:
            self._send(prompt)

    def _send_user_message(self) -> None:
        text = self._input.toPlainText().strip()
        if not text:
            return
        self._input.clear()
        self._send(text)

    def _send(self, user_text: str) -> None:
        if self._worker and self._worker.isRunning():
            return

        self._add_user_bubble(user_text)
        self._history.append({"role": "user", "content": user_text})

        full_prompt = self._build_prompt(user_text)

        self._current_bubble = self._add_assistant_bubble("", streaming=True)
        self._set_busy(True)

        self._worker = CLIWorker(full_prompt)
        self._worker.chunk.connect(self._on_chunk)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _build_prompt(self, latest: str) -> str:
        """Assemble the full prompt: system context + history + latest message."""
        ctx = _build_context(self.db)

        parts = [
            "You are a productivity coach assistant. Be helpful, concise, and actionable.",
            "",
            "Current context about the user:",
            ctx,
        ]

        if len(self._history) > 1:
            parts.append("\nConversation so far:")
            for msg in self._history[:-1]:   # exclude the latest we just appended
                role = "User" if msg["role"] == "user" else "Assistant"
                parts.append(f"{role}: {msg['content']}")

        parts.append(f"\nUser: {latest}")
        parts.append("\nAssistant:")
        return "\n".join(parts)

    # ── Streaming callbacks ───────────────────────────────────────────────────

    def _on_chunk(self, text: str) -> None:
        if self._current_bubble:
            self._current_bubble.append_text(text)
            self._scroll_to_bottom()

    def _on_done(self) -> None:
        if self._current_bubble:
            self._history.append({
                "role": "assistant",
                "content": self._current_bubble._full_text,
            })
        self._current_bubble = None
        self._set_busy(False)

    def _on_error(self, msg: str) -> None:
        self._current_bubble = None
        self._add_assistant_bubble(f"Error running Claude CLI:\n\n{msg}")
        self._set_busy(False)

    def _stop(self) -> None:
        if self._worker:
            self._worker.cancel()

    # ── Bubble helpers ────────────────────────────────────────────────────────

    def _add_user_bubble(self, text: str) -> ChatBubble:
        bubble = ChatBubble(text, "user")
        row = QHBoxLayout()
        row.addStretch()
        row.addWidget(bubble)
        self._bubble_layout.insertLayout(self._bubble_layout.count() - 1, row)
        self._scroll_to_bottom()
        return bubble

    def _add_assistant_bubble(self, text: str, streaming: bool = False) -> ChatBubble:
        bubble = ChatBubble("●" if streaming else text, "assistant")
        bubble.setMaximumWidth(680)
        if streaming:
            bubble._full_text = ""
        row = QHBoxLayout()
        row.addWidget(bubble)
        row.addStretch()
        self._bubble_layout.insertLayout(self._bubble_layout.count() - 1, row)
        self._scroll_to_bottom()
        return bubble

    def _scroll_to_bottom(self) -> None:
        QTimer.singleShot(30, lambda: (
            self._scroll.verticalScrollBar().setValue(
                self._scroll.verticalScrollBar().maximum()
            ) if hasattr(self, "_scroll") else None
        ))

    def _set_busy(self, busy: bool) -> None:
        self._send_btn.setVisible(not busy)
        self._stop_btn.setVisible(busy)
        self._input.setReadOnly(busy)

    def _clear_chat(self) -> None:
        self._history.clear()
        while self._bubble_layout.count() > 1:
            item = self._bubble_layout.takeAt(0)
            if item.layout():
                while item.layout().count():
                    w = item.layout().takeAt(0).widget()
                    if w:
                        w.deleteLater()
            elif item.widget():
                item.widget().deleteLater()
