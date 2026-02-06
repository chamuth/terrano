from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QPen

class QProgressIndicator(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.setFixedSize(20, 20)
        self.color = QColor("#3daee9")
        self.is_animated = False

    def rotate(self):
        self.angle = (self.angle + 30) % 360
        self.update()

    def startAnimation(self):
        self.is_animated = True
        self.timer.start(50) # 50ms interval - 20fps
        self.show()

    def stopAnimation(self):
        self.is_animated = False
        self.timer.stop()
        self.hide()

    def setAnimationDelay(self, delay):
        self.timer.setInterval(delay)

    def paintEvent(self, event):
        if not self.is_animated:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        width = self.width()
        height = self.height()
        outer_radius = (min(width, height) - 4.0) / 2.0
        inner_radius = outer_radius * 0.6
        capsule_height = outer_radius - inner_radius
        capsule_width = 2.0 if width > 32 else 1.5
        capsule_radius = capsule_width / 2.0

        for i in range(12):
            color = QColor(self.color)
            # Alpha fade trail
            # Current angle is at i=0 ideally? No, we rotate canvas.
            # Let's say we draw 12 lines.
            
            # Simple approach: draw lines with varying alpha depending on index vs angle
            alpha = 255 - (i * 20)
            if alpha < 0: alpha = 0
            
            # We want the "head" to be at self.angle
            
            painter.setPen(Qt.PenStyle.NoPen)
            color.setAlpha(alpha)
            painter.setBrush(color)
            
            painter.save()
            painter.translate(width / 2.0, height / 2.0)
            # Rotate to match current animation step + spoke index
            # Negative because we want clockwise visual but loop is 0..11
            painter.rotate(self.angle - (i * 30.0))
            
            painter.translate(inner_radius + capsule_height / 2.0, 0)
            
            # Draw rounded rect/capsule
            painter.drawRoundedRect(
                int(-capsule_height / 2.0), 
                int(-capsule_width / 2.0), 
                int(capsule_height), 
                int(capsule_width), 
                capsule_radius, 
                capsule_radius
            )
            
            painter.restore()
