// Electron API wrapper for the frontend
// This file is used when running in Electron mode

const electronAPI = {
  // Get timer state
  async getTimerState() {
    if (window.electronAPI) {
      const result = await window.electronAPI.getTimerState()
      return {
        data: {
          ...result.timerState,
          settings: result.settings
        },
        downTime: result.downTime
      }
    }
    throw new Error('Electron API not available')
  },

  // Get settings
  async getSettings() {
    if (window.electronAPI) {
      const settings = await window.electronAPI.getSettings()
      return { data: settings }
    }
    throw new Error('Electron API not available')
  },

  // Start timer
  async startTimer() {
    if (window.electronAPI) {
      const timerState = await window.electronAPI.startTimer()
      return { data: timerState }
    }
    throw new Error('Electron API not available')
  },

  // Pause timer
  async pauseTimer() {
    if (window.electronAPI) {
      const timerState = await window.electronAPI.pauseTimer()
      return { data: timerState }
    }
    throw new Error('Electron API not available')
  },

  // Skip timer
  async skipTimer() {
    if (window.electronAPI) {
      const timerState = await window.electronAPI.skipTimer()
      return { data: timerState }
    }
    throw new Error('Electron API not available')
  },

  // Reset timer
  async resetTimer() {
    if (window.electronAPI) {
      const timerState = await window.electronAPI.resetTimer()
      return { data: timerState }
    }
    throw new Error('Electron API not available')
  },

  // Update settings
  async updateSettings(settings) {
    if (window.electronAPI) {
      const updatedSettings = await window.electronAPI.updateSettings(settings)
      return {
        data: updatedSettings,
        timerState: null
      }
    }
    throw new Error('Electron API not available')
  }
}

export default electronAPI

