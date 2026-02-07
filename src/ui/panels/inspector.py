
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox, 
                             QDoubleSpinBox, QCheckBox, QLabel, QScrollArea, QToolButton,
                             QHBoxLayout, QPushButton, QFileDialog)
from PyQt6.QtCore import Qt, QSize
import shutil
import os
from PyQt6.QtGui import QAction, QUndoStack, QKeySequence, QIcon

class CollapsibleGroup(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)

        # Toggle Button
        self.toggle_button = QToolButton()
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(True)
        # Style: Dark background, bold text
        self.toggle_button.setStyleSheet("""
            QToolButton { 
                border: none; 
                font-weight: bold; 
                text-align: left; 
                background-color: #353535; 
                color: #e0e0e0;
                padding: 6px; 
                border-radius: 4px;
                margin-bottom: 4px;
            } 
            QToolButton:hover { background-color: #404040; }
            QToolButton:checked { background-color: #454545; }
        """)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow)
        self.toggle_button.clicked.connect(self.on_toggle_click) # use clicked to toggle state manually if needed, but checkable works
        self.toggle_button.toggled.connect(self.on_toggle)
        self.toggle_button.setSizePolicy(self.toggle_button.sizePolicy().Policy.Expanding, self.toggle_button.sizePolicy().Policy.Fixed)

        self.content_area = QWidget()
        self.content_layout = QFormLayout()
        self.content_layout.setContentsMargins(8, 4, 4, 8) # Indent content
        self.content_area.setLayout(self.content_layout)
        
        self.layout.addWidget(self.toggle_button)
        self.layout.addWidget(self.content_area)
        
    def on_toggle_click(self):
        # QToolButton with ArrowType automatically handles checking if checkable
        pass

    def on_toggle(self, checked):
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
        # Animation could be added here
        self.content_area.setVisible(checked)
        
    def add_row(self, label, widget):
        self.content_layout.addRow(label, widget)
from src.core.commands import PropertyChangeCommand, RenameEntityCommand

class InspectorPanel(QWidget):
    def __init__(self, undo_stack, parent=None):
        super().__init__(parent)
        self.undo_stack = undo_stack
        self.current_entity = None
        
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0,0,0,0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.content_widget = QWidget()
        # Main layout for content is now VBox to stack groups
        self.scroll_layout = QVBoxLayout()
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.content_widget.setLayout(self.scroll_layout)
        self.scroll.setWidget(self.content_widget)
        
        self.main_layout.addWidget(self.scroll)
        self.setLayout(self.main_layout)

    def set_entity(self, entity):
        if self.current_entity:
             try:
                 self.current_entity.changed.disconnect(self.on_entity_changed)
             except:
                 pass
        
        self.current_entity = entity
        
        if self.current_entity:
            self.current_entity.changed.connect(self.on_entity_changed)
            
        self.build_ui()
    
    def on_entity_changed(self):
        # When entity changes (externally or via Undo), refresh UI
        # Check if structure changed (keys mismatch)
        if not self.current_entity:
             self.build_ui()
             return

        current_props = set()
        for pname, pdata in self.current_entity.properties.items():
             if pdata.get("visible", True):
                 current_props.add(pname)
                 
        existing_props = set(self.property_widgets.keys())
        
        # If structure matches, just update values (preserves focus)
        if current_props == existing_props:
            self.refresh_values()
        else:
            self.build_ui()

    def refresh_values(self):
        if not self.current_entity: return
        
        # Block signals to prevent feedback loops during update
        for prop_name, widget in self.property_widgets.items():
             if prop_name not in self.current_entity.properties: continue
             
             data = self.current_entity.properties[prop_name]
             val = data["value"]
             
             # Check type to access widget correctly
             # We need a standardized interface or isinstance checks
             # For now, let's assume we can set/get value generically or check types
             
             # Check if value actually changed (avoid resetting cursor/focus)
             current_widget_val = None
             
             # NumericSlider logic is consistent, but standard widgets vary
             if hasattr(widget, "value"): 
                 current_widget_val = widget.value()
             elif hasattr(widget, "text"):
                 current_widget_val = widget.text()
             elif hasattr(widget, "isChecked"):
                 current_widget_val = widget.isChecked()
             elif hasattr(widget, "currentText"): # ComboBox
                 current_widget_val = widget.currentText()
                 
             # Equality check (loose for string/numbers)
             if str(current_widget_val) == str(val):
                 continue
                 
             # Update
             try:
                 # block signals individually
                 was_blocked = widget.signalsBlocked()
                 widget.blockSignals(True)
                 
                 if hasattr(widget, "setValue"):
                     widget.setValue(val)
                 elif hasattr(widget, "setText"):
                     widget.setText(str(val))
                 elif hasattr(widget, "setChecked"):
                     widget.setChecked(val)
                 elif hasattr(widget, "setCurrentText"):
                     # ComboBox
                     # widget.setCurrentText(str(val)) # might not exist in old Qt?
                     # find index
                     idx = widget.findText(str(val))
                     if idx >= 0: widget.setCurrentIndex(idx)
                     
                 widget.blockSignals(was_blocked)
             except:
                 pass

    def build_ui(self):
        # Clear existing
        self.property_widgets = {} # Reset map
        
        # Clear main layout
        while self.scroll_layout.count():
            child = self.scroll_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        if not self.current_entity:
            self.scroll_layout.addWidget(QLabel("No Selection"))
            return
            
        # 1. Identification (Name) - Always active
        # Create a "General" group or Just put at top
        
        # Identity Container
        identity_group = QWidget()
        identity_layout = QFormLayout()
        identity_layout.setContentsMargins(4,4,4,10)
        identity_group.setLayout(identity_layout)
        
        # Name
        name_edit = QLineEdit(self.current_entity.name)
        # Use editingFinished to avoid spamming undo stack on every character
        name_edit.editingFinished.connect(lambda: self.push_rename(name_edit.text()))
        identity_layout.addRow("Name", name_edit)
        
        self.scroll_layout.addWidget(identity_group)
        
        # 2. Group Properties
        groups = {} # "GroupName" -> CollapsibleGroup
        
        # Pre-define order of common groups
        # Properties without group go to "Misc" or "General"? 
        # We defined default as "General"
        
        # Collect properties
        prop_list = []
        for prop_name, prop_data in self.current_entity.properties.items():
            if not prop_data.get("visible", True):
                continue
            prop_list.append((prop_name, prop_data))
            
        # We might want to sort properties? Or keep insertion order?
        # Dictionary is insertion ordered in Py3.7+
        
        for prop_name, prop_data in prop_list:
            group_name = prop_data.get("group", "General")
            
            # Create group if missing
            if group_name not in groups:
                 groups[group_name] = CollapsibleGroup(group_name)
            
            dtype = prop_data["type"]
            val = prop_data["value"]
            options = prop_data.get("options")
            
            widget = None
            
            # ... Widget Creation Logic (Simplified Copy) ...
            
            # Dropdown Support
            if options is not None:
                from PyQt6.QtWidgets import QComboBox
                widget = QComboBox()
                widget.addItems([str(opt) for opt in options])
                
                # Find current index
                current_text = str(val)
                index = widget.findText(current_text)
                if index >= 0:
                    widget.setCurrentIndex(index)
                    
                widget.currentTextChanged.connect(lambda v, p=prop_name: self.update_prop(p, v))
                
            elif dtype == int:
                from src.ui.widgets.numeric_slider import NumericSlider
                min_v = prop_data.get("min", -999999)
                max_v = prop_data.get("max", 999999)
                widget = NumericSlider(value=val, min_val=min_v, max_val=max_v, is_float=False)
                widget.valueChanged.connect(lambda v, p=prop_name: self.update_prop(p, v))
                
            elif dtype == float:
                from src.ui.widgets.numeric_slider import NumericSlider
                min_v = prop_data.get("min", -999999.0)
                max_v = prop_data.get("max", 999999.0)
                widget = NumericSlider(value=val, min_val=min_v, max_val=max_v, is_float=True)
                widget.valueChanged.connect(lambda v, p=prop_name: self.update_prop(p, v))
                
            elif dtype == bool:
                widget = QCheckBox()
                widget.setChecked(val)
                widget.toggled.connect(lambda v, p=prop_name: self.update_prop(p, v))
                
            elif dtype == str:
                 if prop_name == "Image Path":
                     # File Picker Widget
                     widget = QWidget()
                     h_layout = QHBoxLayout()
                     h_layout.setContentsMargins(0,0,0,0)
                     widget.setLayout(h_layout)
                     
                     line_edit = QLineEdit(str(val))
                     line_edit.textChanged.connect(lambda v, p=prop_name: self.update_prop(p, v))
                     
                     btn_browse = QToolButton()
                     btn_browse.setText("...")
                     btn_browse.clicked.connect(lambda _, le=line_edit, p=prop_name: self.browse_image(le, p))
                     
                     h_layout.addWidget(line_edit)
                     h_layout.addWidget(btn_browse)
                 else:
                     widget = QLineEdit(str(val))
                     widget.textChanged.connect(lambda v, p=prop_name: self.update_prop(p, v))

            if widget:
                # Add to Group
                groups[group_name].add_row(prop_name, widget)
                # Register for in-place updates
                self.property_widgets[prop_name] = widget

        # 3. Add Groups to Layout in specific order
        # "General" first, then others sorted
        sorted_keys = sorted(groups.keys(), key=lambda k: (0 if k == "General" else 1, k))
        
        for key in sorted_keys:
            self.scroll_layout.addWidget(groups[key])
            
        # Add Stretch to push everything up
        self.scroll_layout.addStretch()

    def browse_image(self, line_edit, prop_name):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Image", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if file_path:
            # Logic: Copy to 'assets' folder in project root
            # Assume project root is CWD for now (where main.py is)
            project_root = os.getcwd()
            assets_dir = os.path.join(project_root, "assets")
            
            if not os.path.exists(assets_dir):
                os.makedirs(assets_dir)
                
            filename = os.path.basename(file_path)
            dest_path = os.path.join(assets_dir, filename)
            
            try:
                shutil.copy2(file_path, dest_path)
                # Store relative path
                rel_path = os.path.join("assets", filename)
                
                line_edit.setText(rel_path)
                self.update_prop(prop_name, rel_path)
            except Exception as e:
                print(f"Error copying image: {e}")
                # Fallback to absolute
                line_edit.setText(file_path)
                self.update_prop(prop_name, file_path)

    def update_prop(self, name, value):
        if self.current_entity:
            # Need strict typing based on definition
            dtype = self.current_entity.properties[name]["type"]
            
            # Cast if necessary (especially for string inputs or combo box)
            try:
                if dtype == int:
                    value = int(value)
                elif dtype == float:
                    value = float(value)
            except:
                pass

            # self.current_entity.set_property(name, value)
            
            # Undo Logic
            old_val = self.current_entity.get_property(name)
            if old_val != value:
                cmd = PropertyChangeCommand(self.current_entity, name, value)
                self.undo_stack.push(cmd)
            
            # If the property change affects the structure or available properties (like Type change),
            # we might need to rebuild UI.
            # Simple heuristic: rebuild if "Type" changed
            if name == "Type":
                self.build_ui()

    def push_rename(self, new_name):
        if self.current_entity and self.current_entity.name != new_name:
            cmd = RenameEntityCommand(self.current_entity, new_name)
            self.undo_stack.push(cmd)
