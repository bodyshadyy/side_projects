<template>
  <div class="todo-card">
    <h2 class="card-title">📝 To-Do List</h2>
    <div class="todo-input-container">
      <input
        v-model="newTodo"
        @keyup.enter="addTodo"
        type="text"
        placeholder="Add a new task..."
        class="todo-input"
      />
      <button @click="addTodo" class="btn-add">Add</button>
    </div>
    <div class="todo-list">
      <div
        v-for="(todo, index) in todos"
        :key="todo.id"
        class="todo-item"
        :class="{ completed: todo.completed }"
      >
        <input
          type="checkbox"
          v-model="todo.completed"
          @change="saveTodos"
          class="todo-checkbox"
        />
        <input
          v-if="todo.editing"
          v-model="todo.text"
          @blur="finishEditing(todo)"
          @keyup.enter="finishEditing(todo)"
          @keyup.esc="cancelEditing(todo)"
          class="todo-edit-input"
          ref="editInput"
        />
        <span
          v-else
          @dblclick="startEditing(todo)"
          class="todo-text"
        >
          {{ todo.text }}
        </span>
        <span class="todo-date">{{ formatDate(todo.date) }}</span>
        <button @click="deleteTodo(index)" class="btn-delete">×</button>
      </div>
      <div v-if="todos.length === 0" class="empty-state">
        No tasks yet. Add one above!
      </div>
    </div>
    <div v-if="todos.length > 0" class="todo-stats">
      {{ completedCount }} / {{ todos.length }} completed
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted, watch, nextTick } from 'vue'

export default {
  name: 'ToDoList',
  setup() {
    const todos = ref([])
    const newTodo = ref('')
    const editInput = ref(null)
    let nextId = 1

    // Format date like "2nd August"
    const formatDate = (dateString) => {
      if (!dateString) return ''
      const date = new Date(dateString)
      const day = date.getDate()
      const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
        'July', 'August', 'September', 'October', 'November', 'December']
      
      // Get ordinal suffix (1st, 2nd, 3rd, 4th, etc.)
      const getOrdinalSuffix = (n) => {
        const s = ['th', 'st', 'nd', 'rd']
        const v = n % 100
        return n + (s[(v - 20) % 10] || s[v] || s[0])
      }
      
      return `${getOrdinalSuffix(day)} ${monthNames[date.getMonth()]}`
    }

    // Load todos from localStorage
    const loadTodos = () => {
      const saved = localStorage.getItem('pomodoro-todos')
      if (saved) {
        try {
          todos.value = JSON.parse(saved)
          // Add date to todos that don't have one (backward compatibility)
          todos.value.forEach(todo => {
            if (!todo.date) {
              todo.date = new Date().toISOString()
            }
          })
          // Find max ID
          if (todos.value.length > 0) {
            nextId = Math.max(...todos.value.map(t => t.id || 0)) + 1
          }
          saveTodos() // Save updated todos with dates
        } catch (e) {
          console.error('Error loading todos:', e)
        }
      }
    }

    // Save todos to localStorage
    const saveTodos = () => {
      localStorage.setItem('pomodoro-todos', JSON.stringify(todos.value))
    }

    const addTodo = () => {
      if (newTodo.value.trim()) {
        todos.value.push({
          id: nextId++,
          text: newTodo.value.trim(),
          completed: false,
          editing: false,
          date: new Date().toISOString()
        })
        newTodo.value = ''
        saveTodos()
      }
    }

    const deleteTodo = (index) => {
      todos.value.splice(index, 1)
      saveTodos()
    }

    const startEditing = (todo) => {
      todo.editing = true
      nextTick(() => {
        if (editInput.value && Array.isArray(editInput.value)) {
          const input = editInput.value.find(el => el)
          if (input) input.focus()
        }
      })
    }

    const finishEditing = (todo) => {
      if (todo.text.trim()) {
        todo.editing = false
        saveTodos()
      } else {
        // If empty, delete the todo
        const index = todos.value.findIndex(t => t.id === todo.id)
        if (index !== -1) {
          deleteTodo(index)
        }
      }
    }

    const cancelEditing = (todo) => {
      todo.editing = false
      loadTodos() // Reload to restore original text
    }

    const completedCount = computed(() => {
      return todos.value.filter(t => t.completed).length
    })

    // Auto-save when todos change
    watch(todos, () => {
      saveTodos()
    }, { deep: true })

    onMounted(() => {
      loadTodos()
    })

    return {
      todos,
      newTodo,
      editInput,
      completedCount,
      addTodo,
      deleteTodo,
      startEditing,
      finishEditing,
      cancelEditing,
      saveTodos,
      formatDate
    }
  }
}
</script>

<style scoped>
.todo-card {
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

.todo-input-container {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.todo-input {
  flex: 1;
  padding: 10px 14px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  font-size: 14px;
  transition: border-color 0.3s ease;
}

.todo-input:focus {
  outline: none;
  border-color: #667eea;
}

.btn-add {
  padding: 10px 20px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.3s ease;
}

.btn-add:hover {
  background: #5568d3;
}

.todo-list {
  flex: 1;
  overflow-y: auto;
  max-height: 400px;
}

.todo-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  margin-bottom: 8px;
  background: #f9fafb;
  border-radius: 8px;
  transition: background 0.2s ease;
}

.todo-date {
  font-size: 0.85em;
  color: #6b7280;
  white-space: nowrap;
  margin-left: auto;
  margin-right: 8px;
}

.todo-item:hover {
  background: #f3f4f6;
}

.todo-item.completed {
  opacity: 0.6;
}

.todo-checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: #667eea;
}

.todo-text {
  flex: 1;
  color: #1f2937;
  cursor: text;
  word-break: break-word;
}

.todo-item.completed .todo-text {
  text-decoration: line-through;
  color: #6b7280;
}

.todo-edit-input {
  flex: 1;
  padding: 6px 10px;
  border: 2px solid #667eea;
  border-radius: 6px;
  font-size: 14px;
  background: white;
}

.todo-edit-input:focus {
  outline: none;
}

.btn-delete {
  background: #ef4444;
  color: white;
  border: none;
  border-radius: 6px;
  width: 28px;
  height: 28px;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
  transition: background 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-delete:hover {
  background: #dc2626;
}

.empty-state {
  text-align: center;
  color: #9ca3af;
  padding: 40px 20px;
  font-style: italic;
}

.todo-stats {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #e5e7eb;
  color: #6b7280;
  font-size: 0.9em;
  text-align: center;
}
</style>

