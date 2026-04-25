"""
Claude AI integration for Pomodoro app.

Wraps the Anthropic SDK to provide context-aware productivity coaching.
Uses prompt caching on the (stable) system prompt to minimize costs.

API key resolution order:
  1. ANTHROPIC_API_KEY environment variable
  2. data/ai_config.json  →  {"api_key": "sk-ant-..."}
"""
import os
import json
from pathlib import Path
from typing import Generator, Optional

try:
    import anthropic
    _SDK_AVAILABLE = True
except ImportError:
    _SDK_AVAILABLE = False


# The system prompt is sent with every request but cached on Anthropic's side
# after the first call, so subsequent calls are much cheaper.
_SYSTEM_PROMPT = """\
You are a personal productivity coach embedded inside a Pomodoro Timer desktop app.
You have real-time access to the user's:
  • Pending and completed todos (with priorities and due dates)
  • Daily schedule (fixed-time and auto-sequenced tasks)
  • Pomodoro session history (focus time, completed sessions, day streak)
  • Daily notes

Your role:
  1. Help users plan an effective day given their tasks and energy.
  2. Give concrete, actionable advice — not vague platitudes.
  3. Be encouraging but realistic about what can actually be done in one day.
  4. When asked to generate a schedule, output it in a clean, readable format.
  5. Be concise: most responses should be under 250 words unless a detailed plan is requested.

Tone: professional, warm, direct.  Think of yourself as a knowledgeable friend who cares about the user getting things done without burning out.\
"""


def _config_path() -> Path:
    d = Path(__file__).parent / "data"
    d.mkdir(exist_ok=True)
    return d / "ai_config.json"


def _load_api_key() -> Optional[str]:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return key
    p = _config_path()
    if p.exists():
        try:
            return json.loads(p.read_text()).get("api_key", "").strip() or None
        except Exception:
            pass
    return None


def save_api_key(key: str) -> None:
    _config_path().write_text(json.dumps({"api_key": key.strip()}, indent=2))


def sdk_available() -> bool:
    return _SDK_AVAILABLE


class ClaudeIntegration:
    """Thin wrapper around the Anthropic Messages API with caching."""

    MODEL = "claude-sonnet-4-6"

    def __init__(self):
        self._client: Optional["anthropic.Anthropic"] = None
        key = _load_api_key()
        if key and _SDK_AVAILABLE:
            self._client = anthropic.Anthropic(api_key=key)

    def is_configured(self) -> bool:
        return self._client is not None

    def reinit(self, key: str) -> None:
        """Re-initialise with a new API key (called after user enters it)."""
        if _SDK_AVAILABLE:
            self._client = anthropic.Anthropic(api_key=key.strip())

    # ── Context builder ───────────────────────────────────────────────────────

    @staticmethod
    def build_context(db) -> str:
        """Pull live data from the database and format it for the prompt."""
        from datetime import date as _date, timedelta
        from models import ScheduleTask

        today = _date.today()
        today_str = today.strftime("%Y-%m-%d")
        lines = [f"Today's date: {today.strftime('%A, %B %d, %Y')}"]

        # Wake-up time
        wake = db.get_wakeup_time(today_str)
        if wake:
            lines.append(f"Wake-up time today: {wake}")

        # Pending todos
        todos = db.get_todos()
        pending = [t for t in todos if not t.get("completed")]
        if pending:
            pri_map = {1: "Low", 2: "Medium", 3: "High"}
            lines.append(f"\nPending tasks ({len(pending)}):")
            for t in pending[:15]:
                label = pri_map.get(t.get("priority", 1), "Low")
                lines.append(f"  [{label}] {t['task']} — due {t.get('date') or 'anytime'}")

        # Scheduled tasks
        raw_tasks = db.get_schedule_tasks()
        if raw_tasks:
            lines.append(f"\nSchedule tasks ({len(raw_tasks)}):")
            for t in raw_tasks[:12]:
                if t.get("is_fixed_time"):
                    lines.append(
                        f"  {t['task']}  ({t.get('fixed_time', '?')} – {t.get('fixed_time_end', '?')})"
                    )
                else:
                    lines.append(f"  {t['task']}  ({t.get('duration_minutes', 30)} min)")

        # Today's session stats
        sessions_today = db.get_sessions_for_date(today_str)
        work_today = [s for s in sessions_today if s["state"] == "work"]
        if work_today:
            total_min = sum(s["duration_seconds"] for s in work_today) // 60
            lines.append(
                f"\nPomodoros completed today: {len(work_today)}  ({total_min} min of focus)"
            )
        else:
            lines.append("\nPomodoros completed today: 0")

        streak = db.get_streak_days()
        if streak:
            lines.append(f"Current streak: {streak} day{'s' if streak != 1 else ''}")

        # Today's note (first 300 chars)
        note = db.get_note(today_str)
        if note and note.strip():
            lines.append(f"\nToday's note (excerpt): {note[:300].strip()}")

        return "\n".join(lines)

    # ── Streaming API call ────────────────────────────────────────────────────

    def stream(self, messages: list, context: str = "") -> Generator[str, None, None]:
        """Yield text chunks from Claude.  *messages* follow the Anthropic API format."""
        if not self._client:
            raise RuntimeError("Claude API key not configured.")

        system = [
            {
                "type": "text",
                "text": _SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},   # cache stable system prompt
            }
        ]
        if context:
            system.append({"type": "text", "text": context})

        with self._client.messages.stream(
            model=self.MODEL,
            max_tokens=1024,
            system=system,
            messages=messages,
        ) as stream:
            for text in stream.text_stream:
                yield text

    # ── Canned prompts ────────────────────────────────────────────────────────

    QUICK_PROMPTS = {
        "morning": (
            "Good morning! Give me a focused, motivating morning briefing based on my tasks "
            "and schedule today. Highlight the 2-3 most important things to accomplish. "
            "Keep it under 150 words."
        ),
        "plan": (
            "Generate a realistic hourly plan for the rest of my day. "
            "Use my scheduled tasks and pending todos as input. "
            "Format each block exactly as:\n"
            "  HH:MM – HH:MM  |  Task  |  One-line note\n"
            "Include Pomodoro work blocks and short breaks. "
            "Be realistic — don't overfill the day."
        ),
        "prioritize": (
            "Look at my pending todos and tell me the top 3 highest-impact tasks I should "
            "focus on today and exactly why. Be direct. Under 120 words."
        ),
        "reflect": (
            "Give me an honest, constructive end-of-day reflection based on my Pomodoro "
            "sessions today and my todo list. What went well? What can I improve tomorrow? "
            "Close with one concrete suggestion for tomorrow. Under 150 words."
        ),
        "routine": (
            "Design a sustainable daily routine template for me based on my typical tasks "
            "and schedule. Include morning rituals, deep work blocks, breaks, and an "
            "evening wind-down. Output it as a timed schedule I can follow each day."
        ),
    }
