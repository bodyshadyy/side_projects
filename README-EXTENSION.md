# Pomodoro Timer Chrome Extension

This is a Chrome extension version of the Pomodoro Timer app.

## Building the Extension

1. Install dependencies:
```bash
cd frontend
npm install
```

2. Build the extension:
```bash
npm run build
```

This will:
- Build the Vue.js app using Vite
- Copy necessary extension files (manifest.json, background.js) to the dist folder
- Prepare the extension for loading

## Loading the Extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in the top right)
3. Click "Load unpacked"
4. Select the `dist` folder from this project

## Adding Icons

You need to add icon files to the `dist` folder:
- `icon16.png` (16x16 pixels)
- `icon48.png` (48x48 pixels)
- `icon128.png` (128x128 pixels)

You can create these icons or use an online tool to generate them from a single image.

## Features

- **Pomodoro Timer**: Work sessions, short breaks, and long breaks
- **Todo List**: Manage your tasks
- **Notes**: Calendar-based note taking
- **Settings**: Customize timer durations and behavior
- **Notifications**: Chrome notifications when timer completes
- **Background Operation**: Timer continues running even when popup is closed

## Development

For development with hot reload:
```bash
npm run dev
```

Note: The extension needs to be rebuilt and reloaded in Chrome for changes to take effect.

## Architecture

- **Background Service Worker** (`background.js`): Manages timer state and notifications
- **Popup** (`popup.html`): Main UI interface
- **Chrome Storage API**: Stores timer state and settings
- **Chrome Messaging API**: Communication between popup and background

## Differences from Web Version

- No Flask backend needed - timer logic runs in background service worker
- Uses Chrome Storage API instead of HTTP API
- Uses Chrome Notifications API for system notifications
- Popup-based UI instead of full-page web app
- Timer continues running in background when popup is closed





