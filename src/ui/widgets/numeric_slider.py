from PyQt6.QtWidgets import QWidget, QHBoxLayout, QSlider, QSpinBox, QDoubleSpinBox
from PyQt6.QtCore import Qt, pyqtSignal

class NumericSlider(QWidget):
    """
    A widget that combines a slider and a spinbox for numeric input.
    Supports both float and int values.
    """
    valueChanged = pyqtSignal(float) # Emits float, cast to int if needed by receiver
    
    def __init__(self, value=0, min_val=0, max_val=100, is_float=False, parent=None):
        super().__init__(parent)
        self.is_float = is_float
        self.min_val = min_val
        self.max_val = max_val
        self._block_signals = False
        
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(5)
        
        # Slider
        self.slider_resolution = 1000 if is_float else (max_val - min_val)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, self.slider_resolution)
        self.slider.valueChanged.connect(self.on_slider_changed)
        
        # SpinBox
        if is_float:
            self.spinbox = QDoubleSpinBox()
            self.spinbox.setDecimals(3)
            self.spinbox.setSingleStep(0.1) # Maybe dynamic based on range?
        else:
            self.spinbox = QSpinBox()
        
        self.spinbox.setRange(min_val, max_val)
        self.spinbox.setValue(value)
        self.spinbox.valueChanged.connect(self.on_spinbox_changed)
        
        # Layout
        self.layout.addWidget(self.slider)
        self.layout.addWidget(self.spinbox)
        self.setLayout(self.layout)
        
        # Initial sync
        self.update_slider_from_value(value)
        
    def on_slider_changed(self, slider_val):
        if self._block_signals: return
        
        # Map slider (0-res) to value (min-max)
        t = slider_val / self.slider_resolution
        val = self.min_val + t * (self.max_val - self.min_val)
        
        if not self.is_float:
            val = int(round(val))
            
        self._block_signals = True
        self.spinbox.setValue(val)
        self._block_signals = False
        
        self.valueChanged.emit(val)
        
    def on_spinbox_changed(self, val):
        if self._block_signals: return
        
        self._block_signals = True
        self.update_slider_from_value(val)
        self._block_signals = False
        
        self.valueChanged.emit(val)

    def update_slider_from_value(self, val):
        # Map value to slider
        if self.max_val == self.min_val:
            t = 0
        else:
            t = (val - self.min_val) / (self.max_val - self.min_val)
        
        slider_val = int(t * self.slider_resolution)
        self.slider.setValue(slider_val)
        
    def setValue(self, val):
        self._block_signals = True
        self.spinbox.setValue(val)
        self.update_slider_from_value(val)
        self._block_signals = False

    def value(self):
        return self.spinbox.value()
