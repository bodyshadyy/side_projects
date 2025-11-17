<template>
  <div class="notes-card">
    <h2 class="card-title">📄 Notes</h2>
    
    <div class="calendar-container">
      <div class="calendar-header">
        <button @click="previousMonth" class="btn-nav">‹</button>
        <span class="month-year">{{ currentMonthYear }}</span>
        <button @click="nextMonth" class="btn-nav">›</button>
      </div>
      
      <div class="calendar-grid">
        <div class="calendar-weekday" v-for="day in weekDays" :key="day">
          {{ day }}
        </div>
        
        <div
          v-for="(date, index) in calendarDays"
          :key="index"
          :class="[
            'calendar-day',
            {
              'other-month': !date.currentMonth,
              'today': date.isToday,
              'selected': date.isSelected,
              'has-notes': date.hasNotes
            }
          ]"
          @click="selectDate(date.date)"
        >
          {{ date.day }}
          <span v-if="date.hasNotes" class="notes-indicator">●</span>
        </div>
      </div>
    </div>
    
    <div class="selected-date">
      <strong>{{ selectedDateFormatted }}</strong>
    </div>
    
    <textarea
      v-model="notesText"
      @input="saveNotes"
      placeholder="Write your notes here..."
      class="notes-textarea"
    ></textarea>
    <div class="notes-footer">
      <span class="notes-info">{{ characterCount }} characters</span>
      <button @click="clearNotes" class="btn-clear">Clear</button>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'

export default {
  name: 'Notes',
  setup() {
    const notesText = ref('')
    const selectedDate = ref(new Date())
    const currentMonth = ref(new Date().getMonth())
    const currentYear = ref(new Date().getFullYear())
    const notesData = ref({}) // { 'YYYY-MM-DD': 'note text' }

    const weekDays = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

    // Format date as YYYY-MM-DD for storage
    const formatDateKey = (date) => {
      const d = new Date(date)
      const year = d.getFullYear()
      const month = String(d.getMonth() + 1).padStart(2, '0')
      const day = String(d.getDate()).padStart(2, '0')
      return `${year}-${month}-${day}`
    }

    // Load all notes from localStorage
    const loadAllNotes = () => {
      const saved = localStorage.getItem('pomodoro-notes-calendar')
      if (saved) {
        try {
          notesData.value = JSON.parse(saved)
        } catch (e) {
          console.error('Error loading notes:', e)
          notesData.value = {}
        }
      }
    }

    // Save all notes to localStorage
    const saveAllNotes = () => {
      localStorage.setItem('pomodoro-notes-calendar', JSON.stringify(notesData.value))
    }

    // Load notes for selected date
    const loadNotes = () => {
      const dateKey = formatDateKey(selectedDate.value)
      notesText.value = notesData.value[dateKey] || ''
    }

    // Save notes for selected date
    const saveNotes = () => {
      const dateKey = formatDateKey(selectedDate.value)
      notesData.value[dateKey] = notesText.value
      saveAllNotes()
    }

    const selectDate = (date) => {
      selectedDate.value = new Date(date)
      loadNotes()
    }

    const clearNotes = () => {
      if (confirm('Are you sure you want to clear notes for this date?')) {
        const dateKey = formatDateKey(selectedDate.value)
        notesData.value[dateKey] = ''
        delete notesData.value[dateKey]
        notesText.value = ''
        saveAllNotes()
      }
    }

    const previousMonth = () => {
      currentMonth.value--
      if (currentMonth.value < 0) {
        currentMonth.value = 11
        currentYear.value--
      }
    }

    const nextMonth = () => {
      currentMonth.value++
      if (currentMonth.value > 11) {
        currentMonth.value = 0
        currentYear.value++
      }
    }

    const characterCount = computed(() => {
      return notesText.value.length
    })

    const selectedDateFormatted = computed(() => {
      const options = { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' }
      return selectedDate.value.toLocaleDateString('en-US', options)
    })

    const currentMonthYear = computed(() => {
      const options = { year: 'numeric', month: 'long' }
      return new Date(currentYear.value, currentMonth.value).toLocaleDateString('en-US', options)
    })

    const calendarDays = computed(() => {
      const days = []
      const firstDay = new Date(currentYear.value, currentMonth.value, 1)
      const lastDay = new Date(currentYear.value, currentMonth.value + 1, 0)
      const startDate = new Date(firstDay)
      startDate.setDate(startDate.getDate() - startDate.getDay())

      const today = new Date()
      today.setHours(0, 0, 0, 0)

      for (let i = 0; i < 42; i++) {
        const date = new Date(startDate)
        date.setDate(startDate.getDate() + i)

        const dateKey = formatDateKey(date)
        const hasNotes = notesData.value[dateKey] && notesData.value[dateKey].trim().length > 0

        days.push({
          date: new Date(date),
          day: date.getDate(),
          currentMonth: date.getMonth() === currentMonth.value,
          isToday: date.getTime() === today.getTime(),
          isSelected: formatDateKey(date) === formatDateKey(selectedDate.value),
          hasNotes: hasNotes
        })
      }

      return days
    })

    onMounted(() => {
      loadAllNotes()
      loadNotes()
    })

    return {
      notesText,
      selectedDate,
      currentMonth,
      currentYear,
      weekDays,
      characterCount,
      selectedDateFormatted,
      currentMonthYear,
      calendarDays,
      saveNotes,
      clearNotes,
      selectDate,
      previousMonth,
      nextMonth
    }
  }
}
</script>

<style scoped>
.notes-card {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  height: 100%;
  display: flex;
  flex-direction: column;
}

.card-title {
  margin: 0 0 20px 0;
  color: #1f2937;
  font-size: 1.5em;
  font-weight: 600;
}

.calendar-container {
  margin-bottom: 20px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  overflow: hidden;
}

.calendar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}

.month-year {
  font-weight: 600;
  color: #1f2937;
  font-size: 1em;
}

.btn-nav {
  background: transparent;
  border: none;
  font-size: 1.5em;
  color: #667eea;
  cursor: pointer;
  padding: 4px 12px;
  border-radius: 6px;
  transition: background 0.2s ease;
}

.btn-nav:hover {
  background: #e5e7eb;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 1px;
  background: #e5e7eb;
  padding: 1px;
}

.calendar-weekday {
  background: white;
  padding: 8px 4px;
  text-align: center;
  font-size: 0.75em;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
}

.calendar-day {
  background: white;
  padding: 8px;
  text-align: center;
  cursor: pointer;
  font-size: 0.9em;
  color: #1f2937;
  transition: all 0.2s ease;
  position: relative;
  min-height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.calendar-day:hover {
  background: #f3f4f6;
}

.calendar-day.other-month {
  color: #9ca3af;
  background: #f9fafb;
}

.calendar-day.today {
  background: #dbeafe;
  font-weight: 600;
  color: #1e40af;
}

.calendar-day.selected {
  background: #667eea;
  color: white;
  font-weight: 600;
}

.calendar-day.selected.today {
  background: #5568d3;
}

.calendar-day.has-notes {
  font-weight: 500;
}

.notes-indicator {
  position: absolute;
  top: 2px;
  right: 2px;
  font-size: 0.6em;
  color: #10b981;
}

.calendar-day.selected .notes-indicator {
  color: white;
}

.selected-date {
  margin-bottom: 12px;
  padding: 8px 12px;
  background: #f9fafb;
  border-radius: 6px;
  color: #4b5563;
  font-size: 0.9em;
  text-align: center;
}

.notes-textarea {
  flex: 1;
  width: 100%;
  min-height: 200px;
  padding: 14px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  font-size: 14px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  line-height: 1.6;
  resize: vertical;
  transition: border-color 0.3s ease;
  background: #fafafa;
}

.notes-textarea:focus {
  outline: none;
  border-color: #667eea;
  background: white;
}

.notes-textarea::placeholder {
  color: #9ca3af;
}

.notes-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e5e7eb;
}

.notes-info {
  color: #6b7280;
  font-size: 0.9em;
}

.btn-clear {
  padding: 8px 16px;
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 500;
  font-size: 0.9em;
  cursor: pointer;
  transition: background 0.3s ease;
}

.btn-clear:hover {
  background: #dc2626;
}
</style>

