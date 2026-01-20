"""
Todo list management widget for Pomodoro app.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QListWidget, QListWidgetItem,
                             QCheckBox, QMessageBox, QDateEdit, QComboBox,
                             QDialog, QFormLayout, QDialogButtonBox)
from PyQt6.QtCore import QDate, Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from datetime import datetime
from database import Database
from models import Todo


class TodoEditDialog(QDialog):
    """Dialog for editing todo items."""
    
    def __init__(self, parent=None, todo: Todo = None):
        super().__init__(parent)
        self.todo = todo
        self.setWindowTitle("Edit Todo" if todo else "Add Todo")
        self.setMinimumSize(400, 300)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        form = QFormLayout()
        form.setSpacing(12)
        
        # Task input
        self.task_input = QLineEdit()
        if todo:
            self.task_input.setText(todo.task)
        self.task_input.setPlaceholderText("Enter task description...")
        form.addRow("Task:", self.task_input)
        
        # Date picker
        self.date_picker = QDateEdit()
        self.date_picker.setCalendarPopup(True)
        if todo:
            try:
                todo_date = datetime.strptime(todo.date, "%Y-%m-%d").date()
                self.date_picker.setDate(QDate.fromString(todo.date, "yyyy-MM-dd"))
            except:
                self.date_picker.setDate(QDate.currentDate())
        else:
            self.date_picker.setDate(QDate.currentDate())
        form.addRow("Date:", self.date_picker)
        
        # Priority
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Low", "Medium", "High"])
        if todo:
            self.priority_combo.setCurrentIndex(todo.priority - 1)
        else:
            self.priority_combo.setCurrentIndex(0)  # Default to Low
        form.addRow("Priority:", self.priority_combo)
        
        # Repeatable checkbox
        self.repeatable_check = QCheckBox()
        if todo:
            self.repeatable_check.setChecked(todo.is_repeatable)
        form.addRow("Repeatable:", self.repeatable_check)
        
        # Repeat type
        self.repeat_type_combo = QComboBox()
        self.repeat_type_combo.addItems(["Daily", "Weekly", "Monthly"])
        if todo and todo.repeat_type:
            repeat_map = {"daily": 0, "weekly": 1, "monthly": 2}
            self.repeat_type_combo.setCurrentIndex(repeat_map.get(todo.repeat_type.lower(), 0))
        self.repeat_type_combo.setEnabled(self.repeatable_check.isChecked())
        self.repeatable_check.toggled.connect(self.repeat_type_combo.setEnabled)
        form.addRow("Repeat Type:", self.repeat_type_combo)
        
        layout.addLayout(form)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def get_todo_data(self):
        """Get todo data from dialog."""
        priority_map = {"Low": 1, "Medium": 2, "High": 3}
        repeat_type_map = {"Daily": "daily", "Weekly": "weekly", "Monthly": "monthly"}
        
        return {
            'task': self.task_input.text().strip(),
            'date': self.date_picker.date().toPyDate().strftime("%Y-%m-%d"),
            'priority': priority_map[self.priority_combo.currentText()],
            'is_repeatable': self.repeatable_check.isChecked(),
            'repeat_type': repeat_type_map[self.repeat_type_combo.currentText()] if self.repeatable_check.isChecked() else ''
        }


class TodoListWidget(QWidget):
    """Todo list widget."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = Database()
        self._init_ui()
        self._load_todos()
        # Check for repeatable todos on startup
        self.db.handle_repeatable_todos()
        self._load_todos()
    
    def _init_ui(self):
        """Initialize the UI."""
        self.setStyleSheet("""
            QWidget {
                background-color: #f5f7fa;
            }
            QLineEdit {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 10px;
                font-size: 13px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #4CAF50;
                background-color: #f9fff9;
            }
            QDateEdit {
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px;
                background-color: white;
            }
            QDateEdit:focus {
                border-color: #4CAF50;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 8px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton#filterBtn {
                background-color: #2196F3;
            }
            QPushButton#filterBtn:hover {
                background-color: #0b7dda;
            }
            QPushButton#deleteBtn {
                background-color: #f44336;
            }
            QPushButton#deleteBtn:hover {
                background-color: #da190b;
            }
            QPushButton#editBtn {
                background-color: #ff9800;
            }
            QPushButton#editBtn:hover {
                background-color: #e68900;
            }
            QListWidget {
                border: none;
                background-color: transparent;
                padding: 5px;
            }
            QListWidget::item {
                margin: 6px 0px;
                min-height: 65px;
            }
            QListWidget::item:hover {
                background-color: transparent;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(25, 25, 25, 25)
        
        # Title
        title = QLabel("✅ Todo List")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #2c3e50; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Add todo section
        add_layout = QHBoxLayout()
        add_layout.setSpacing(10)
        
        self.todo_input = QLineEdit()
        self.todo_input.setPlaceholderText("Enter a new task...")
        self.todo_input.returnPressed.connect(self._quick_add_todo)
        add_layout.addWidget(self.todo_input)
        
        quick_add_button = QPushButton("➕ Quick Add")
        quick_add_button.clicked.connect(self._quick_add_todo)
        quick_add_button.setMinimumWidth(120)
        quick_add_button.setMinimumHeight(40)
        add_layout.addWidget(quick_add_button)
        
        add_full_button = QPushButton("➕ Add with Details")
        add_full_button.clicked.connect(self._add_todo_with_details)
        add_full_button.setMinimumWidth(150)
        add_full_button.setMinimumHeight(40)
        add_layout.addWidget(add_full_button)
        
        layout.addLayout(add_layout)
        
        # Filter buttons
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(10)
        
        all_button = QPushButton("📋 All")
        all_button.setObjectName("filterBtn")
        all_button.clicked.connect(lambda: self._filter_todos(None))
        all_button.setMinimumHeight(38)
        filter_layout.addWidget(all_button)
        
        today_button = QPushButton("📅 Today")
        today_button.setObjectName("filterBtn")
        today_button.clicked.connect(lambda: self._filter_todos(datetime.now().date()))
        today_button.setMinimumHeight(38)
        filter_layout.addWidget(today_button)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Todo list
        self.todo_list = QListWidget()
        self.todo_list.setSpacing(10)
        layout.addWidget(self.todo_list)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        edit_button = QPushButton("✏️ Edit Selected")
        edit_button.setObjectName("editBtn")
        edit_button.clicked.connect(self._edit_selected)
        edit_button.setMinimumWidth(140)
        edit_button.setMinimumHeight(40)
        button_layout.addWidget(edit_button)
        
        delete_button = QPushButton("🗑️ Delete Selected")
        delete_button.setObjectName("deleteBtn")
        delete_button.clicked.connect(self._delete_selected)
        delete_button.setMinimumWidth(150)
        delete_button.setMinimumHeight(40)
        button_layout.addWidget(delete_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _quick_add_todo(self):
        """Quick add todo with default settings."""
        task_text = self.todo_input.text().strip()
        if not task_text:
            return
        
        selected_date = QDate.currentDate()
        date_str = selected_date.toPyDate().strftime("%Y-%m-%d")
        
        self.db.add_todo(task_text, date_str, priority=1, is_repeatable=False)
        self.todo_input.clear()
        self._load_todos()
    
    def _add_todo_with_details(self):
        """Add todo with full details dialog."""
        dialog = TodoEditDialog(self)
        if dialog.exec():
            data = dialog.get_todo_data()
            self.db.add_todo(
                data['task'],
                data['date'],
                priority=data['priority'],
                is_repeatable=data['is_repeatable'],
                repeat_type=data['repeat_type']
            )
            self._load_todos()
    
    def _load_todos(self, filter_date=None):
        """Load todos from database."""
        self.todo_list.clear()
        
        if filter_date:
            date_str = filter_date.strftime("%Y-%m-%d")
            todos = self.db.get_todos(date_str)
        else:
            todos = self.db.get_todos()
        
        for todo_data in todos:
            todo = Todo.from_dict(todo_data)
            self._add_todo_item(todo)
    
    def _add_todo_item(self, todo: Todo):
        """Add a todo item to the list widget with improved styling."""
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, todo.id)
        
        # Priority colors - more vibrant
        priority_colors = {
            1: {"bg": "#e8f5e9", "border": "#4CAF50", "accent": "#66bb6a", "text": "#2e7d32", "emoji": "🟢"},
            2: {"bg": "#fff3e0", "border": "#ff9800", "accent": "#ffb74d", "text": "#e65100", "emoji": "🟠"},
            3: {"bg": "#ffebee", "border": "#f44336", "accent": "#ef5350", "text": "#c62828", "emoji": "🔴"}
        }
        
        colors = priority_colors.get(todo.priority, priority_colors[1])
        
        # Create widget for todo item - compact design
        widget = QWidget()
        
        # Main container - smaller and more compact
        widget.setStyleSheet(f"""
            QWidget {{
                background-color: {colors['bg']};
                border-radius: 12px;
                border-left: 4px solid {colors['border']};
                min-height: 60px;
            }}
        """)
        
        widget_layout = QHBoxLayout()
        widget_layout.setContentsMargins(12, 10, 12, 10)
        widget_layout.setSpacing(12)
        
        # Left side: Checkbox
        checkbox = QCheckBox()
        checkbox.setChecked(todo.completed)
        checkbox.setMinimumSize(22, 22)
        checkbox.setStyleSheet(f"""
            QCheckBox::indicator {{
                width: 22px;
                height: 22px;
                border-radius: 5px;
                border: 2px solid {colors['border']};
                background-color: white;
            }}
            QCheckBox::indicator:checked {{
                background-color: {colors['border']};
                border-color: {colors['border']};
            }}
            QCheckBox::indicator:hover {{
                border-color: {colors['accent']};
            }}
        """)
        checkbox.stateChanged.connect(
            lambda state, tid=todo.id: self._toggle_todo(tid, state == Qt.CheckState.Checked.value)
        )
        widget_layout.addWidget(checkbox)
        
        # Center: Task content - single line with emojis
        content_layout = QHBoxLayout()
        content_layout.setSpacing(12)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Task label - compact single line
        task_label = QLabel(todo.task)
        task_font = QFont()
        task_font.setPointSize(13)
        task_font.setBold(not todo.completed)
        task_label.setFont(task_font)
        if todo.completed:
            task_label.setStyleSheet("""
                text-decoration: line-through;
                color: #9e9e9e;
                opacity: 0.6;
            """)
        else:
            task_label.setStyleSheet(f"color: {colors['text']};")
        content_layout.addWidget(task_label, 1)  # Take available space
        
        # Combined emoji box - all emojis in one container
        emoji_container = QWidget()
        emoji_layout = QHBoxLayout()
        emoji_layout.setSpacing(8)
        emoji_layout.setContentsMargins(10, 6, 10, 6)
        
        emoji_text = ""
        tooltip_parts = []
        
        # Priority emoji
        priority_emoji = colors['emoji']
        priority_text = "Low Priority" if todo.priority == 1 else "Medium Priority" if todo.priority == 2 else "High Priority"
        emoji_text += priority_emoji + " "
        tooltip_parts.append(f"{priority_emoji} {priority_text}")
        
        # Date emoji
        try:
            todo_date = datetime.strptime(todo.date, "%Y-%m-%d").date()
            today = datetime.now().date()
            
            if todo_date == today:
                date_emoji = "📅"
                date_text = "Due Today"
            elif todo_date < today:
                date_emoji = "⚠️"
                days_overdue = (today - todo_date).days
                date_text = f"Overdue by {days_overdue} day{'s' if days_overdue > 1 else ''}"
            else:
                date_emoji = "📆"
                date_text = f"Due {todo_date.strftime('%b %d, %Y')}"
            
            emoji_text += date_emoji + " "
            tooltip_parts.append(f"{date_emoji} {date_text}")
        except:
            pass
        
        # Repeat emoji (if repeatable)
        if todo.is_repeatable:
            repeat_emojis = {"daily": "🔄", "weekly": "🔁", "monthly": "🔂"}
            repeat_emoji = repeat_emojis.get(todo.repeat_type.lower(), "🔄")
            repeat_text = f"Repeats {todo.repeat_type.capitalize()}"
            emoji_text += repeat_emoji
            tooltip_parts.append(f"{repeat_emoji} {repeat_text}")
        
        # Single label with all emojis
        emoji_label = QLabel(emoji_text.strip())
        emoji_label.setStyleSheet(f"""
            font-size: 16px;
            padding: 6px 12px;
            background-color: white;
            border-radius: 8px;
            border: 1px solid {colors['border']}40;
        """)
        emoji_label.setToolTip(" | ".join(tooltip_parts))
        emoji_layout.addWidget(emoji_label)
        
        emoji_container.setLayout(emoji_layout)
        content_layout.addWidget(emoji_container)
        
        widget_layout.addLayout(content_layout)
        
        widget.setLayout(widget_layout)
        
        # Set item size - compact
        item.setSizeHint(widget.sizeHint())
        size_hint = item.sizeHint()
        size_hint.setWidth(max(size_hint.width(), 600))
        size_hint.setHeight(max(size_hint.height(), 65))  # Much shorter - 65px
        item.setSizeHint(size_hint)
        
        self.todo_list.addItem(item)
        self.todo_list.setItemWidget(item, widget)
    
    def _toggle_todo(self, todo_id: int, completed: bool):
        """Toggle todo completion status."""
        self.db.update_todo(todo_id, completed=completed)
        # Handle repeatable todos
        if completed:
            self.db.handle_repeatable_todos()
        self._load_todos()
    
    def _edit_selected(self):
        """Edit selected todo item."""
        selected_items = self.todo_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a todo item to edit.")
            return
        
        if len(selected_items) > 1:
            QMessageBox.warning(self, "Multiple Selection", "Please select only one todo item to edit.")
            return
        
        item = selected_items[0]
        todo_id = item.data(Qt.ItemDataRole.UserRole)
        
        # Get todo from database
        todos = self.db.get_todos()
        todo_data = next((t for t in todos if t['id'] == todo_id), None)
        
        if todo_data:
            todo = Todo.from_dict(todo_data)
            dialog = TodoEditDialog(self, todo)
            if dialog.exec():
                data = dialog.get_todo_data()
                self.db.update_todo(
                    todo_id,
                    task=data['task'],
                    priority=data['priority'],
                    is_repeatable=data['is_repeatable'],
                    repeat_type=data['repeat_type']
                )
                # Update date if changed
                if data['date'] != todo.date:
                    # For date change, we'd need to delete and recreate or add a method
                    # For now, just update other fields
                    pass
                self._load_todos()
    
    def _delete_selected(self):
        """Delete selected todo items."""
        selected_items = self.todo_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "No Selection", "Please select a todo item to delete.")
            return
        
        reply = QMessageBox.question(
            self, "Delete Todo",
            f"Are you sure you want to delete {len(selected_items)} todo item(s)?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for item in selected_items:
                todo_id = item.data(Qt.ItemDataRole.UserRole)
                self.db.delete_todo(todo_id)
            self._load_todos()
    
    def _filter_todos(self, filter_date):
        """Filter todos by date."""
        self._load_todos(filter_date)
