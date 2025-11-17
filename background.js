// Background service worker for Pomodoro Timer Extension
// Replaces the Flask backend functionality

// Default timer state
const defaultTimerState = {
  is_running: false,
  is_paused: false,
  current_mode: 'work', // 'work', 'short_break', 'long_break'
  remaining_seconds: 25 * 60, // Default 25 minutes
  completed_pomodoros: 0
}

// Default settings
const defaultSettings = {
  work_duration: 25 * 60, // seconds
  short_break: 5 * 60, // seconds
  long_break: 15 * 60, // seconds
  short_breaks_until_long: 4,
  auto_switch: false
}

// Initialize storage with defaults
async function initializeStorage() {
  const result = await chrome.storage.local.get(['timerState', 'settings'])
  
  if (!result.timerState) {
    await chrome.storage.local.set({ timerState: defaultTimerState })
  }
  
  if (!result.settings) {
    await chrome.storage.local.set({ settings: defaultSettings })
  }
}

// Load timer state from storage
async function loadTimerState() {
  const result = await chrome.storage.local.get(['timerState', 'settings'])
  return {
    timerState: result.timerState || defaultTimerState,
    settings: result.settings || defaultSettings
  }
}

// Save timer state to storage
async function saveTimerState(timerState) {
  await chrome.storage.local.set({ timerState })
}

// Save settings to storage
async function saveSettings(settings) {
  await chrome.storage.local.set({ settings })
}

// Update badge with remaining minutes
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
    // Clear badge when timer is not running
    chrome.action.setBadgeText({ text: '' })
  }
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
      if (timerState.remaining_seconds > 0) {
        timerState.remaining_seconds -= 1
        await saveTimerState(timerState)
        
        // Update badge
        await updateBadge(timerState)
        
        // Notify popup if open
        try {
          chrome.runtime.sendMessage({
            type: 'TIMER_UPDATE',
            timerState
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
        
        // Clear badge
        chrome.action.setBadgeText({ text: '' })
        
        // Open new tab when timer completes
        openTimerCompleteTab(previousMode, timerState.current_mode, timerState.completed_pomodoros)
        
        // Show notification
        showTimerCompleteNotification(previousMode, timerState.current_mode, timerState.completed_pomodoros)
        
        // Notify popup
        try {
          chrome.runtime.sendMessage({
            type: 'TIMER_COMPLETE',
            timerState,
            previousMode
          }).catch(() => {
            // Popup might not be open, ignore error
          })
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

// Store tab IDs for timer completion tabs
let timerCompleteTabIds = new Set()

// Listen for tab updates to inject script into timer completion tabs
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (timerCompleteTabIds.has(tabId) && changeInfo.status === 'complete') {
    // Inject script to handle button click
    chrome.scripting.executeScript({
      target: { tabId: tabId },
      func: () => {
        const button = document.getElementById('startTimerBtn');
        if (button) {
          button.addEventListener('click', function() {
            chrome.runtime.sendMessage({ type: 'START_TIMER' }, function(response) {
              window.close();
            });
          });
        }
      }
    }).catch((error) => {
      console.log('Script injection failed:', error);
    });
    // Remove from set after injection
    timerCompleteTabIds.delete(tabId);
  }
});

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
    <button class="button" id="startTimerBtn">Start Timer & Close</button>
  </div>
  <script>
    // Fallback script in case injection doesn't work
    (function() {
      function setupButton() {
        const button = document.getElementById('startTimerBtn');
        if (button && !button.dataset.setup) {
          button.dataset.setup = 'true';
          button.addEventListener('click', function() {
            if (typeof chrome !== 'undefined' && chrome.runtime && chrome.runtime.sendMessage) {
              chrome.runtime.sendMessage({ type: 'START_TIMER' }, function(response) {
                window.close();
              });
            } else {
              // If chrome.runtime is not available, try to close anyway
              window.close();
            }
          });
        }
      }
      
      // Try immediately
      setupButton();
      
      // Also try after a short delay in case DOM isn't ready
      setTimeout(setupButton, 100);
    })();
  </script>
</body>
</html>`
  
  // Create a data URL from the HTML
  const dataUrl = 'data:text/html;charset=utf-8,' + encodeURIComponent(htmlContent)
  
  // Open the new tab
  chrome.tabs.create({
    url: dataUrl,
    active: true
  }, (tab) => {
    // Store tab ID so we can inject script when it loads
    if (tab && tab.id) {
      timerCompleteTabIds.add(tab.id);
    }
  })
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
  
  chrome.notifications.create({
    type: 'basic',
    iconUrl: 'icon48.png',
    title: title,
    message: body,
    requireInteraction: true,
    priority: 2
  })
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
        sendResponse({ success: true, timerState, settings })
        break
        
      case 'START_TIMER':
        const startData = await loadTimerState()
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
chrome.notifications.onClicked.addListener((notificationId) => {
  chrome.notifications.clear(notificationId)
  // Focus the extension popup
  chrome.action.openPopup()
})

// Initialize badge on startup
async function initializeBadge() {
  const { timerState } = await loadTimerState()
  await updateBadge(timerState)
}

// Initialize on startup
chrome.runtime.onStartup.addListener(() => {
  initializeStorage().then(() => {
    startTimerUpdate()
    initializeBadge()
  })
})

chrome.runtime.onInstalled.addListener(() => {
  initializeStorage().then(() => {
    startTimerUpdate()
    initializeBadge()
  })
})

// Start timer update when service worker starts
initializeStorage().then(() => {
  startTimerUpdate()
  initializeBadge()
})

