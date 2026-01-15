// Cross-platform API wrapper
// Supports Electron (Windows app) and Chrome Extension

// Detect if running in Electron
const isElectron = typeof window !== 'undefined' && window.electronAPI

// Electron API wrapper (will be set dynamically)
let electronAPI = null

// Detect browser API (for Chrome extension)
const browserAPI = (typeof browser !== 'undefined' && browser.runtime) 
  ? browser 
  : (typeof chrome !== 'undefined' ? chrome : null)

const chromeAPI = {
  // Get timer state
  async getTimerState() {
    // Use Electron API if available
    if (isElectron) {
      if (!electronAPI) {
        const module = await import('./electron-api.js')
        electronAPI = module.default
      }
      return electronAPI.getTimerState()
    }
    
    // Fallback to Chrome extension API
    if (!browserAPI || !browserAPI.runtime) {
      throw new Error('Browser runtime API not available')
    }
    
    return new Promise((resolve, reject) => {
      browserAPI.runtime.sendMessage({ type: 'GET_TIMER_STATE' }, (response) => {
        if (browserAPI.runtime.lastError) {
          reject(new Error(browserAPI.runtime.lastError.message))
        } else if (response && response.success) {
          resolve({
            data: {
              ...response.timerState,
              settings: response.settings
            },
            downTime: response.downTime
          })
        } else {
          reject(new Error(response?.error || 'Unknown error'))
        }
      })
    })
  },

  // Get settings
  async getSettings() {
    if (isElectron) {
      if (!electronAPI) {
        const module = await import('./electron-api.js')
        electronAPI = module.default
      }
      return electronAPI.getSettings()
    }
    
    if (!browserAPI || !browserAPI.runtime) {
      throw new Error('Browser runtime API not available')
    }
    
    return new Promise((resolve, reject) => {
      browserAPI.runtime.sendMessage({ type: 'GET_SETTINGS' }, (response) => {
        if (browserAPI.runtime.lastError) {
          reject(new Error(browserAPI.runtime.lastError.message))
        } else if (response && response.success) {
          resolve({ data: response.settings })
        } else {
          reject(new Error(response?.error || 'Unknown error'))
        }
      })
    })
  },

  // Start timer
  async startTimer() {
    if (isElectron) {
      if (!electronAPI) {
        const module = await import('./electron-api.js')
        electronAPI = module.default
      }
      return electronAPI.startTimer()
    }
    
    if (!browserAPI || !browserAPI.runtime) {
      throw new Error('Browser runtime API not available')
    }
    
    return new Promise((resolve, reject) => {
      browserAPI.runtime.sendMessage({ type: 'START_TIMER' }, (response) => {
        if (browserAPI.runtime.lastError) {
          reject(new Error(browserAPI.runtime.lastError.message))
        } else if (response && response.success) {
          resolve({ data: response.timerState })
        } else {
          reject(new Error(response?.error || 'Unknown error'))
        }
      })
    })
  },

  // Pause timer
  async pauseTimer() {
    if (isElectron) {
      if (!electronAPI) {
        const module = await import('./electron-api.js')
        electronAPI = module.default
      }
      return electronAPI.pauseTimer()
    }
    
    if (!browserAPI || !browserAPI.runtime) {
      throw new Error('Browser runtime API not available')
    }
    
    return new Promise((resolve, reject) => {
      browserAPI.runtime.sendMessage({ type: 'PAUSE_TIMER' }, (response) => {
        if (browserAPI.runtime.lastError) {
          reject(new Error(browserAPI.runtime.lastError.message))
        } else if (response && response.success) {
          resolve({ data: response.timerState })
        } else {
          reject(new Error(response?.error || 'Unknown error'))
        }
      })
    })
  },

  // Skip timer
  async skipTimer() {
    if (isElectron) {
      if (!electronAPI) {
        const module = await import('./electron-api.js')
        electronAPI = module.default
      }
      return electronAPI.skipTimer()
    }
    
    if (!browserAPI || !browserAPI.runtime) {
      throw new Error('Browser runtime API not available')
    }
    
    return new Promise((resolve, reject) => {
      browserAPI.runtime.sendMessage({ type: 'SKIP_TIMER' }, (response) => {
        if (browserAPI.runtime.lastError) {
          reject(new Error(browserAPI.runtime.lastError.message))
        } else if (response && response.success) {
          resolve({ data: response.timerState })
        } else {
          reject(new Error(response?.error || 'Unknown error'))
        }
      })
    })
  },

  // Reset timer
  async resetTimer() {
    if (isElectron) {
      if (!electronAPI) {
        const module = await import('./electron-api.js')
        electronAPI = module.default
      }
      return electronAPI.resetTimer()
    }
    
    if (!browserAPI || !browserAPI.runtime) {
      throw new Error('Browser runtime API not available')
    }
    
    return new Promise((resolve, reject) => {
      browserAPI.runtime.sendMessage({ type: 'RESET_TIMER' }, (response) => {
        if (browserAPI.runtime.lastError) {
          reject(new Error(browserAPI.runtime.lastError.message))
        } else if (response && response.success) {
          resolve({ data: response.timerState })
        } else {
          reject(new Error(response?.error || 'Unknown error'))
        }
      })
    })
  },

  // Update settings
  async updateSettings(settings) {
    if (isElectron) {
      if (!electronAPI) {
        const module = await import('./electron-api.js')
        electronAPI = module.default
      }
      return electronAPI.updateSettings(settings)
    }
    
    if (!browserAPI || !browserAPI.runtime) {
      throw new Error('Browser runtime API not available')
    }
    
    return new Promise((resolve, reject) => {
      browserAPI.runtime.sendMessage({ 
        type: 'UPDATE_SETTINGS', 
        settings 
      }, (response) => {
        if (browserAPI.runtime.lastError) {
          reject(new Error(browserAPI.runtime.lastError.message))
        } else if (response && response.success) {
          resolve({ 
            data: response.settings,
            timerState: response.timerState 
          })
        } else {
          reject(new Error(response?.error || 'Unknown error'))
        }
      })
    })
  }
}

export default chromeAPI

