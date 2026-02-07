const { app, BrowserWindow, ipcMain, Notification } = require('electron')
const path = require('path')
const fs = require('fs').promises

// Default timer state
const defaultTimerState = {
  is_running: false,
  is_paused: false,
  current_mode: 'work',
  remaining_seconds: 25 * 60,
  completed_pomodoros: 0
}

// Default settings
const defaultSettings = {
  work_duration: 25 * 60,
  short_break: 5 * 60,
  long_break: 15 * 60,
  short_breaks_until_long: 4,
  auto_switch: false,
  max_down_time: 15 * 60,
  max_downtime_reminders: 0,
  work_sound: null,
  work_sound_file_name: '',
  break_sound: null,
  break_sound_file_name: ''
}

// Storage file path
const storagePath = path.join(app.getPath('userData'), 'pomodoro-data.json')

// Current state
let timerState = { ...defaultTimerState }
let settings = { ...defaultSettings }
let downTime = 0
let downTimeStartTime = null
let downTimeInterval = null
let lastNotifiedMultiple = 0
let timerInterval = null

// Load data from file
async function loadData() {
  try {
    const data = await fs.readFile(storagePath, 'utf-8')
    const parsed = JSON.parse(data)
    timerState = { ...defaultTimerState, ...parsed.timerState }
    settings = { ...defaultSettings, ...parsed.settings }
    downTime = parsed.downTime || 0
    downTimeStartTime = parsed.downTimeStartTime || null
  } catch (err) {
    // File doesn't exist or is invalid, use defaults
    await saveData()
  }
}

// Save data to file
async function saveData() {
  try {
    const data = {
      timerState,
      settings,
      downTime,
      downTimeStartTime
    }
    await fs.writeFile(storagePath, JSON.stringify(data, null, 2))
  } catch (err) {
    console.error('Error saving data:', err)
  }
}

// Merge settings with defaults
function mergeSettingsWithDefaults(newSettings) {
  const merged = { ...defaultSettings }
  if (newSettings) {
    Object.keys(defaultSettings).forEach(key => {
      if (newSettings[key] !== undefined) {
        if (key.includes('duration') || key.includes('break') || key.includes('time')) {
          merged[key] = Math.max(1, parseInt(newSettings[key]) || defaultSettings[key])
        } else if (key.includes('until') || key.includes('reminders')) {
          merged[key] = Math.max(0, parseInt(newSettings[key]) || defaultSettings[key])
        } else if (key === 'auto_switch') {
          merged[key] = Boolean(newSettings[key])
        } else {
          merged[key] = newSettings[key] !== null ? newSettings[key] : defaultSettings[key]
        }
      }
    })
  }
  return merged
}

// Create window
let mainWindow = null

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, '../dist/icon48.png')
  })

  // Load the app
  if (app.isPackaged) {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  } else {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

// Timer update function
function startTimerUpdate() {
  if (timerInterval) {
    clearInterval(timerInterval)
  }

  timerInterval = setInterval(async () => {
    if (timerState.is_running && !timerState.is_paused) {
      if (timerState.remaining_seconds > 0) {
        timerState.remaining_seconds -= 1
        await saveData()
        
        // Notify renderer
        if (mainWindow) {
          mainWindow.webContents.send('timer-update', { timerState, downTime: await getCurrentDownTime() })
        }
      } else {
        // Timer completed
        timerState.is_running = false
        const previousMode = timerState.current_mode

        // Switch to next mode
        if (timerState.current_mode === 'work') {
          timerState.completed_pomodoros += 1
          if (timerState.completed_pomodoros % settings.short_breaks_until_long === 0) {
            timerState.current_mode = 'long_break'
            timerState.remaining_seconds = settings.long_break
          } else {
            timerState.current_mode = 'short_break'
            timerState.remaining_seconds = settings.short_break
          }
        } else if (timerState.current_mode === 'short_break') {
          timerState.current_mode = 'work'
          timerState.remaining_seconds = settings.work_duration
        } else if (timerState.current_mode === 'long_break') {
          timerState.current_mode = 'work'
          timerState.remaining_seconds = settings.work_duration
        }

        await saveData()
        await startDownTimeTracking()

        // Show notification
        showNotification(previousMode, timerState.current_mode, timerState.completed_pomodoros)

        // Play sound
        playAudioNotification(previousMode)

        // Notify renderer
        if (mainWindow) {
          mainWindow.webContents.send('timer-complete', {
            timerState,
            previousMode,
            downTime: await getCurrentDownTime()
          })
        }

        // Auto-switch
        if (settings.auto_switch) {
          timerState.is_running = true
          await saveData()
        }
      }
    }
  }, 1000)
}

// Down time tracking
async function getCurrentDownTime() {
  if (downTimeStartTime) {
    const elapsed = Math.floor((Date.now() - downTimeStartTime) / 1000)
    return downTime + elapsed
  }
  return downTime
}

async function startDownTimeTracking() {
  if (downTimeInterval) {
    return
  }

  if (!timerState.is_running && !timerState.is_paused) {
    lastNotifiedMultiple = 0

    if (!downTimeStartTime) {
      downTimeStartTime = Date.now()
      await saveData()
    }

    downTimeInterval = setInterval(async () => {
      if (!timerState.is_running && !timerState.is_paused) {
        const elapsed = Math.floor((Date.now() - downTimeStartTime) / 1000)
        const currentDownTime = downTime + elapsed

        const maxDownTime = settings.max_down_time || (15 * 60)
        const maxReminders = settings.max_downtime_reminders !== undefined ? parseInt(settings.max_downtime_reminders) : 0

        if (maxDownTime > 0) {
          const currentMultiple = Math.floor(currentDownTime / maxDownTime)
          if (currentMultiple > lastNotifiedMultiple && currentDownTime >= maxDownTime) {
            lastNotifiedMultiple = currentMultiple

            if (maxReminders > 0 && lastNotifiedMultiple >= maxReminders) {
              stopDownTimeTracking()
              return
            }

            showDownTimeNotification(maxDownTime, currentMultiple)
          }
        }
      } else {
        stopDownTimeTracking()
      }
    }, 1000)
  }
}

function stopDownTimeTracking() {
  if (downTimeInterval) {
    clearInterval(downTimeInterval)
    downTimeInterval = null
  }

  if (downTimeStartTime) {
    const elapsed = Math.floor((Date.now() - downTimeStartTime) / 1000)
    downTime = (downTime + elapsed) || 0
    downTimeStartTime = null
    saveData()
  }
}

// Notifications
function showNotification(completedMode, nextMode, pomodoros) {
  let title = '🍅 Timer Complete!'
  let body = ''

  if (completedMode === 'work') {
    body = `Pomodoro ${pomodoros} completed! `
    if (nextMode === 'short_break') {
      body += 'Take a short break ☕'
    } else {
      body += 'Take a long break 🌴'
    }
  } else if (completedMode === 'short_break') {
    body = 'Short break finished! Time to get back to work! 💼'
  } else if (completedMode === 'long_break') {
    body = 'Long break finished! Ready for more work? 💼'
  }

  if (Notification.isSupported()) {
    new Notification({
      title,
      body,
      icon: path.join(__dirname, '../dist/icon48.png')
    }).show()
  }
}

function showDownTimeNotification(maxDownTime, currentMultiple) {
  const minutes = Math.floor(maxDownTime / 60)
  const exceededTime = maxDownTime * currentMultiple
  const exceededMinutes = Math.floor(exceededTime / 60)

  if (Notification.isSupported()) {
    new Notification({
      title: '⏰ Downtime Alert',
      body: `You've been away for ${exceededMinutes} minutes (${currentMultiple}x ${minutes} min)`,
      icon: path.join(__dirname, '../dist/icon48.png')
    }).show()
  }
}

// Audio notification
function playAudioNotification(previousMode) {
  const isWorkCompletion = previousMode === 'work'
  const soundData = isWorkCompletion ? settings.work_sound : settings.break_sound

  if (soundData && mainWindow) {
    mainWindow.webContents.send('play-sound', { soundData, type: previousMode })
  } else if (mainWindow) {
    mainWindow.webContents.send('play-sound', { soundData: null, type: previousMode })
  }
}

// IPC Handlers
ipcMain.handle('get-timer-state', async () => {
  return {
    timerState,
    settings,
    downTime: await getCurrentDownTime()
  }
})

ipcMain.handle('get-settings', async () => {
  return settings
})

ipcMain.handle('start-timer', async () => {
  if (timerState.is_paused) {
    timerState.is_paused = false
  } else {
    if (timerState.current_mode === 'work') {
      timerState.remaining_seconds = settings.work_duration
    } else if (timerState.current_mode === 'short_break') {
      timerState.remaining_seconds = settings.short_break
    } else {
      timerState.remaining_seconds = settings.long_break
    }
  }
  timerState.is_running = true
  await saveData()
  return timerState
})

ipcMain.handle('pause-timer', async () => {
  if (timerState.is_running && !timerState.is_paused) {
    timerState.is_paused = true
    await saveData()
  }
  return timerState
})

ipcMain.handle('skip-timer', async () => {
  timerState.is_running = false
  timerState.is_paused = false

  if (timerState.current_mode === 'work') {
    timerState.completed_pomodoros += 1
    if (timerState.completed_pomodoros % settings.short_breaks_until_long === 0) {
      timerState.current_mode = 'long_break'
      timerState.remaining_seconds = settings.long_break
    } else {
      timerState.current_mode = 'short_break'
      timerState.remaining_seconds = settings.short_break
    }
  } else if (timerState.current_mode === 'short_break') {
    timerState.current_mode = 'work'
    timerState.remaining_seconds = settings.work_duration
  } else if (timerState.current_mode === 'long_break') {
    timerState.current_mode = 'work'
    timerState.remaining_seconds = settings.work_duration
  }

  await saveData()
  await startDownTimeTracking()
  return timerState
})

ipcMain.handle('reset-timer', async () => {
  timerState.is_running = false
  timerState.is_paused = false
  timerState.current_mode = 'work'
  timerState.remaining_seconds = settings.work_duration
  await saveData()
  await startDownTimeTracking()
  return timerState
})

ipcMain.handle('update-settings', async (event, newSettings) => {
  settings = mergeSettingsWithDefaults(newSettings)
  await saveData()
  return settings
})

// App lifecycle
app.whenReady().then(async () => {
  await loadData()
  createWindow()
  startTimerUpdate()
  await startDownTimeTracking()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('before-quit', async () => {
  stopDownTimeTracking()
  await saveData()
})





