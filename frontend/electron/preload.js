const { contextBridge, ipcRenderer } = require('electron')

// Expose protected methods that allow the renderer process to use
// the ipcRenderer without exposing the entire object
contextBridge.exposeInMainWorld('electronAPI', {
  // Timer operations
  getTimerState: () => ipcRenderer.invoke('get-timer-state'),
  getSettings: () => ipcRenderer.invoke('get-settings'),
  startTimer: () => ipcRenderer.invoke('start-timer'),
  pauseTimer: () => ipcRenderer.invoke('pause-timer'),
  skipTimer: () => ipcRenderer.invoke('skip-timer'),
  resetTimer: () => ipcRenderer.invoke('reset-timer'),
  updateSettings: (settings) => ipcRenderer.invoke('update-settings', settings),

  // Listeners
  onTimerUpdate: (callback) => {
    ipcRenderer.on('timer-update', (event, data) => callback(data))
  },
  onTimerComplete: (callback) => {
    ipcRenderer.on('timer-complete', (event, data) => callback(data))
  },
  onPlaySound: (callback) => {
    ipcRenderer.on('play-sound', (event, data) => callback(data))
  },

  // Remove listeners
  removeAllListeners: (channel) => {
    ipcRenderer.removeAllListeners(channel)
  }
})





