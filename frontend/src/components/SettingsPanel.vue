<template>
  <div class="settings-panel">
    <h3 class="settings-title">Settings</h3>
    
    <div class="settings-form">
      <div class="duration-group">
        <label class="duration-label">Work Duration</label>
        <div class="time-inputs">
          <div class="time-input-group">
            <input
              id="work-minutes"
              type="number"
              v-model.number="workMinutes"
              min="0"
              max="120"
              placeholder="0"
            />
            <label for="work-minutes">Min</label>
          </div>
          <div class="time-input-group">
            <input
              id="work-seconds"
              type="number"
              v-model.number="workSeconds"
              min="0"
              max="59"
              placeholder="0"
            />
            <label for="work-seconds">Sec</label>
          </div>
        </div>
      </div>
      
      <div class="duration-group">
        <label class="duration-label">Short Break</label>
        <div class="time-inputs">
          <div class="time-input-group">
            <input
              id="short-minutes"
              type="number"
              v-model.number="shortMinutes"
              min="0"
              max="60"
              placeholder="0"
            />
            <label for="short-minutes">Min</label>
          </div>
          <div class="time-input-group">
            <input
              id="short-seconds"
              type="number"
              v-model.number="shortSeconds"
              min="0"
              max="59"
              placeholder="0"
            />
            <label for="short-seconds">Sec</label>
          </div>
        </div>
      </div>
      
      <div class="duration-group">
        <label class="duration-label">Long Break</label>
        <div class="time-inputs">
          <div class="time-input-group">
            <input
              id="long-minutes"
              type="number"
              v-model.number="longMinutes"
              min="0"
              max="60"
              placeholder="0"
            />
            <label for="long-minutes">Min</label>
          </div>
          <div class="time-input-group">
            <input
              id="long-seconds"
              type="number"
              v-model.number="longSeconds"
              min="0"
              max="59"
              placeholder="0"
            />
            <label for="long-seconds">Sec</label>
          </div>
        </div>
      </div>
      
      <div class="setting-item">
        <label for="breaks-until-long">Short Breaks Until Long Break</label>
        <input
          id="breaks-until-long"
          type="number"
          v-model.number="localSettings.short_breaks_until_long"
          min="1"
          max="10"
        />
      </div>
      
      <div class="duration-group">
        <label class="duration-label">Max Down Time</label>
        <div class="time-inputs">
          <div class="time-input-group">
            <input
              id="max-down-minutes"
              type="number"
              v-model.number="maxDownMinutes"
              min="0"
              max="120"
              placeholder="0"
            />
            <label for="max-down-minutes">Min</label>
          </div>
          <div class="time-input-group">
            <input
              id="max-down-seconds"
              type="number"
              v-model.number="maxDownSeconds"
              min="0"
              max="59"
              placeholder="0"
            />
            <label for="max-down-seconds">Sec</label>
          </div>
        </div>
      </div>
      
      <div class="setting-item">
        <label for="max-downtime-reminders">Max Downtime Reminders</label>
        <input
          id="max-downtime-reminders"
          type="number"
          v-model.number="localSettings.max_downtime_reminders"
          min="0"
          max="100"
          placeholder="0"
        />
        <span class="setting-hint">After this many reminders, downtime tracking will pause (0 = unlimited)</span>
      </div>
      
      <div class="setting-item toggle-item">
        <label class="toggle-label">
          <input
            type="checkbox"
            v-model="localSettings.auto_switch"
            class="toggle-input"
          />
          <span class="toggle-text">Auto-switch to next phase when timer completes</span>
        </label>
      </div>
      
      <div class="setting-item">
        <label for="work-sound">Work Completion Sound (MP3)</label>
        <div class="file-input-group">
          <input
            id="work-sound"
            type="file"
            accept="audio/mpeg,audio/mp3"
            @change="handleWorkSoundChange"
            class="file-input"
          />
          <div v-if="workSoundFileName" class="file-name">{{ workSoundFileName }}</div>
          <button v-if="workSoundFileName" @click="clearWorkSound" class="btn-clear">Clear</button>
        </div>
      </div>
      
      <div class="setting-item">
        <label for="break-sound">Break Completion Sound (MP3)</label>
        <div class="file-input-group">
          <input
            id="break-sound"
            type="file"
            accept="audio/mpeg,audio/mp3"
            @change="handleBreakSoundChange"
            class="file-input"
          />
          <div v-if="breakSoundFileName" class="file-name">{{ breakSoundFileName }}</div>
          <button v-if="breakSoundFileName" @click="clearBreakSound" class="btn-clear">Clear</button>
        </div>
      </div>
      
      <button @click="saveSettings" class="btn-save">
        Save Settings
      </button>
    </div>
  </div>
</template>

<script>
import { ref, watch } from 'vue'

export default {
  name: 'SettingsPanel',
  props: {
    settings: {
      type: Object,
      required: true
    }
  },
  emits: ['update-settings'],
  setup(props, { emit }) {
    const localSettings = ref({ ...props.settings })
    
    // Convert seconds to minutes and seconds for display
    const workMinutes = ref(Math.floor((localSettings.value.work_duration || 0) / 60))
    const workSeconds = ref((localSettings.value.work_duration || 0) % 60)
    const shortMinutes = ref(Math.floor((localSettings.value.short_break || 0) / 60))
    const shortSeconds = ref((localSettings.value.short_break || 0) % 60)
    const longMinutes = ref(Math.floor((localSettings.value.long_break || 0) / 60))
    const longSeconds = ref((localSettings.value.long_break || 0) % 60)
    const maxDownMinutes = ref(Math.floor((localSettings.value.max_down_time || 15 * 60) / 60))
    const maxDownSeconds = ref((localSettings.value.max_down_time || 15 * 60) % 60)
    
    // Sound file handling
    const workSoundFileName = ref(localSettings.value.work_sound_file_name || '')
    const breakSoundFileName = ref(localSettings.value.break_sound_file_name || '')
    
    watch(() => props.settings, (newSettings) => {
      localSettings.value = { ...newSettings }
      // Update time inputs when settings change
      workMinutes.value = Math.floor((newSettings.work_duration || 0) / 60)
      workSeconds.value = (newSettings.work_duration || 0) % 60
      shortMinutes.value = Math.floor((newSettings.short_break || 0) / 60)
      shortSeconds.value = (newSettings.short_break || 0) % 60
      longMinutes.value = Math.floor((newSettings.long_break || 0) / 60)
      longSeconds.value = (newSettings.long_break || 0) % 60
      maxDownMinutes.value = Math.floor((newSettings.max_down_time || 15 * 60) / 60)
      maxDownSeconds.value = (newSettings.max_down_time || 15 * 60) % 60
      workSoundFileName.value = newSettings.work_sound_file_name || ''
      breakSoundFileName.value = newSettings.break_sound_file_name || ''
    }, { deep: true })
    
    const handleWorkSoundChange = (event) => {
      const file = event.target.files[0]
      if (file) {
        if (file.type !== 'audio/mpeg' && file.type !== 'audio/mp3' && !file.name.endsWith('.mp3')) {
          alert('Please select an MP3 file')
          event.target.value = ''
          return
        }
        
        const reader = new FileReader()
        reader.onload = (e) => {
          localSettings.value.work_sound = e.target.result // base64 data URL
          workSoundFileName.value = file.name
        }
        reader.readAsDataURL(file)
      }
    }
    
    const handleBreakSoundChange = (event) => {
      const file = event.target.files[0]
      if (file) {
        if (file.type !== 'audio/mpeg' && file.type !== 'audio/mp3' && !file.name.endsWith('.mp3')) {
          alert('Please select an MP3 file')
          event.target.value = ''
          return
        }
        
        const reader = new FileReader()
        reader.onload = (e) => {
          localSettings.value.break_sound = e.target.result // base64 data URL
          breakSoundFileName.value = file.name
        }
        reader.readAsDataURL(file)
      }
    }
    
    const clearWorkSound = () => {
      localSettings.value.work_sound = null
      localSettings.value.work_sound_file_name = ''
      workSoundFileName.value = ''
      // Reset file input
      const input = document.getElementById('work-sound')
      if (input) input.value = ''
    }
    
    const clearBreakSound = () => {
      localSettings.value.break_sound = null
      localSettings.value.break_sound_file_name = ''
      breakSoundFileName.value = ''
      // Reset file input
      const input = document.getElementById('break-sound')
      if (input) input.value = ''
    }
    
    const saveSettings = () => {
      // Convert minutes and seconds back to total seconds
      const settingsToSave = {
        ...localSettings.value,
        work_duration: (workMinutes.value || 0) * 60 + (workSeconds.value || 0),
        short_break: (shortMinutes.value || 0) * 60 + (shortSeconds.value || 0),
        long_break: (longMinutes.value || 0) * 60 + (longSeconds.value || 0),
        max_down_time: (maxDownMinutes.value || 0) * 60 + (maxDownSeconds.value || 0),
        auto_switch: localSettings.value.auto_switch || false,
        work_sound: localSettings.value.work_sound || null,
        work_sound_file_name: workSoundFileName.value || '',
        break_sound: localSettings.value.break_sound || null,
        break_sound_file_name: breakSoundFileName.value || ''
      }
      
      // Ensure minimum 1 second
      if (settingsToSave.work_duration < 1) settingsToSave.work_duration = 1
      if (settingsToSave.short_break < 1) settingsToSave.short_break = 1
      if (settingsToSave.long_break < 1) settingsToSave.long_break = 1
      if (settingsToSave.max_down_time < 1) settingsToSave.max_down_time = 1
      
      emit('update-settings', settingsToSave)
    }
    
    return {
      localSettings,
      workMinutes,
      workSeconds,
      shortMinutes,
      shortSeconds,
      longMinutes,
      longSeconds,
      maxDownMinutes,
      maxDownSeconds,
      workSoundFileName,
      breakSoundFileName,
      handleWorkSoundChange,
      handleBreakSoundChange,
      clearWorkSound,
      clearBreakSound,
      saveSettings
    }
  }
}
</script>

<style scoped>
.settings-panel {
  margin-top: 30px;
  padding: 25px;
  background: #f9fafb;
  border-radius: 12px;
  border: 2px solid #e5e7eb;
}

.settings-title {
  color: #1f2937;
  margin-bottom: 20px;
  font-size: 1.5em;
  text-align: center;
}

.settings-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.setting-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.setting-item label {
  font-weight: 600;
  color: #374151;
  font-size: 0.95em;
}

.setting-hint {
  font-size: 0.85em;
  color: #6b7280;
  font-style: italic;
  margin-top: 4px;
  display: block;
}

.setting-item input {
  padding: 12px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 0.3s ease;
}

.setting-item input:focus {
  outline: none;
  border-color: #667eea;
}

.duration-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.duration-label {
  font-weight: 600;
  color: #374151;
  font-size: 0.95em;
}

.time-inputs {
  display: flex;
  gap: 15px;
  align-items: flex-end;
}

.time-input-group {
  display: flex;
  flex-direction: column;
  gap: 5px;
  flex: 1;
}

.time-input-group input {
  padding: 12px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 0.3s ease;
  text-align: center;
}

.time-input-group input:focus {
  outline: none;
  border-color: #667eea;
}

.time-input-group label {
  font-size: 0.85em;
  color: #6b7280;
  text-align: center;
  font-weight: 500;
}

.toggle-item {
  padding: 10px 0;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
}

.toggle-input {
  width: 20px;
  height: 20px;
  cursor: pointer;
  accent-color: #667eea;
}

.toggle-text {
  font-weight: 500;
  color: #374151;
  user-select: none;
}

.btn-save {
  margin-top: 10px;
  padding: 14px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-save:hover {
  background: #5568d3;
  transform: translateY(-2px);
}

.file-input-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-input {
  padding: 8px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  transition: border-color 0.3s ease;
}

.file-input:focus {
  outline: none;
  border-color: #667eea;
}

.file-name {
  font-size: 0.9em;
  color: #6b7280;
  font-style: italic;
  padding: 4px 0;
}

.btn-clear {
  padding: 8px 16px;
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  align-self: flex-start;
}

.btn-clear:hover {
  background: #dc2626;
  transform: translateY(-1px);
}
</style>

