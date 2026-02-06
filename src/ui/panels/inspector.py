
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox, 
                             QDoubleSpinBox, QCheckBox, QLabel, QScrollArea)
from PyQt6.QtCore import Qt
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
        self.form_layout = QFormLayout()
        self.content_widget.setLayout(self.form_layout)
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
        # To avoid loops with internal changes, we could potentially block signals
        # or check values. But build_ui clears everything.
        # Ideally we just update values, but rebuilding is robust.
        # Optimization: Check if focus is in one of our widgets?
        self.build_ui()
        
    def build_ui(self):
        # Clear existing
        while self.form_layout.count():
            child = self.form_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        if not self.current_entity:
            self.form_layout.addRow(QLabel("No Selection"))
            return
            
        # Name
        name_edit = QLineEdit(self.current_entity.name)
        # Use editingFinished to avoid spamming undo stack on every character
        name_edit.editingFinished.connect(lambda: self.push_rename(name_edit.text()))
        self.form_layout.addRow("Name", name_edit)
        
        
        # Properties
        for prop_name, prop_data in self.current_entity.properties.items():
            dtype = prop_data["type"]
            val = prop_data["value"]
            options = prop_data.get("options")
            
            widget = None
            
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
                widget = QSpinBox()
                widget.setRange(prop_data.get("min", -999999), prop_data.get("max", 999999))
                widget.setValue(val)
                widget.valueChanged.connect(lambda v, p=prop_name: self.update_prop(p, v))
                
            elif dtype == float:
                widget = QDoubleSpinBox()
                widget.setRange(prop_data.get("min", -999999.0), prop_data.get("max", 999999.0))
                widget.setValue(val)
                widget.setSingleStep(0.1)
                widget.valueChanged.connect(lambda v, p=prop_name: self.update_prop(p, v))
                
            elif dtype == bool:
                widget = QCheckBox()
                widget.setChecked(val)
                widget.toggled.connect(lambda v, p=prop_name: self.update_prop(p, v))
                
            elif dtype == str:
                 widget = QLineEdit(str(val))
                 widget.textChanged.connect(lambda v, p=prop_name: self.update_prop(p, v))

            if widget:
                # Add label
                self.form_layout.addRow(prop_name, widget)

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
