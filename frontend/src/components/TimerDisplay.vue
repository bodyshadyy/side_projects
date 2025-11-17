<template>
  <div class="timer-display">
    <div class="timer-circle-container">
      <svg class="progress-ring" width="280" height="280">
        <circle
          class="progress-ring-background"
          stroke="#e5e7eb"
          stroke-width="8"
          fill="transparent"
          r="130"
          cx="140"
          cy="140"
        />
        <circle
          class="progress-ring-circle"
          :class="modeClass"
          :stroke-dasharray="circumference"
          :stroke-dashoffset="progressOffset"
          stroke-width="8"
          fill="transparent"
          r="130"
          cx="140"
          cy="140"
          transform="rotate(-90 140 140)"
        />
      </svg>
      
      <div class="timer-content">
        <div class="mode-indicator" :class="modeClass">
          <span class="mode-icon">{{ modeIcon }}</span>
          <h2 class="mode-text">{{ modeText }}</h2>
        </div>
        
        <div class="timer-time">
          {{ formattedTime }}
        </div>
        
        <div class="timer-status">
          <span v-if="isRunning && !isPaused">Running</span>
          <span v-else-if="isPaused">Paused</span>
          <span v-else>Ready</span>
        </div>
      </div>
    </div>
    
    <div class="stats">
      <div class="stat-item">
        <span class="stat-label">Completed</span>
        <span class="stat-value">{{ completedPomodoros }}</span>
      </div>
    </div>
  </div>
</template>

<script>
import { computed, watch } from 'vue'

export default {
  name: 'TimerDisplay',
  props: {
    mode: {
      type: String,
      required: true
    },
    remainingSeconds: {
      type: Number,
      required: true
    },
    isRunning: {
      type: Boolean,
      default: false
    },
    isPaused: {
      type: Boolean,
      default: false
    },
    completedPomodoros: {
      type: Number,
      default: 0
    },
    settings: {
      type: Object,
      required: false,
      default: () => ({
        work_duration: 25 * 60,  // in seconds
        short_break: 5 * 60,  // in seconds
        long_break: 15 * 60,  // in seconds
        short_breaks_until_long: 4,
        auto_switch: false
      })
    }
  },
  emits: ['timer-complete'],
  setup(props, { emit }) {
    const radius = 130
    const circumference = 2 * Math.PI * radius
    
    const totalSeconds = computed(() => {
      // Ensure settings exist and have valid values
      // Settings are now in seconds directly, not minutes
      const settings = props.settings || {}
      
      if (props.mode === 'work') {
        const duration = settings.work_duration || (25 * 60)
        return Math.max(1, duration)
      } else if (props.mode === 'short_break') {
        const duration = settings.short_break || (5 * 60)
        return Math.max(1, duration)
      } else {
        const duration = settings.long_break || (15 * 60)
        return Math.max(1, duration)
      }
    })
    
    const progress = computed(() => {
      if (!totalSeconds.value || totalSeconds.value === 0) {
        return 0
      }
      // Handle case where remainingSeconds might be greater than totalSeconds (e.g., after settings change)
      const clampedRemaining = Math.min(props.remainingSeconds, totalSeconds.value)
      const elapsed = Math.max(0, totalSeconds.value - clampedRemaining)
      const progressValue = Math.min(1, Math.max(0, elapsed / totalSeconds.value))
      return isNaN(progressValue) ? 0 : progressValue
    })
    
    const progressOffset = computed(() => {
      return circumference - (progress.value * circumference)
    })
    
    const formattedTime = computed(() => {
      const minutes = Math.floor(props.remainingSeconds / 60)
      const seconds = props.remainingSeconds % 60
      return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
    })
    
    const modeText = computed(() => {
      switch (props.mode) {
        case 'work':
          return 'Work Time'
        case 'short_break':
          return 'Short Break'
        case 'long_break':
          return 'Long Break'
        default:
          return 'Work Time'
      }
    })
    
    const modeIcon = computed(() => {
      switch (props.mode) {
        case 'work':
          return '💼'
        case 'short_break':
          return '☕'
        case 'long_break':
          return '🌴'
        default:
          return '💼'
      }
    })
    
    const modeClass = computed(() => {
      return `mode-${props.mode}`
    })
    
    watch(() => props.remainingSeconds, (newVal, oldVal) => {
      if (newVal === 0 && oldVal > 0) {
        emit('timer-complete')
      }
    })
    
    // Watch settings changes to ensure progress updates
    watch(() => props.settings, () => {
      // Force reactivity when settings change
    }, { deep: true })
    
    return {
      circumference,
      progressOffset,
      formattedTime,
      modeText,
      modeIcon,
      modeClass
    }
  }
}
</script>

<style scoped>
.timer-display {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 30px;
}

.timer-circle-container {
  position: relative;
  width: 280px;
  height: 280px;
  margin: 20px 0;
  display: flex;
  justify-content: center;
  align-items: center;
}

.progress-ring {
  position: absolute;
  top: 0;
  left: 0;
  transform: rotate(0deg);
}

.progress-ring-circle {
  transition: stroke-dashoffset 0.5s ease, stroke 0.3s ease;
  stroke: #667eea;
}

.mode-work .progress-ring-circle {
  stroke: #667eea;
}

.mode-short_break .progress-ring-circle {
  stroke: #10b981;
}

.mode-long_break .progress-ring-circle {
  stroke: #f59e0b;
}

.timer-content {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  padding: 20px;
}

.mode-indicator {
  margin-bottom: 15px;
  text-align: center;
}

.mode-icon {
  font-size: 2.5em;
  display: block;
  margin-bottom: 5px;
}

.mode-text {
  font-size: 1.2em;
  font-weight: 600;
  color: #667eea;
  margin: 0;
}

.mode-work .mode-text {
  color: #667eea;
}

.mode-short_break .mode-text {
  color: #10b981;
}

.mode-long_break .mode-text {
  color: #f59e0b;
}

.timer-time {
  font-size: 4.5em;
  font-weight: 700;
  color: #1f2937;
  font-variant-numeric: tabular-nums;
  line-height: 1;
  margin: 10px 0;
  text-align: center;
}

.timer-status {
  font-size: 0.95em;
  color: #6b7280;
  margin-top: 10px;
  text-align: center;
  font-weight: 500;
}

.stats {
  display: flex;
  gap: 30px;
  margin-top: 20px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-label {
  font-size: 0.9em;
  color: #6b7280;
  margin-bottom: 5px;
}

.stat-value {
  font-size: 1.8em;
  font-weight: 700;
  color: #667eea;
}
</style>

