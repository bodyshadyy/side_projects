// Cross-browser API compatibility layer
// Supports Chrome, Firefox, Edge, and other Chromium-based browsers

// Detect browser API
const browserAPI = (typeof browser !== 'undefined' && browser.storage) 
  ? browser 
  : (typeof chrome !== 'undefined' ? chrome : null)

// Storage API wrapper
export const storage = {
  local: {
    get: (keys) => {
      return new Promise((resolve) => {
        if (browserAPI && browserAPI.storage && browserAPI.storage.local) {
          browserAPI.storage.local.get(keys, resolve)
        } else {
          resolve({})
        }
      })
    },
    set: (items) => {
      return new Promise((resolve, reject) => {
        if (browserAPI && browserAPI.storage && browserAPI.storage.local) {
          browserAPI.storage.local.set(items, () => {
            if (browserAPI.runtime && browserAPI.runtime.lastError) {
              reject(browserAPI.runtime.lastError)
            } else {
              resolve()
            }
          })
        } else {
          reject(new Error('Storage API not available'))
        }
      })
    }
  }
}

// Runtime API wrapper
export const runtime = {
  sendMessage: (message) => {
    return new Promise((resolve, reject) => {
      if (browserAPI && browserAPI.runtime && browserAPI.runtime.sendMessage) {
        browserAPI.runtime.sendMessage(message, (response) => {
          if (browserAPI.runtime.lastError) {
            reject(browserAPI.runtime.lastError)
          } else {
            resolve(response)
          }
        })
      } else {
        reject(new Error('Runtime API not available'))
      }
    })
  },
  onMessage: browserAPI && browserAPI.runtime ? browserAPI.runtime.onMessage : null,
  getURL: (path) => {
    if (browserAPI && browserAPI.runtime && browserAPI.runtime.getURL) {
      return browserAPI.runtime.getURL(path)
    }
    return path
  },
  lastError: browserAPI && browserAPI.runtime ? browserAPI.runtime.lastError : null
}

// Notifications API wrapper
export const notifications = {
  create: (options, callback) => {
    if (browserAPI && browserAPI.notifications && browserAPI.notifications.create) {
      browserAPI.notifications.create(options, callback)
    } else if (callback) {
      callback(null)
    }
  }
}

// Tabs API wrapper
export const tabs = {
  create: (options, callback) => {
    if (browserAPI && browserAPI.tabs && browserAPI.tabs.create) {
      browserAPI.tabs.create(options, callback)
    } else if (callback) {
      callback(null)
    }
  },
  remove: (tabId) => {
    return new Promise((resolve, reject) => {
      if (browserAPI && browserAPI.tabs && browserAPI.tabs.remove) {
        browserAPI.tabs.remove(tabId, () => {
          if (browserAPI.runtime && browserAPI.runtime.lastError) {
            reject(browserAPI.runtime.lastError)
          } else {
            resolve()
          }
        })
      } else {
        resolve()
      }
    })
  }
}

// Action API wrapper (for badges)
export const action = {
  setBadgeText: (options) => {
    if (browserAPI && browserAPI.action && browserAPI.action.setBadgeText) {
      browserAPI.action.setBadgeText(options)
    } else if (browserAPI && browserAPI.browserAction && browserAPI.browserAction.setBadgeText) {
      // Firefox uses browserAction
      browserAPI.browserAction.setBadgeText(options)
    }
  },
  setBadgeBackgroundColor: (options) => {
    if (browserAPI && browserAPI.action && browserAPI.action.setBadgeBackgroundColor) {
      browserAPI.action.setBadgeBackgroundColor(options)
    } else if (browserAPI && browserAPI.browserAction && browserAPI.browserAction.setBadgeBackgroundColor) {
      // Firefox uses browserAction
      browserAPI.browserAction.setBadgeBackgroundColor(options)
    }
  }
}

export default {
  storage,
  runtime,
  notifications,
  tabs,
  action,
  isAvailable: () => browserAPI !== null
}


