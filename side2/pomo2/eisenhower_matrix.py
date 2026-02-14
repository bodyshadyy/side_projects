"""
Eisenhower Matrix widget for Pomodoro app.
4-quadrant task prioritization matrix.
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QListWidget, QListWidgetItem,
                             QCheckBox, QGridLayout, QFrame, QMessageBox,
                             QSizePolicy)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor
from database import Database


# Quadrant definitions
QUADRANTS = {
    1: {"title": "Do First", "subtitle": "Urgent & Important", "color": "#c62828", "bg": "#ffebee", "border": "#ef5350"},
    2: {"title": "Schedule", "subtitle": "Not Urgent & Important", "color": "#1565c0", "bg": "#e3f2fd", "border": "#42a5f5"},
    3: {"title": "Delegate", "subtitle": "Urgent & Not Important", "color": "#e65100", "bg": "#fff3e0", "border": "#ff9800"},
    4: {"title": "Eliminate", "subtitle": "Not Urgent & Not Important", "color": "#616161", "bg": "#f5f5f5", "border": "#9e9e9e"},
}


class TaskItemWidget(QWidget):
    """Custom widget for a task item in the list."""
    
    def __init__(self, task_id: int, task_text: str, completed: bool,
                 quadrant: int, parent_widget=None):
        super().__init__()
        self.task_id = task_id
        self.quadrant = quadrant
        self.parent_widget = parent_widget
        
        layout = QHBoxLayout()
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)
        
        # Checkbox
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(completed)
        self.checkbox.stateChanged.connect(self._on_toggle)
        layout.addWidget(self.checkbox)
        
        # Task label
        self.label = QLabel(task_text)
        self.label.setWordWrap(True)
        self.label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        if completed:
            self.label.setStyleSheet("text-decoration: line-through; color: #999;")
        else:
            self.label.setStyleSheet("color: #333;")
        layout.addWidget(self.label, stretch=1)
        
        # Delete button
        delete_btn = QPushButton("✕")
        delete_btn.setFixedSize(24, 24)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #999;
                border: none;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #f44336;
            }
        """)
        delete_btn.clicked.connect(self._on_delete)
        layout.addWidget(delete_btn)
        
        self.setLayout(layout)
    
    def _on_toggle(self, state):
        """Handle task completion toggle."""
        completed = state == 2  # Qt.CheckState.Checked
        db = Database()
        db.update_eisenhower_task(self.task_id, completed=completed)
        if completed:
            self.label.setStyleSheet("text-decoration: line-through; color: #999;")
        else:
            self.label.setStyleSheet("color: #333;")
    
    def _on_delete(self):
        """Handle task deletion."""
        db = Database()
        db.delete_eisenhower_task(self.task_id)
        if self.parent_widget:
            self.parent_widget.load_tasks()


class QuadrantWidget(QFrame):
    """Widget for a single quadrant of the Eisenhower matrix."""
    
    def __init__(self, quadrant: int, parent_matrix=None):
        super().__init__()
        self.quadrant = quadrant
        self.parent_matrix = parent_matrix
        self.db = Database()
        info = QUADRANTS[quadrant]
        
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet(f"""
            QuadrantWidget {{
                background-color: {info['bg']};
                border: 2px solid {info['border']};
                border-radius: 8px;
            }}
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Header
        header = QLabel(f"{info['title']}")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setStyleSheet(f"color: {info['color']}; border: none;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Subtitle
        subtitle = QLabel(info['subtitle'])
        subtitle_font = QFont()
        subtitle_font.setPointSize(9)
        subtitle.setFont(subtitle_font)
        subtitle.setStyleSheet(f"color: {info['color']}; opacity: 0.7; border: none;")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)
        
        # Task list
        self.task_list = QListWidget()
        self.task_list.setStyleSheet(f"""
            QListWidget {{
                background-color: white;
                border: 1px solid {info['border']};
                border-radius: 4px;
            }}
            QListWidget::item {{
                border-bottom: 1px solid #eee;
                padding: 2px;
            }}
        """)
        layout.addWidget(self.task_list, stretch=1)
        
        # Add task input row
        input_layout = QHBoxLayout()
        input_layout.setSpacing(6)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Add a task...")
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                padding: 6px 10px;
                border: 1px solid {info['border']};
                border-radius: 4px;
                background-color: white;
                color: #333;
            }}
            QLineEdit:focus {{
                border: 2px solid {info['color']};
            }}
        """)
        self.input_field.returnPressed.connect(self._add_task)
        input_layout.addWidget(self.input_field, stretch=1)
        
        add_btn = QPushButton("+")
        add_btn.setFixedSize(32, 32)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {info['color']};
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                opacity: 0.85;
            }}
        """)
        add_btn.clicked.connect(self._add_task)
        input_layout.addWidget(add_btn)
        
        layout.addLayout(input_layout)
        
        self.setLayout(layout)
        self.load_tasks()
    
    def _add_task(self):
        """Add a new task to this quadrant."""
        text = self.input_field.text().strip()
        if not text:
            return
        self.db.add_eisenhower_task(text, self.quadrant)
        self.input_field.clear()
        self.load_tasks()
    
    def load_tasks(self):
        """Load and display tasks for this quadrant."""
        self.task_list.clear()
        tasks = self.db.get_eisenhower_tasks(self.quadrant)
        for task in tasks:
            item = QListWidgetItem()
            widget = TaskItemWidget(
                task_id=task['id'],
                task_text=task['task'],
                completed=bool(task['completed']),
                quadrant=self.quadrant,
                parent_widget=self
            )
            item.setSizeHint(widget.sizeHint())
            self.task_list.addItem(item)
            self.task_list.setItemWidget(item, widget)


class EisenhowerMatrixWidget(QWidget):
    """Eisenhower Matrix widget with 4 quadrants."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI."""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # Title
        title = QLabel("Eisenhower Matrix")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #333;")
        main_layout.addWidget(title)
        
        # Axis labels row (top)
        top_label_layout = QHBoxLayout()
        top_label_layout.addStretch()
        urgent_label = QLabel("URGENT")
        urgent_label.setStyleSheet("color: #c62828; font-weight: bold; font-size: 11px;")
        urgent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_label_layout.addWidget(urgent_label)
        top_label_layout.addStretch()
        not_urgent_label = QLabel("NOT URGENT")
        not_urgent_label.setStyleSheet("color: #1565c0; font-weight: bold; font-size: 11px;")
        not_urgent_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_label_layout.addWidget(not_urgent_label)
        top_label_layout.addStretch()
        main_layout.addLayout(top_label_layout)
        
        # Grid with side labels
        content_layout = QHBoxLayout()
        
        # Left side labels
        side_label_layout = QVBoxLayout()
        imp_label = QLabel("I\nM\nP\nO\nR\nT\nA\nN\nT")
        imp_label.setStyleSheet("color: #2e7d32; font-weight: bold; font-size: 10px;")
        imp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        side_label_layout.addWidget(imp_label)
        not_imp_label = QLabel("N\nO\nT\n \nI\nM\nP")
        not_imp_label.setStyleSheet("color: #e65100; font-weight: bold; font-size: 10px;")
        not_imp_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        side_label_layout.addWidget(not_imp_label)
        content_layout.addLayout(side_label_layout)
        
        # 2x2 Grid of quadrants
        grid = QGridLayout()
        grid.setSpacing(8)
        
        # Q1: Urgent + Important (top-left)
        self.q1 = QuadrantWidget(1, self)
        grid.addWidget(self.q1, 0, 0)
        
        # Q2: Not Urgent + Important (top-right)
        self.q2 = QuadrantWidget(2, self)
        grid.addWidget(self.q2, 0, 1)
        
        # Q3: Urgent + Not Important (bottom-left)
        self.q3 = QuadrantWidget(3, self)
        grid.addWidget(self.q3, 1, 0)
        
        # Q4: Not Urgent + Not Important (bottom-right)
        self.q4 = QuadrantWidget(4, self)
        grid.addWidget(self.q4, 1, 1)
        
        content_layout.addLayout(grid, stretch=1)
        main_layout.addLayout(content_layout, stretch=1)
        
        self.setLayout(main_layout)
    
    def refresh(self):
        """Reload all quadrants."""
        self.q1.load_tasks()
        self.q2.load_tasks()
        self.q3.load_tasks()
        self.q4.load_tasks()


