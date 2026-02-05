
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox, 
                             QDoubleSpinBox, QCheckBox, QLabel, QScrollArea)
from PyQt6.QtCore import Qt

class InspectorPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
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
        self.current_entity = entity
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
        name_edit.textChanged.connect(lambda val: setattr(self.current_entity, 'name', val))
        self.form_layout.addRow("Name", name_edit)
        
        # Properties
        for prop_name, prop_data in self.current_entity.properties.items():
            dtype = prop_data["type"]
            val = prop_data["value"]
            
            widget = None
            
            if dtype == int:
                widget = QSpinBox()
                widget.setRange(prop_data.get("min", -9999), prop_data.get("max", 9999))
                widget.setValue(val)
                # Capture prop_name in closure (default arg trick)
                widget.valueChanged.connect(lambda v, p=prop_name: self.update_prop(p, v))
                
            elif dtype == float:
                widget = QDoubleSpinBox()
                widget.setRange(prop_data.get("min", -9999.0), prop_data.get("max", 9999.0))
                widget.setValue(val)
                widget.valueChanged.connect(lambda v, p=prop_name: self.update_prop(p, v))
                
            elif dtype == bool:
                widget = QCheckBox()
                widget.setChecked(val)
                widget.toggled.connect(lambda v, p=prop_name: self.update_prop(p, v))
                
            if widget:
                self.form_layout.addRow(prop_name, widget)

    def update_prop(self, name, value):
        if self.current_entity:
            self.current_entity.set_property(name, value)
