// Background service worker for Pomodoro Timer Extension
// Replaces the Flask backend functionality

// Cross-browser API detection
const browserAPI = (typeof browser !== 'undefined' && browser.storage) 
  ? browser 
  : (typeof chrome !== 'undefined' ? chrome : null)

// Default timer state
const defaultTimerState = {
  is_running: false,
  is_paused: false,
  current_mode: 'work', // 'work', 'short_break', 'long_break'
  remaining_seconds: 25 * 60, // Default 25 minutes
  completed_pomodoros: 0
}

// Down time tracking
let downTime = 0
let downTimeStartTime = null
let downTimeInterval = null
let lastNotifiedMultiple = 0 // Track the last multiple of max_down_time that was notified (0 = first time, 1 = second time, etc.)

// Default settings - ensure all fields are present for consistency
const defaultSettings = {
  work_duration: 25 * 60, // seconds
  short_break: 5 * 60, // seconds
  long_break: 15 * 60, // seconds
  short_breaks_until_long: 4,
  auto_switch: false,
  max_down_time: 15 * 60, // 15 minutes in seconds
  max_downtime_reminders: 0, // 0 = unlimited reminders
  work_sound: null,
  work_sound_file_name: '',
  break_sound: null,
  break_sound_file_name: ''
}

// Merge settings with defaults to ensure consistency
function mergeSettingsWithDefaults(settings) {
  const merged = { ...defaultSettings }
  if (settings) {
    // Only copy valid settings that exist in defaults
    Object.keys(defaultSettings).forEach(key => {
      if (settings[key] !== undefined) {
        // Type validation and conversion
        if (key === 'work_duration' || key === 'short_break' || key === 'long_break' || key === 'max_down_time') {
          merged[key] = Math.max(1, parseInt(settings[key]) || defaultSettings[key])
        } else if (key === 'short_breaks_until_long' || key === 'max_downtime_reminders') {
          merged[key] = Math.max(0, parseInt(settings[key]) || defaultSettings[key])
        } else if (key === 'auto_switch') {
          merged[key] = Boolean(settings[key])
        } else {
          merged[key] = settings[key] !== null ? settings[key] : defaultSettings[key]
        }
      }
    })
  }
  return merged
}

// Merge timer state with defaults
function mergeTimerStateWithDefaults(timerState) {
  const merged = { ...defaultTimerState }
  if (timerState) {
    Object.keys(defaultTimerState).forEach(key => {
      if (timerState[key] !== undefined) {
        if (key === 'remaining_seconds' || key === 'completed_pomodoros') {
          merged[key] = Math.max(0, parseInt(timerState[key]) || defaultTimerState[key])
        } else if (key === 'is_running' || key === 'is_paused') {
          merged[key] = Boolean(timerState[key])
        } else {
          merged[key] = timerState[key]
        }
      }
    })
  }
  return merged
}

// Storage helper with cross-browser support
function getStorage() {
  return browserAPI && browserAPI.storage ? browserAPI.storage.local : null
}

// Initialize storage with defaults
async function initializeStorage() {
  const storage = getStorage()
  if (!storage) {
    console.error('Storage API not available')
    return
  }
  
  const result = await new Promise((resolve) => {
    storage.get(['timerState', 'settings', 'downTime', 'downTimeStartTime'], resolve)
  })
  
  // Merge and save timer state with defaults
  const mergedTimerState = mergeTimerStateWithDefaults(result.timerState)
  if (!result.timerState || JSON.stringify(result.timerState) !== JSON.stringify(mergedTimerState)) {
    await new Promise((resolve) => {
      storage.set({ timerState: mergedTimerState }, resolve)
    })
  }
  
  // Merge and save settings with defaults
  const mergedSettings = mergeSettingsWithDefaults(result.settings)
  if (!result.settings || JSON.stringify(result.settings) !== JSON.stringify(mergedSettings)) {
    await new Promise((resolve) => {
      storage.set({ settings: mergedSettings }, resolve)
    })
  }
  
  // Load down time
  if (result.downTime !== undefined) {
    downTime = result.downTime || 0
  }
  if (result.downTimeStartTime) {
    downTimeStartTime = result.downTimeStartTime
  }
}

// Load timer state from storage
async function loadTimerState() {
  const storage = getStorage()
  if (!storage) {
    return {
      timerState: defaultTimerState,
      settings: defaultSettings
    }
  }
  
  const result = await new Promise((resolve) => {
    storage.get(['timerState', 'settings'], resolve)
  })
  
  return {
    timerState: mergeTimerStateWithDefaults(result.timerState),
    settings: mergeSettingsWithDefaults(result.settings)
  }
}

// Save timer state to storage
async function saveTimerState(timerState) {
  const storage = getStorage()
  if (!storage) return
  
  const mergedState = mergeTimerStateWithDefaults(timerState)
  await new Promise((resolve) => {
    storage.set({ timerState: mergedState }, resolve)
  })
}

// Save settings to storage
async function saveSettings(settings) {
  const storage = getStorage()
  if (!storage) return
  
  const mergedSettings = mergeSettingsWithDefaults(settings)
  await new Promise((resolve) => {
    storage.set({ settings: mergedSettings }, resolve)
  })
}

// Format down time for badge
function formatDownTimeForBadge(seconds) {
  if (seconds < 60) {
    return seconds.toString()
  } else if (seconds < 3600) {
    const minutes = Math.floor(seconds / 60)
    return minutes.toString() + 'm'
  } else {
    const hours = Math.floor(seconds / 3600)
    return hours.toString() + 'h'
  }
}

// Update badge with remaining minutes or down time
async function updateBadge(timerState) {
  if (timerState.is_running && !timerState.is_paused) {
    const minutes = Math.ceil(timerState.remaining_seconds / 60)
    const badgeText = minutes > 0 ? minutes.toString() : '0'
    
    // Set badge text
    chrome.action.setBadgeText({ text: badgeText })
    
    // Set badge color based on mode
    let badgeColor = '#667eea' // default blue
    if (timerState.current_mode === 'short_break') {
      badgeColor = '#10b981' // green
    } else if (timerState.current_mode === 'long_break') {
      badgeColor = '#f59e0b' // orange
    }
    chrome.action.setBadgeBackgroundColor({ color: badgeColor })
  } else {
    // Show down time when timer is not running
    const currentDownTime = await getCurrentDownTime(timerState)
    if (currentDownTime > 0) {
      const badgeText = formatDownTimeForBadge(currentDownTime)
      const actionAPI = browserAPI && browserAPI.action ? browserAPI.action : 
                        (browserAPI && browserAPI.browserAction ? browserAPI.browserAction : null)
      if (actionAPI) {
        if (actionAPI.setBadgeText) {
          actionAPI.setBadgeText({ text: badgeText })
        }
        if (actionAPI.setBadgeBackgroundColor) {
          actionAPI.setBadgeBackgroundColor({ color: '#6b7280' }) // gray for down time
        }
      }
    } else {
      const actionAPI = browserAPI && browserAPI.action ? browserAPI.action : 
                        (browserAPI && browserAPI.browserAction ? browserAPI.browserAction : null)
      if (actionAPI && actionAPI.setBadgeText) {
        actionAPI.setBadgeText({ text: '' })
      }
    }
  }
}

// Get current down time
async function getCurrentDownTime(timerState) {
  if (timerState.is_running || timerState.is_paused) {
    return 0
  }
  
  if (downTimeStartTime) {
    const elapsed = Math.floor((Date.now() - downTimeStartTime) / 1000)
    return downTime + elapsed
  }
  
  return downTime
}

// Open down time exceeded tab
function openDownTimeExceededTab(maxDownTime, currentMultiple) {
  const minutes = Math.floor(maxDownTime / 60)
  const seconds = maxDownTime % 60
  const maxTimeText = seconds > 0 ? `${minutes}m ${seconds}s` : `${minutes}m`
  
  // Calculate the actual time that was exceeded
  const exceededTime = maxDownTime * currentMultiple
  const exceededMinutes = Math.floor(exceededTime / 60)
  const exceededSeconds = exceededTime % 60
  const exceededTimeText = exceededSeconds > 0 ? `${exceededMinutes}m ${exceededSeconds}s` : `${exceededMinutes}m`
  
  const htmlContent = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Down Time Exceeded</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      text-align: center;
      padding: 20px;
    }
    .container {
      background: white;
      border-radius: 20px;
      padding: 60px 40px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
      max-width: 500px;
      width: 100%;
    }
    .emoji {
      font-size: 80px;
      margin-bottom: 20px;
      display: block;
    }
    h1 {
      color: #1f2937;
      font-size: 2.5em;
      margin-bottom: 20px;
    }
    p {
      color: #6b7280;
      font-size: 1.2em;
      line-height: 1.6;
      margin-bottom: 30px;
    }
    .button {
      background: #ef4444;
      color: white;
      border: none;
      padding: 15px 30px;
      border-radius: 8px;
      font-size: 16px;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.3s ease;
    }
    .button:hover {
      background: #dc2626;
    }
  </style>
</head>
<body>
  <div class="container">
    <span class="emoji">⏰</span>
    <h1>Down Time Exceeded!</h1>
    <p>The down time has reached ${exceededTimeText} (${currentMultiple}x the maximum of ${maxTimeText}). Time to get back to work!</p>
    <button class="button" onclick="window.close()">Close</button>
  </div>
</body>
</html>`
  
  // Create a data URL from the HTML
  const dataUrl = 'data:text/html;charset=utf-8,' + encodeURIComponent(htmlContent)
  
  // Open the new tab
  chrome.tabs.create({
    url: dataUrl,
    active: true
  })
}

// Start down time tracking
async function startDownTimeTracking() {
  if (downTimeInterval) {
    return
  }
  
  const { timerState, settings } = await loadTimerState()
  if (!timerState.is_running && !timerState.is_paused) {
    // Reset notification tracking when starting to track
    lastNotifiedMultiple = 0
    
    if (!downTimeStartTime) {
      downTimeStartTime = Date.now()
      const storage = getStorage()
      if (storage) {
        await new Promise((resolve) => {
          storage.set({ downTimeStartTime }, resolve)
        })
      }
    }
    
    downTimeInterval = setInterval(async () => {
      const { timerState, settings } = await loadTimerState()
      if (!timerState.is_running && !timerState.is_paused) {
        const elapsed = Math.floor((Date.now() - downTimeStartTime) / 1000)
        const storage = getStorage()
        if (storage) {
          const downTimeResult = await new Promise((resolve) => {
            storage.get(['downTime'], resolve)
          })
          downTime = downTimeResult.downTime || 0
        }
        const currentDownTime = downTime + elapsed
        
        // Check if down time has crossed a new multiple of max_down_time
        const maxDownTime = settings.max_down_time || (15 * 60)
        const maxReminders = settings.max_downtime_reminders !== undefined ? parseInt(settings.max_downtime_reminders) : 0
        
        if (maxDownTime > 0) {
          const currentMultiple = Math.floor(currentDownTime / maxDownTime)
          // Only notify when we cross into a new multiple (e.g., 15, 30, 45 minutes)
          if (currentMultiple > lastNotifiedMultiple && currentDownTime >= maxDownTime) {
            lastNotifiedMultiple = currentMultiple
            
            // Check if we've reached the max reminders (0 = unlimited)
            if (maxReminders > 0 && lastNotifiedMultiple >= maxReminders) {
              // Pause downtime tracking after max reminders reached
              stopDownTimeTracking()
              return
            }
            
            openDownTimeExceededTab(maxDownTime, currentMultiple)
          }
        }
        
        await updateBadge(timerState)
      } else {
        stopDownTimeTracking()
      }
    }, 1000)
  }
}

// Stop down time tracking
async function stopDownTimeTracking() {
  if (downTimeInterval) {
    clearInterval(downTimeInterval)
    downTimeInterval = null
  }
  
  if (downTimeStartTime) {
    const elapsed = Math.floor((Date.now() - downTimeStartTime) / 1000)
    downTime = (downTime + elapsed) || 0
    downTimeStartTime = null
    const storage = getStorage()
    if (storage) {
      await new Promise((resolve) => {
        storage.set({ downTime, downTimeStartTime: null }, resolve)
      })
    }
  }
}

// Reset down time
async function resetDownTime() {
  downTime = 0
  downTimeStartTime = null
  lastNotifiedMultiple = 0
  const storage = getStorage()
  if (storage) {
    await new Promise((resolve) => {
      storage.set({ downTime: 0, downTimeStartTime: null }, resolve)
    })
  }
  stopDownTimeTracking()
}

// Update timer every second
let timerInterval = null

async function startTimerUpdate() {
  if (timerInterval) {
    clearInterval(timerInterval)
  }
  
  timerInterval = setInterval(async () => {
    const { timerState, settings } = await loadTimerState()
    
    if (timerState.is_running && !timerState.is_paused) {
      // Stop down time tracking when timer is running
      await stopDownTimeTracking()
      
      if (timerState.remaining_seconds > 0) {
        timerState.remaining_seconds -= 1
        await saveTimerState(timerState)
        
        // Update badge
        await updateBadge(timerState)
        
        // Notify popup if open
        try {
          const currentDownTime = await getCurrentDownTime(timerState)
          chrome.runtime.sendMessage({
            type: 'TIMER_UPDATE',
            timerState,
            downTime: currentDownTime
          }).catch(() => {
            // Popup might not be open, ignore error
          })
        } catch (e) {
          // Ignore
        }
      } else {
        // Timer completed
        timerState.is_running = false
        const previousMode = timerState.current_mode
        
        // Switch to next mode
        if (timerState.current_mode === 'work') {
          timerState.completed_pomodoros += 1
          // Check if we need a long break
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
        
        await saveTimerState(timerState)
        
        // Start down time tracking when timer completes
        await startDownTimeTracking()
        
        // Update badge (will show down time)
        await updateBadge(timerState)
        
        // Open new tab when timer completes
        openTimerCompleteTab(previousMode, timerState.current_mode, timerState.completed_pomodoros)
        
        // Show notification
        showTimerCompleteNotification(previousMode, timerState.current_mode, timerState.completed_pomodoros)
        
        // Play audio notification (works even when popup is closed)
        playAudioNotification(previousMode, settings)
        
        // Notify popup
        try {
          const currentDownTime = await getCurrentDownTime(timerState)
          const runtimeAPI = browserAPI && browserAPI.runtime ? browserAPI.runtime : null
          if (runtimeAPI && runtimeAPI.sendMessage) {
            runtimeAPI.sendMessage({
              type: 'TIMER_COMPLETE',
              timerState,
              previousMode,
              downTime: currentDownTime
            }, () => {
              // Ignore errors - popup might not be open
              if (runtimeAPI.lastError) {
                // Silently ignore
              }
            })
          }
        } catch (e) {
          // Ignore
        }
        
        // Auto-switch: automatically start the next phase if enabled
        if (settings.auto_switch) {
          timerState.is_running = true
          await saveTimerState(timerState)
          await updateBadge(timerState)
        }
      }
    }
  }, 1000)
}

// Open a new tab when timer completes
function openTimerCompleteTab(completedMode, nextMode, pomodoros) {
  // Create HTML content for the completion page
  let title = ''
  let message = ''
  let emoji = '🍅'
  
  if (completedMode === 'work') {
    title = `Pomodoro ${pomodoros} Completed!`
    emoji = '🍅'
    if (nextMode === 'short_break') {
      message = 'Great work! Time to take a short break ☕'
    } else {
      message = 'Excellent! You\'ve earned a long break 🌴'
    }
  } else if (completedMode === 'short_break') {
    title = 'Short Break Finished!'
    emoji = '☕'
    message = 'Break time is over! Ready to get back to work? 💼'
  } else if (completedMode === 'long_break') {
    title = 'Long Break Finished!'
    emoji = '🌴'
    message = 'You\'re refreshed! Time to tackle more work 💼'
  }
  
  const htmlContent = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${title}</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      text-align: center;
      padding: 20px;
    }
    .container {
      background: white;
      border-radius: 20px;
      padding: 60px 40px;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
      max-width: 500px;
      width: 100%;
    }
    .emoji {
      font-size: 80px;
      margin-bottom: 20px;
      display: block;
    }
    h1 {
      color: #1f2937;
      font-size: 2.5em;
      margin-bottom: 20px;
    }
    p {
      color: #6b7280;
      font-size: 1.2em;
      line-height: 1.6;
      margin-bottom: 30px;
    }
    .button {
      background: #667eea;
      color: white;
      border: none;
      padding: 15px 30px;
      border-radius: 8px;
      font-size: 16px;
      font-weight: 600;
      cursor: pointer;
      transition: background 0.3s ease;
    }
    .button:hover {
      background: #5568d3;
    }
  </style>
</head>
<body>
  <div class="container">
    <span class="emoji">${emoji}</span>
    <h1>${title}</h1>
    <p>${message}</p>
    <button class="button" onclick="window.close()">Close</button>
  </div>
</body>
</html>`
  
  // Create a data URL from the HTML
  const dataUrl = 'data:text/html;charset=utf-8,' + encodeURIComponent(htmlContent)
  
  // Open the new tab
  chrome.tabs.create({
    url: dataUrl,
    active: true
  })
}

// Play audio notification from background script
async function playAudioNotification(previousMode, settings) {
  try {
    // Determine which sound to play
    const isWorkCompletion = previousMode === 'work'
    const soundData = isWorkCompletion 
      ? settings.work_sound 
      : settings.break_sound
    
    // If custom sound is available, try to play it via a data URL in a new tab
    if (soundData) {
      // Create a temporary HTML page that plays the audio
      const audioHTML = `<!DOCTYPE html>
<html>
<head><title>Playing Sound</title></head>
<body>
  <script>
    const audio = new Audio('${soundData}');
    audio.volume = 0.7;
    audio.play().then(() => {
      setTimeout(() => window.close(), 2000);
    }).catch(() => {
      // Fallback to beep
      playBeep();
    });
    
    function playBeep() {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = 800;
      osc.type = 'sine';
      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.5);
      setTimeout(() => {
        const osc2 = ctx.createOscillator();
        const gain2 = ctx.createGain();
        osc2.connect(gain2);
        gain2.connect(ctx.destination);
        osc2.frequency.value = 800;
        osc2.type = 'sine';
        gain2.gain.setValueAtTime(0.3, ctx.currentTime);
        gain2.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
        osc2.start(ctx.currentTime);
        osc2.stop(ctx.currentTime + 0.5);
        setTimeout(() => window.close(), 1000);
      }, 300);
    }
  </script>
</body>
</html>`
      
      const dataUrl = 'data:text/html;charset=utf-8,' + encodeURIComponent(audioHTML)
      const tabsAPI = browserAPI && browserAPI.tabs ? browserAPI.tabs : null
      if (tabsAPI && tabsAPI.create) {
        tabsAPI.create({
          url: dataUrl,
          active: false
        }, (tab) => {
          // Close the tab after audio plays
          setTimeout(() => {
            if (tab && tab.id && tabsAPI.remove) {
              tabsAPI.remove(tab.id, () => {})
            }
          }, 3000)
        })
      }
    } else {
      // Play default beep via temporary tab
      const beepHTML = `<!DOCTYPE html>
<html>
<head><title>Beep</title></head>
<body>
  <script>
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    if (ctx.state === 'suspended') {
      ctx.resume().then(() => playBeep());
    } else {
      playBeep();
    }
    
    function playBeep() {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.frequency.value = 800;
      osc.type = 'sine';
      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
      osc.start(ctx.currentTime);
      osc.stop(ctx.currentTime + 0.5);
      setTimeout(() => {
        const osc2 = ctx.createOscillator();
        const gain2 = ctx.createGain();
        osc2.connect(gain2);
        gain2.connect(ctx.destination);
        osc2.frequency.value = 800;
        osc2.type = 'sine';
        gain2.gain.setValueAtTime(0.3, ctx.currentTime);
        gain2.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.5);
        osc2.start(ctx.currentTime);
        osc2.stop(ctx.currentTime + 0.5);
        setTimeout(() => window.close(), 1000);
      }, 300);
    }
  </script>
</body>
</html>`
      
      const dataUrl = 'data:text/html;charset=utf-8,' + encodeURIComponent(beepHTML)
      const tabsAPI = browserAPI && browserAPI.tabs ? browserAPI.tabs : null
      if (tabsAPI && tabsAPI.create) {
        tabsAPI.create({
          url: dataUrl,
          active: false
        }, (tab) => {
          setTimeout(() => {
            if (tab && tab.id && tabsAPI.remove) {
              tabsAPI.remove(tab.id, () => {})
            }
          }, 2000)
        })
      }
    }
  } catch (err) {
    console.error('Error playing audio notification:', err)
  }
}

// Show notification when timer completes
function showTimerCompleteNotification(completedMode, nextMode, pomodoros) {
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
  
  // Create notification with error handling
  // Cross-browser notifications
  const notificationsAPI = browserAPI && browserAPI.notifications ? browserAPI.notifications : null
  const runtimeAPI = browserAPI && browserAPI.runtime ? browserAPI.runtime : null
  
  if (notificationsAPI && notificationsAPI.create) {
    const iconUrl = runtimeAPI && runtimeAPI.getURL ? runtimeAPI.getURL('icon48.png') : 'icon48.png'
    
    notificationsAPI.create({
      type: 'basic',
      iconUrl: iconUrl,
      title: title,
      message: body,
      requireInteraction: true,
      priority: 2
    }, (notificationId) => {
      if (runtimeAPI && runtimeAPI.lastError) {
        console.error('Error creating notification:', runtimeAPI.lastError.message)
      } else {
        console.log('Notification created:', notificationId)
      }
    })
  }
}

// Handle messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  handleMessage(message, sender, sendResponse)
  return true // Keep channel open for async response
})

async function handleMessage(message, sender, sendResponse) {
  try {
    switch (message.type) {
      case 'GET_TIMER_STATE':
        const { timerState, settings } = await loadTimerState()
        const currentDownTime = await getCurrentDownTime(timerState)
        // Start down time tracking if timer is not running
        if (!timerState.is_running && !timerState.is_paused) {
          await startDownTimeTracking()
        }
        sendResponse({ success: true, timerState, settings, downTime: currentDownTime })
        break
        
      case 'START_TIMER':
        const startData = await loadTimerState()
        // Reset down time when timer starts
        await resetDownTime()
        if (startData.timerState.is_paused) {
          startData.timerState.is_paused = false
        } else {
          // Set timer to current mode's duration
          if (startData.timerState.current_mode === 'work') {
            startData.timerState.remaining_seconds = startData.settings.work_duration
          } else if (startData.timerState.current_mode === 'short_break') {
            startData.timerState.remaining_seconds = startData.settings.short_break
          } else {
            startData.timerState.remaining_seconds = startData.settings.long_break
          }
        }
        startData.timerState.is_running = true
        await saveTimerState(startData.timerState)
        await startTimerUpdate()
        await updateBadge(startData.timerState)
        sendResponse({ success: true, timerState: startData.timerState })
        break
        
      case 'PAUSE_TIMER':
        const pauseData = await loadTimerState()
        if (pauseData.timerState.is_running && !pauseData.timerState.is_paused) {
          pauseData.timerState.is_paused = true
          await saveTimerState(pauseData.timerState)
          await stopDownTimeTracking()
          await updateBadge(pauseData.timerState)
        }
        sendResponse({ success: true, timerState: pauseData.timerState })
        break
        
      case 'SKIP_TIMER':
        const skipData = await loadTimerState()
        skipData.timerState.is_running = false
        skipData.timerState.is_paused = false
        
        // Switch to next mode
        if (skipData.timerState.current_mode === 'work') {
          skipData.timerState.completed_pomodoros += 1
          if (skipData.timerState.completed_pomodoros % skipData.settings.short_breaks_until_long === 0) {
            skipData.timerState.current_mode = 'long_break'
            skipData.timerState.remaining_seconds = skipData.settings.long_break
          } else {
            skipData.timerState.current_mode = 'short_break'
            skipData.timerState.remaining_seconds = skipData.settings.short_break
          }
        } else if (skipData.timerState.current_mode === 'short_break') {
          skipData.timerState.current_mode = 'work'
          skipData.timerState.remaining_seconds = skipData.settings.work_duration
        } else if (skipData.timerState.current_mode === 'long_break') {
          skipData.timerState.current_mode = 'work'
          skipData.timerState.remaining_seconds = skipData.settings.work_duration
        }
        
        await saveTimerState(skipData.timerState)
        await startDownTimeTracking()
        await updateBadge(skipData.timerState)
        sendResponse({ success: true, timerState: skipData.timerState })
        break
        
      case 'RESET_TIMER':
        const resetData = await loadTimerState()
        resetData.timerState.is_running = false
        resetData.timerState.is_paused = false
        resetData.timerState.current_mode = 'work'
        resetData.timerState.remaining_seconds = resetData.settings.work_duration
        await saveTimerState(resetData.timerState)
        await startDownTimeTracking()
        await updateBadge(resetData.timerState)
        sendResponse({ success: true, timerState: resetData.timerState })
        break
        
      case 'GET_SETTINGS':
        const settingsData = await loadTimerState()
        sendResponse({ success: true, settings: settingsData.settings })
        break
        
      case 'UPDATE_SETTINGS':
        const updateData = await loadTimerState()
        const newSettings = message.settings
        
        if (newSettings.work_duration !== undefined) {
          updateData.settings.work_duration = Math.max(1, parseInt(newSettings.work_duration))
        }
        if (newSettings.short_break !== undefined) {
          updateData.settings.short_break = Math.max(1, parseInt(newSettings.short_break))
        }
        if (newSettings.long_break !== undefined) {
          updateData.settings.long_break = Math.max(1, parseInt(newSettings.long_break))
        }
        if (newSettings.short_breaks_until_long !== undefined) {
          updateData.settings.short_breaks_until_long = parseInt(newSettings.short_breaks_until_long)
        }
        if (newSettings.auto_switch !== undefined) {
          updateData.settings.auto_switch = Boolean(newSettings.auto_switch)
        }
        if (newSettings.max_down_time !== undefined) {
          updateData.settings.max_down_time = Math.max(1, parseInt(newSettings.max_down_time))
        }
        if (newSettings.work_sound !== undefined) {
          updateData.settings.work_sound = newSettings.work_sound
        }
        if (newSettings.work_sound_file_name !== undefined) {
          updateData.settings.work_sound_file_name = newSettings.work_sound_file_name
        }
        if (newSettings.break_sound !== undefined) {
          updateData.settings.break_sound = newSettings.break_sound
        }
        if (newSettings.break_sound_file_name !== undefined) {
          updateData.settings.break_sound_file_name = newSettings.break_sound_file_name
        }
        
        // Update current timer if not running
        if (!updateData.timerState.is_running) {
          if (updateData.timerState.current_mode === 'work') {
            updateData.timerState.remaining_seconds = updateData.settings.work_duration
          } else if (updateData.timerState.current_mode === 'short_break') {
            updateData.timerState.remaining_seconds = updateData.settings.short_break
          } else if (updateData.timerState.current_mode === 'long_break') {
            updateData.timerState.remaining_seconds = updateData.settings.long_break
          }
        }
        
        await saveSettings(updateData.settings)
        await saveTimerState(updateData.timerState)
        sendResponse({ success: true, settings: updateData.settings, timerState: updateData.timerState })
        break
        
      default:
        sendResponse({ success: false, error: 'Unknown message type' })
    }
  } catch (error) {
    console.error('Error handling message:', error)
    sendResponse({ success: false, error: error.message })
  }
}

// Handle notification clicks
// Notification click handler - cross-browser
if (notificationsAPI && notificationsAPI.onClicked) {
  notificationsAPI.onClicked.addListener((notificationId) => {
    if (notificationsAPI.clear) {
      notificationsAPI.clear(notificationId)
    }
    // Focus the extension popup
    if (actionAPI && actionAPI.openPopup) {
      actionAPI.openPopup()
    }
  })
}

// Initialize badge on startup
async function initializeBadge() {
  const { timerState } = await loadTimerState()
  // Start down time tracking if timer is not running
  if (!timerState.is_running && !timerState.is_paused) {
    await startDownTimeTracking()
  }
  await updateBadge(timerState)
}

// Initialize on startup
// Startup and install listeners - cross-browser
if (runtimeAPI) {
  if (runtimeAPI.onStartup && runtimeAPI.onStartup.addListener) {
    runtimeAPI.onStartup.addListener(() => {
      initializeStorage().then(() => {
        startTimerUpdate()
        initializeBadge()
      })
    })
  }
  
  if (runtimeAPI.onInstalled && runtimeAPI.onInstalled.addListener) {
    runtimeAPI.onInstalled.addListener(() => {
      initializeStorage().then(() => {
        startTimerUpdate()
        initializeBadge()
      })
    })
  }
}

// Start timer update when service worker starts
initializeStorage().then(() => {
  startTimerUpdate()
  initializeBadge()
})

