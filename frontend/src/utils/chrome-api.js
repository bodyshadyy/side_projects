// Chrome Extension API wrapper
// Replaces axios calls with Chrome messaging

const chromeAPI = {
  // Get timer state
  async getTimerState() {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage({ type: 'GET_TIMER_STATE' }, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message))
        } else if (response && response.success) {
          resolve({
            data: {
              ...response.timerState,
              settings: response.settings
            }
          })
        } else {
          reject(new Error(response?.error || 'Unknown error'))
        }
      })
    })
  },

  // Get settings
  async getSettings() {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage({ type: 'GET_SETTINGS' }, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message))
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
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage({ type: 'START_TIMER' }, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message))
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
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage({ type: 'PAUSE_TIMER' }, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message))
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
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage({ type: 'SKIP_TIMER' }, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message))
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
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage({ type: 'RESET_TIMER' }, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message))
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
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage({ 
        type: 'UPDATE_SETTINGS', 
        settings 
      }, (response) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message))
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

