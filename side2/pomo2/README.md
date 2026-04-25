# Pomodoro Timer — Full-Stack Productivity App

A polished, feature-rich desktop Pomodoro timer built with **PyQt6** and powered by **Claude AI**.  It combines focused work sessions with a complete personal productivity suite — todos, daily scheduling, task prioritization, session statistics, and an AI assistant that knows your whole day.

---

## Features at a glance

| Tab | What it does |
|-----|-------------|
| ⏱ **Timer** | Circular progress ring, session dots, keyboard shortcuts, downtime tracker, tick sound countdown |
| 📝 **Notes** | One note per calendar day, auto-saved as you type (1.5 s debounce) |
| ✅ **Todos** | Card-based task list with priorities, due dates, overdue highlighting, and daily/weekly/monthly recurrence |
| 🎯 **Eisenhower** | Classic 2×2 urgency–importance matrix for strategic task sorting |
| 📅 **Schedule** | Daily timeline that auto-sequences relative tasks around fixed events; Google Calendar / `.ics` export |
| 📊 **Statistics** | 7-day bar chart, today's focus time, all-time totals, consecutive-day streak |
| 🤖 **Claude AI** | Streaming chat with Claude; context includes your todos, schedule, and session history |
| 🔒 **Super Focus** | Full-screen deep-work countdown that locks all other tabs |

---

## Quick start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) Set your Anthropic API key for the AI tab
export ANTHROPIC_API_KEY="sk-ant-..."

# 3. Launch
python main.py
```

> **Windows shortcut** — run `create_shortcut.py` once to place a `.lnk` in your Start Menu.

---

## Keyboard shortcuts

| Key | Action |
|-----|--------|
| `Space` | Start / Pause timer |
| `R` | Reset current phase |
| `S` | Skip to next phase |
| `M` | Toggle mute |
| `Ctrl+1` … `Ctrl+8` | Switch tabs |
| `Ctrl+,` | Open Settings |
| `Ctrl+Q` | Quit |
| `Ctrl+S` | Save note immediately (Notes tab) |
| `Enter` | Send message (AI tab) |
| `Shift+Enter` | New line in AI input |
| `Ctrl+/` | Show keyboard shortcuts help |

---

## Claude AI integration

The **🤖 Claude AI** tab gives you an always-on productivity coach that has full context about your day:

### What Claude knows
Every message automatically includes:
- Today's date and your wake-up time (if set in Schedule)
- All pending todos with priorities and due dates
- Your scheduled tasks for the day
- Number of Pomodoros completed and total focus time today
- Your current streak
- Today's note (first 300 characters)

### Quick actions
| Button | What it sends |
|--------|--------------|
| ☀️ Morning Briefing | Motivating summary of today's priorities |
| 📋 Generate Day Plan | Timed hourly plan based on your todos and schedule |
| 🎯 Prioritize Tasks | Top 3 highest-impact tasks with reasoning |
| 🌙 Daily Reflection | End-of-day review with tomorrow's suggestion |
| 🔁 Build My Routine | Sustainable daily routine template |

### Setup
**Option A — Environment variable (recommended)**
```bash
export ANTHROPIC_API_KEY="sk-ant-api03-..."   # add to ~/.bashrc or system env
```

**Option B — In-app setup**
Launch the app → click the **🤖 Claude AI** tab → enter your key in the setup panel.
The key is saved to `data/ai_config.json` (local only, never synced).

### Prompt caching
The system prompt is marked `"cache_control": "ephemeral"` so Anthropic caches it after the first call.  Subsequent messages in a session cost ~90% less for the input tokens.

---

## Timer phases

```
Work → Short Break → Work → Short Break → Work → Short Break → Work → Long Break
       (every 4th work session triggers a long break)
```

| Phase | Default |
|-------|---------|
| Work | 25 min |
| Short break | 5 min |
| Long break | 15 min |

All durations are configurable in **Settings → Timer & Presets**.

### Downtime tracking
When a session ends and auto-start is off, the app tracks "downtime" (idle time between sessions).  If downtime exceeds the configured threshold an alert fires so you stay accountable.

---

## Presets

Create named timer presets (e.g. "Deep Work 50/10", "Light Day 20/5") and optionally auto-apply different presets on weekdays vs. weekends.

---

## Daily Schedule

1. Press **☀️ I'm Awake!** to record your wake-up time.
2. Add tasks — choose **Auto Sequence** (duration-based, flows from wake time) or **Fixed Time** (anchored to a clock time).
3. Fixed-time tasks take priority; relative tasks are pushed forward to avoid overlaps automatically.
4. Optional **🌙 Bedtime routine** injects a wind-down block and sleep entry at the end of your day.
5. Export to **Google Calendar** (requires OAuth setup) or download an **`.ics`** file.

### Google Calendar setup
1. Enable the **Google Calendar API** in Google Cloud Console.
2. Create OAuth 2.0 credentials for a Desktop app.
3. Download the JSON file and save it as `data/google_client_secret.json`.
4. Click **📅 Google Calendar** — a browser window opens for one-time auth.

---

## Dark mode

Toggle via **File → Switch to Dark / Light Mode**.  The preference is saved; the new theme applies on next launch.

---

## Statistics

The **📊 Stats** tab reads from the `session_history` table which is updated automatically every time a Pomodoro completes.  No manual action required.

- **Today** — sessions and focus time for the current calendar day.
- **7-day chart** — bar chart of work sessions per day; today's bar is highlighted.
- **All time** — lifetime totals and active-day count.
- **Streak** — consecutive calendar days with at least one completed work session.

---

## Data storage

Everything is stored locally in **`data/pomodoro.db`** (SQLite).  No cloud sync, no account required.

| Table | Contents |
|-------|----------|
| `settings` | Timer durations, sounds, behavior flags |
| `notes` | One note row per calendar date |
| `todos` | Task list with priority, recurrence |
| `eisenhower_tasks` | Matrix tasks by quadrant |
| `schedule_tasks` | Daily schedule task templates |
| `schedule_wakeup` | Wake-up time per date |
| `session_history` | Every completed Pomodoro phase (used by Stats) |
| `super_focus_settings` | Super Focus duration and enabled flag |

Backups: just copy the `data/` folder.

---

## Configuration files

| File | Purpose |
|------|---------|
| `data/timer_presets.json` | Named presets + weekday/weekend auto-apply |
| `data/schedule_options.json` | Bedtime routine toggle and awake-hours setting |
| `data/ai_config.json` | Anthropic API key (if entered in-app) |
| `data/theme_pref.json` | Dark/light mode preference |
| `data/google_client_secret.json` | Google OAuth credentials (user-provided) |
| `data/google_token.json` | Cached Google OAuth token |
| `data/google_calendar_config.json` | Target calendar ID |

---

## Project structure

```
pomo2/
├── main.py                 Entry point — applies theme, builds QApplication
├── pomodoro_app.py         Main window, tab container, menu bar
├── theme.py                Design system — COLORS, dark/light palette, app stylesheet
├── models.py               Dataclasses: Settings, Todo, ScheduleTask, Note
├── database.py             SQLite singleton — all DB operations
│
├── timer_window.py         ⏱ Pomodoro timer widget
├── calendar_notes.py       📝 Daily notes with auto-save
├── todo_list.py            ✅ Todo cards with priority and recurrence
├── eisenhower_matrix.py    🎯 2×2 priority matrix
├── daily_schedule.py       📅 Timeline + Google Calendar export
├── stats.py                📊 Statistics with painted bar chart
├── ai_assistant.py         🤖 Claude streaming chat UI
├── super_focus.py          🔒 Deep-focus mode with tab lock
│
├── claude_ai.py            Claude API wrapper with prompt caching
├── settings_dialog.py      Settings dialog (timer, behavior, sounds)
│
├── requirements.txt
├── create_shortcut.py      Windows Start Menu shortcut helper
└── data/                   Runtime data (SQLite DB + JSON config)
```

---

## Requirements

- Python 3.11+
- PyQt6 >= 6.10.2
- anthropic >= 0.40.0 (for AI tab)
- `google-api-python-client`, `google-auth-httplib2`, `google-auth-oauthlib` (for Google Calendar export — optional)

```bash
pip install -r requirements.txt
```
