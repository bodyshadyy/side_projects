# Pomodoro Timer App 🍅

A beautiful Pomodoro timer application with a Vue.js frontend and Flask backend. Perfect for managing your work sessions and breaks!

## Features

- ⏱️ **Timer Functionality**: Start, pause, and skip timers
- 🎨 **Beautiful UI**: Modern, responsive design with a circular progress indicator
- ⚙️ **Customizable Settings**: 
  - Adjust work duration (default: 25 minutes)
  - Customize short break duration (default: 5 minutes)
  - Set long break duration (default: 15 minutes)
  - Configure how many short breaks before a long break (default: 4)
- 🔔 **Sound Notifications**: Plays a beep sound when the timer completes or switches modes
- 📊 **Progress Tracking**: Visual progress ring and completed Pomodoros counter

## Tech Stack

- **Frontend**: Vue.js 3, Vite, Axios
- **Backend**: Python, Flask, Flask-CORS
- **Real-time Updates**: Polling-based state synchronization

## Setup Instructions

### Prerequisites

- Python 3.7+ installed
- Node.js 16+ and npm installed

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment (recommended):
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the Flask server:
```bash
python app.py
```

The backend will start on `http://localhost:5000`

### Frontend Setup

1. Open a new terminal and navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend will start on `http://localhost:3000`

## Usage

1. **Start the Timer**: Click the "Start" button to begin your Pomodoro session
2. **Pause**: Click "Pause" to temporarily stop the timer
3. **Resume**: Click "Resume" to continue from where you paused
4. **Skip**: Click "Skip" to move to the next phase (work → break or break → work)
5. **Reset**: Click "Reset" to stop the timer and return to the initial state
6. **Customize Settings**: Click "Show Settings" to adjust:
   - Work duration
   - Short break duration
   - Long break duration
   - Number of short breaks before a long break

## How It Works

- The app follows the classic Pomodoro Technique:
  1. Work for the set duration (default: 25 minutes)
  2. Take a short break (default: 5 minutes)
  3. After completing a set number of work sessions (default: 4), take a long break (default: 15 minutes)
  4. Repeat

- The timer automatically switches between work and break modes
- A sound notification plays when:
  - A timer completes
  - The mode switches (work to break or vice versa)
  - You skip a timer

## Project Structure

```
.
├── backend/
│   ├── app.py              # Flask application with timer logic
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── TimerDisplay.vue   # Timer visualization component
│   │   │   └── SettingsPanel.vue  # Settings configuration component
│   │   ├── App.vue               # Main application component
│   │   ├── main.js              # Vue app entry point
│   │   └── style.css            # Global styles
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## API Endpoints

- `GET /api/timer/state` - Get current timer state
- `POST /api/timer/start` - Start the timer
- `POST /api/timer/pause` - Pause the timer
- `POST /api/timer/skip` - Skip to next mode
- `POST /api/timer/reset` - Reset the timer
- `GET /api/settings` - Get current settings
- `POST /api/settings` - Update settings

## Development

To build for production:
```bash
cd frontend
npm run build
```

The built files will be in `frontend/dist/`

## License

MIT

## Contributing

Feel free to submit issues and enhancement requests!

