<template>
  <div class="app-container">
    <div class="version-indicator">v1.0.0</div>
    <h1 class="app-title">🍅 Pomodoro Timer</h1>
    
    <div class="main-grid">
      <div class="pomodoro-column">
        <div class="pomodoro-app">
          <TimerDisplay 
            :mode="timerState.current_mode"
            :remaining-seconds="timerState.remaining_seconds"
            :is-running="timerState.is_running"
            :is-paused="timerState.is_paused"
            :completed-pomodoros="timerState.completed_pomodoros"
            :settings="settings"
            :down-time="downTime"
            @timer-complete="handleTimerComplete"
          />
          
          <div class="controls">
            <button 
              v-if="!timerState.is_running" 
              @click="startTimer" 
              class="btn btn-primary"
            >
              Start
            </button>
            <button 
              v-if="timerState.is_running && !timerState.is_paused" 
              @click="pauseTimer" 
              class="btn btn-secondary"
            >
              Pause
            </button>
            <button 
              v-if="timerState.is_paused" 
              @click="startTimer" 
              class="btn btn-primary"
            >
              Resume
            </button>
            <button 
              @click="skipTimer" 
              class="btn btn-warning"
              :disabled="!timerState.is_running && !timerState.is_paused"
            >
              Skip
            </button>
            <button 
              @click="resetTimer" 
              class="btn btn-danger"
            >
              Reset
            </button>
          </div>
          
          <button 
            @click="showSettings = !showSettings" 
            class="btn btn-settings"
          >
            {{ showSettings ? 'Hide' : 'Show' }} Settings
          </button>
          
          <SettingsPanel 
            v-if="showSettings"
            :settings="settings"
            @update-settings="updateSettings"
          />
        </div>
      </div>
      
      <div class="todo-column">
        <ToDoList />
      </div>
      
      <div class="notes-column">
        <Notes />
      </div>
    </div>
    
    <ToastNotification
      :message="notificationMessage"
      :type="notificationType"
      :show="showNotification"
      @close="showNotification = false"
    />
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import chromeAPI from './utils/chrome-api.js'
import TimerDisplay from './components/TimerDisplay.vue'
import SettingsPanel from './components/SettingsPanel.vue'
import ToastNotification from './components/ToastNotification.vue'
import ToDoList from './components/ToDoList.vue'
import Notes from './components/Notes.vue'

export default {
  name: 'App',
  components: {
    TimerDisplay,
    SettingsPanel,
    ToastNotification,
    ToDoList,
    Notes
  },
  setup() {
    const timerState = ref({
      is_running: false,
      is_paused: false,
      current_mode: 'work',
      remaining_seconds: 25 * 60,
      completed_pomodoros: 0
    })
    
    const settings = ref({
      work_duration: 25 * 60,  // in seconds
      short_break: 5 * 60,  // in seconds
      long_break: 15 * 60,  // in seconds
      short_breaks_until_long: 4,
      auto_switch: false,
      max_down_time: 15 * 60  // 15 minutes in seconds
    })
    
    const showSettings = ref(false)
    const showNotification = ref(false)
    const notificationMessage = ref('')
    const notificationType = ref('success')
    const downTime = ref(0) // Down time in seconds
    let pollInterval = null
    let downTimeInterval = null
    let previousRemaining = 25 * 60
    let previousMode = 'work'
    let previousCompleted = 0
    let wasRunning = false
    let isInitialLoad = true // Track if this is the first load
    
    const showToast = (message, type = 'success') => {
      notificationMessage.value = message
      notificationType.value = type
      showNotification.value = false // Reset to trigger animation
      setTimeout(() => {
        showNotification.value = true
      }, 10)
    }
    
    const fetchTimerState = async () => {
      try {
        const response = await chromeAPI.getTimerState()
        
        // On initial load, just set the state without triggering notifications
        if (isInitialLoad) {
          previousRemaining = response.data.remaining_seconds
          previousMode = response.data.current_mode
          previousCompleted = response.data.completed_pomodoros
          wasRunning = response.data.is_running
          timerState.value = response.data
          // Load down time from response if available
          if (response.downTime !== undefined) {
            downTime.value = response.downTime
          }
          isInitialLoad = false
          return
        }
        
        // Check if timer just completed or mode switched
        const modeChanged = previousMode !== response.data.current_mode
        const pomodoroCompleted = response.data.completed_pomodoros > previousCompleted
        
        if (modeChanged) {
          // Mode switched (timer completed and moved to next phase)
          playNotificationSound()
          
          // Show notification based on what phase we're entering
          if (response.data.current_mode === 'work') {
            // Coming back from break
            if (previousMode === 'long_break') {
              showToast('Long break finished! Ready for more work? 💼', 'info')
            } else {
              showToast('Break finished! Time to get back to work! 💼', 'info')
            }
          } else if (response.data.current_mode === 'short_break') {
            // Work session completed, entering short break
            const message = `Pomodoro ${response.data.completed_pomodoros} completed! Take a break ☕`
            showToast(message, 'success')
          } else if (response.data.current_mode === 'long_break') {
            // Multiple pomodoros completed, entering long break
            const message = `Amazing! ${response.data.completed_pomodoros} pomodoros completed! Enjoy your long break 🌴`
            showToast(message, 'success')
          }
        } else if (pomodoroCompleted && !modeChanged) {
          // Edge case: pomodoro count increased without mode change (work just completed)
          playNotificationSound()
          const message = `Pomodoro ${response.data.completed_pomodoros} completed! 🍅`
          showToast(message, 'success')
        }
        
        
        previousRemaining = response.data.remaining_seconds
        previousMode = response.data.current_mode
        previousCompleted = response.data.completed_pomodoros
        timerState.value = response.data
      } catch (error) {
        console.error('Error fetching timer state:', error)
      }
    }
    
    const fetchSettings = async () => {
      try {
        const response = await chromeAPI.getSettings()
        settings.value = {
          work_duration: response.data.work_duration,  // already in seconds
          short_break: response.data.short_break,  // already in seconds
          long_break: response.data.long_break,  // already in seconds
          short_breaks_until_long: response.data.short_breaks_until_long,
          auto_switch: response.data.auto_switch || false,
          max_down_time: response.data.max_down_time || (15 * 60)  // default 15 minutes
        }
      } catch (error) {
        console.error('Error fetching settings:', error)
      }
    }
    
    const startTimer = async () => {
      try {
        await chromeAPI.startTimer()
        // Down time is reset in background script
        downTime.value = 0
        fetchTimerState()
      } catch (error) {
        console.error('Error starting timer:', error)
      }
    }
    
    const pauseTimer = async () => {
      try {
        await chromeAPI.pauseTimer()
        fetchTimerState()
      } catch (error) {
        console.error('Error pausing timer:', error)
      }
    }
    
    const skipTimer = async () => {
      try {
        await chromeAPI.skipTimer()
        fetchTimerState()
        playNotificationSound()
      } catch (error) {
        console.error('Error skipping timer:', error)
      }
    }
    
    const resetTimer = async () => {
      try {
        await chromeAPI.resetTimer()
        fetchTimerState()
      } catch (error) {
        console.error('Error resetting timer:', error)
      }
    }
    
    const updateSettings = async (newSettings) => {
      try {
        const response = await chromeAPI.updateSettings(newSettings)
        settings.value = {
          work_duration: response.data.work_duration,
          short_break: response.data.short_break,
          long_break: response.data.long_break,
          short_breaks_until_long: response.data.short_breaks_until_long,
          auto_switch: response.data.auto_switch || false,
          max_down_time: response.data.max_down_time || (15 * 60)
        }
        if (response.timerState) {
          timerState.value = response.timerState
        }
        showToast('Settings saved successfully! ✅', 'success')
      } catch (error) {
        console.error('Error updating settings:', error)
        showToast('Failed to save settings. Please try again.', 'error')
      }
    }
    
    const handleTimerComplete = () => {
      playNotificationSound()
    }
    
    const playNotificationSound = () => {
      // Use Web Audio API to generate a beep sound
      const audioContext = new (window.AudioContext || window.webkitAudioContext)()
      const oscillator = audioContext.createOscillator()
      const gainNode = audioContext.createGain()
      
      oscillator.connect(gainNode)
      gainNode.connect(audioContext.destination)
      
      oscillator.frequency.value = 800
      oscillator.type = 'sine'
      
      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime)
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5)
      
      oscillator.start(audioContext.currentTime)
      oscillator.stop(audioContext.currentTime + 0.5)
      
      // Play a second beep after a short delay
      setTimeout(() => {
        const oscillator2 = audioContext.createOscillator()
        const gainNode2 = audioContext.createGain()
        
        oscillator2.connect(gainNode2)
        gainNode2.connect(audioContext.destination)
        
        oscillator2.frequency.value = 800
        oscillator2.type = 'sine'
        
        gainNode2.gain.setValueAtTime(0.3, audioContext.currentTime)
        gainNode2.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5)
        
        oscillator2.start(audioContext.currentTime)
        oscillator2.stop(audioContext.currentTime + 0.5)
      }, 300)
    }
    
    // Manage down time stopwatch - sync with background script
    const updateDownTime = async () => {
      // Only count down time when timer is not running and not paused
      if (!timerState.value.is_running && !timerState.value.is_paused) {
        try {
          const response = await chromeAPI.getTimerState()
          if (response.downTime !== undefined) {
            downTime.value = response.downTime
          }
        } catch (error) {
          // Ignore errors, just increment locally
          downTime.value++
        }
      }
    }

    // Watch timer state to manage down time
    watch(() => [timerState.value.is_running, timerState.value.is_paused], ([isRunning, isPaused]) => {
      // If timer just started (was not running, now is running), reset down time
      if (!wasRunning && isRunning) {
        downTime.value = 0
      }
      wasRunning = isRunning

      // Start/stop down time interval
      if (!isRunning && !isPaused) {
        // Timer is stopped, start counting down time
        if (!downTimeInterval) {
          // Sync with background script first
          chromeAPI.getTimerState().then(response => {
            if (response.downTime !== undefined) {
              downTime.value = response.downTime
            }
          })
          downTimeInterval = setInterval(updateDownTime, 1000)
        }
      } else {
        // Timer is running or paused, stop counting down time
        if (downTimeInterval) {
          clearInterval(downTimeInterval)
          downTimeInterval = null
        }
      }
    })

    // Listen for messages from background script
    const setupMessageListener = () => {
      if (chrome && chrome.runtime && chrome.runtime.onMessage) {
        chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
          if (message.type === 'TIMER_UPDATE') {
            timerState.value = message.timerState
            // Sync down time on timer updates
            if (message.downTime !== undefined) {
              downTime.value = message.downTime
            }
          } else if (message.type === 'TIMER_COMPLETE') {
            timerState.value = message.timerState
            // Down time starts tracking when timer completes (handled by background)
            if (message.downTime !== undefined) {
              downTime.value = message.downTime
            }
            playNotificationSound()
            // Show toast notification
            if (message.timerState.current_mode === 'work') {
              if (message.previousMode === 'long_break') {
                showToast('Long break finished! Ready for more work? 💼', 'info')
              } else {
                showToast('Break finished! Time to get back to work! 💼', 'info')
              }
            } else if (message.timerState.current_mode === 'short_break') {
              const msg = `Pomodoro ${message.timerState.completed_pomodoros} completed! Take a break ☕`
              showToast(msg, 'success')
            } else if (message.timerState.current_mode === 'long_break') {
              const msg = `Amazing! ${message.timerState.completed_pomodoros} pomodoros completed! Enjoy your long break 🌴`
              showToast(msg, 'success')
            }
          }
          return true // Keep channel open for async response
        })
      }
    }
    
    onMounted(async () => {
      await fetchTimerState()
      await fetchSettings()
      pollInterval = setInterval(fetchTimerState, 1000)
      setupMessageListener()
      
      // Initialize wasRunning based on current state
      wasRunning = timerState.value.is_running
      
      // Start down time interval if timer is not running and not paused
      if (!timerState.value.is_running && !timerState.value.is_paused) {
        downTimeInterval = setInterval(updateDownTime, 1000)
      }
    })
    
    onUnmounted(() => {
      if (pollInterval) {
        clearInterval(pollInterval)
      }
      if (downTimeInterval) {
        clearInterval(downTimeInterval)
      }
    })
    
    return {
      timerState,
      settings,
      showSettings,
      showNotification,
      notificationMessage,
      notificationType,
      downTime,
      startTimer,
      pauseTimer,
      skipTimer,
      resetTimer,
      updateSettings,
      handleTimerComplete
    }
  }
}
</script>

<style scoped>
.app-container {
  width: 100%;
  min-height: 100%;
  padding: 20px;
  overflow-y: auto;
}

.version-indicator {
  text-align: center;
  color: rgba(255, 255, 255, 0.6);
  font-size: 0.75em;
  margin-bottom: 5px;
  font-weight: 400;
}

.app-title {
  text-align: center;
  color: white;
  margin-bottom: 30px;
  font-size: 2.5em;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
}

.main-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
  max-width: 600px;
  margin: 0 auto;
}

.todo-column,
.notes-column {
  display: flex;
  flex-direction: column;
}

.pomodoro-column {
  display: flex;
  flex-direction: column;
}

.pomodoro-app {
  background: white;
  border-radius: 20px;
  padding: 30px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  width: 100%;
}

/* Extension popup is always single column */

.controls {
  display: flex;
  gap: 10px;
  justify-content: center;
  flex-wrap: wrap;
  margin-top: 30px;
}

.btn {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #5568d3;
  transform: translateY(-2px);
}

.btn-secondary {
  background: #f59e0b;
  color: white;
}

.btn-secondary:hover:not(:disabled) {
  background: #d97706;
  transform: translateY(-2px);
}

.btn-warning {
  background: #10b981;
  color: white;
}

.btn-warning:hover:not(:disabled) {
  background: #059669;
  transform: translateY(-2px);
}

.btn-danger {
  background: #ef4444;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #dc2626;
  transform: translateY(-2px);
}

.btn-settings {
  margin-top: 20px;
  background: #6b7280;
  color: white;
  width: 100%;
}

.btn-settings:hover {
  background: #4b5563;
  transform: translateY(-2px);
}
</style>

