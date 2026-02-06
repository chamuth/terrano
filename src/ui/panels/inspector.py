
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
            if not prop_data.get("visible", True):
                continue
                
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
                 widget = QLineEdit(str(val))
                 widget.textChanged.connect(lambda v, p=prop_name: self.update_prop(p, v))

            if widget:
                # Add label
                self.form_layout.addRow(prop_name, widget)
                # Register for in-place updates
                self.property_widgets[prop_name] = widget

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
