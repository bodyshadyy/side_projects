# Building Pomodoro Timer as a Windows App

This guide explains how to build and run the Pomodoro Timer as a Windows desktop application using Electron.

## Prerequisites

- Node.js 16+ and npm installed
- Windows 10/11

## Setup

1. **Install dependencies:**

```bash
cd frontend
npm install
```

This will install:
- Vue.js and Vite (for the frontend)
- Electron (for desktop app)
- electron-builder (for packaging)

## Development

### Run in Development Mode

```bash
npm run electron:dev
```

This will:
1. Start the Vite dev server
2. Launch Electron with hot-reload
3. Open the app window

### Build for Production

```bash
npm run build:electron
```

This builds the frontend for Electron.

## Creating Windows Installer

### Build Windows Installer

```bash
npm run electron:dist
```

This will:
1. Build the frontend
2. Package the Electron app
3. Create a Windows installer (NSIS) in `dist-electron/`

The installer will be named something like:
- `Pomodoro Timer Setup 1.0.0.exe`

### Installer Features

- One-click installation (optional)
- Custom installation directory
- Desktop shortcut
- Start menu shortcut
- Uninstaller

## Project Structure

```
.
├── electron/
│   ├── main.js          # Electron main process
│   └── preload.js       # Preload script (bridge)
├── frontend/
│   ├── src/
│   │   ├── utils/
│   │   │   ├── chrome-api.js    # Chrome extension API
│   │   │   └── electron-api.js  # Electron API wrapper
│   │   └── ...
│   └── ...
└── package.json
```

## How It Works

1. **Electron Main Process** (`electron/main.js`):
   - Manages the application window
   - Handles timer logic (replaces background.js)
   - Manages data storage (JSON file)
   - Handles notifications

2. **Preload Script** (`electron/preload.js`):
   - Bridges Electron APIs to the renderer process
   - Exposes safe APIs to the frontend

3. **Frontend**:
   - Detects if running in Electron or Chrome extension
   - Uses appropriate API wrapper
   - Same Vue.js components work in both modes

## Data Storage

In Electron mode, data is stored in:
```
%APPDATA%/Pomodoro Timer/pomodoro-data.json
```

This includes:
- Timer state
- Settings
- Down time tracking

## Building for Distribution

### Create Installer

```bash
npm run electron:dist
```

The installer will be in `frontend/dist-electron/`

### Customize Installer

Edit `package.json` under the `build` section to customize:
- App ID
- Product name
- Icon
- Installer options

## Troubleshooting

### App won't start
- Make sure all dependencies are installed: `npm install`
- Check Node.js version: `node --version` (should be 16+)

### Build fails
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Check that Vite build completes successfully first

### Icons not showing
- Make sure `frontend/dist/icon128.png` exists
- Rebuild the frontend: `npm run build:electron`

## Notes

- The app works both as a Chrome extension and Windows app
- Same codebase, different entry points
- Electron version uses file-based storage instead of Chrome storage
- Notifications use Electron's native notifications

