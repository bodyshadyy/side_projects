import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  build: {
    outDir: 'dist',
    rollupOptions: {
      input: resolve(__dirname, 'popup.html')
    },
    // Ensure assets are properly referenced
    assetsDir: 'assets',
    // Don't inline assets for extension compatibility
    assetsInlineLimit: 0
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  }
})

