// Service Worker for handling notifications when page is in background
self.addEventListener('install', (event) => {
  self.skipWaiting()
  // Activate immediately
  return self.clients.claim()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim())
})

// Handle notification clicks - this works even when page is closed or in background
self.addEventListener('notificationclick', (event) => {
  console.log('Notification clicked:', event)
  event.notification.close()
  
  // Get URL from notification data
  let urlToOpen = '/timer-notification.html'
  if (event.notification.data && event.notification.data.url) {
    urlToOpen = event.notification.data.url
  }
  
  // Ensure URL is absolute
  if (!urlToOpen.startsWith('http')) {
    urlToOpen = self.location.origin + urlToOpen
  }
  
  event.waitUntil(
    clients.matchAll({
      type: 'window',
      includeUncontrolled: true
    }).then((clientList) => {
      // Check if there's already a notification window open
      for (let i = 0; i < clientList.length; i++) {
        const client = clientList[i]
        if (client.url && client.url.includes('timer-notification')) {
          // Focus existing notification window
          return client.focus()
        }
      }
      
      // No existing window, open a new one
      // clients.openWindow() works from service worker notification clicks
      if (clients.openWindow) {
        return clients.openWindow(urlToOpen)
      }
    }).catch((error) => {
      console.error('Error handling notification click:', error)
    })
  )
})

// Handle background sync or push events (for future use)
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting()
  }
})

