<template>
  <Transition name="toast">
    <div v-if="visible" :class="['toast', `toast-${type}`]">
      <span class="toast-icon">{{ icon }}</span>
      <span class="toast-message">{{ message }}</span>
    </div>
  </Transition>
</template>

<script>
import { ref, watch, computed } from 'vue'

export default {
  name: 'ToastNotification',
  props: {
    message: {
      type: String,
      required: true
    },
    type: {
      type: String,
      default: 'success',
      validator: (value) => ['success', 'info', 'warning', 'error'].includes(value)
    },
    duration: {
      type: Number,
      default: 3000
    },
    show: {
      type: Boolean,
      default: false
    }
  },
  emits: ['close'],
  setup(props, { emit }) {
    const visible = ref(false)
    
    const icons = {
      success: '✅',
      info: 'ℹ️',
      warning: '⚠️',
      error: '❌'
    }
    
    const icon = computed(() => icons[props.type] || icons.success)
    
    watch(() => props.show, (newVal) => {
      if (newVal) {
        visible.value = true
        if (props.duration > 0) {
          setTimeout(() => {
            visible.value = false
            setTimeout(() => emit('close'), 300) // Wait for transition
          }, props.duration)
        }
      }
    })
    
    return {
      visible,
      icon
    }
  }
}
</script>

<style scoped>
.toast {
  position: fixed;
  top: 20px;
  right: 20px;
  background: white;
  padding: 16px 20px;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  display: flex;
  align-items: center;
  gap: 12px;
  z-index: 10000;
  min-width: 300px;
  max-width: 400px;
  animation: slideIn 0.3s ease-out;
}

.toast-success {
  border-left: 4px solid #10b981;
}

.toast-info {
  border-left: 4px solid #3b82f6;
}

.toast-warning {
  border-left: 4px solid #f59e0b;
}

.toast-error {
  border-left: 4px solid #ef4444;
}

.toast-icon {
  font-size: 1.5em;
}

.toast-message {
  font-weight: 500;
  color: #1f2937;
  flex: 1;
}

@keyframes slideIn {
  from {
    transform: translateX(400px);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.toast-enter-active {
  transition: all 0.3s ease-out;
}

.toast-leave-active {
  transition: all 0.3s ease-in;
}

.toast-enter-from {
  transform: translateX(400px);
  opacity: 0;
}

.toast-leave-to {
  transform: translateX(400px);
  opacity: 0;
}
</style>

