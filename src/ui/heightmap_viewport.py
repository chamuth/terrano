
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
import vispy.scene
from vispy.scene import visuals
import numpy as np

class HeightmapViewport(QWidget):
    def __init__(self, terrain_data, road_network=None, on_paint_callback=None, parent=None):
        super().__init__(parent)
        self.terrain_data = terrain_data
        self.mask_data = None # Store mask data for visualization
        self.on_paint_callback = on_paint_callback
        self.is_painting = False
        
        # Vispy Canvas
        self.canvas = vispy.scene.SceneCanvas(keys='interactive', show=True, parent=self, bgcolor='#202020')
        self.view = self.canvas.central_widget.add_view()
        
        # 2D Camera
        self.view.camera = vispy.scene.cameras.PanZoomCamera(aspect=1)
        self.view.camera.set_range(x=(-50, 1050), y=(-50, 1050))
        
        # Layout
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0) # Zero margins important for precise docking
        self.layout.addWidget(self.canvas.native)
        self.setLayout(self.layout)
        
        self.setMinimumSize(0, 0)
        
        # Image Visual (Foreground)
        # Interpolation: 'nearest' works well for heightmap pixel inspection, 'cubic' for smooth look
        self.image = visuals.Image(parent=self.view.scene, method='auto', interpolation='nearest', cmap='grays')
        
        # Status Label
        self.lbl_mask_status = QLabel("MASK VIEW", self)
        self.lbl_mask_status.setStyleSheet("color: white; font-weight: bold; background-color: rgba(0, 0, 0, 150); padding: 5px;")
        self.lbl_mask_status.move(10, 10)
        self.lbl_mask_status.hide()
        
        # Events
        self.canvas.events.mouse_press.connect(self.on_mouse_press)
        self.canvas.events.mouse_move.connect(self.on_mouse_move)
        self.canvas.events.mouse_release.connect(self.on_mouse_release)
        
        self.update_image()
    
    def set_data(self, terrain_data):
        self.terrain_data = terrain_data
        self.update_image()
        
    def set_mask(self, mask_data):
        self.mask_data = mask_data
        
        if self.mask_data is not None:
             self.lbl_mask_status.show()
             self.lbl_mask_status.raise_()
        else:
             self.lbl_mask_status.hide()
             
        self.update_image()
        
    def reset_camera(self):
        """Reset camera to fit the image"""
        if self.image._data is None:
            return
            
        h, w = self.image._data.shape[:2]
        # Margin
        margin = max(h, w) * 0.05
        self.view.camera.set_range(x=(-margin, w+margin), y=(-margin, h+margin))
        
    def get_world_pos(self, canvas_pos):
        """Map canvas pixels to world coordinates"""
        try:
             # Get the transform from canvas directly to the image visual
             tr = self.view.get_transform('canvas', self.image)
             local_pos = tr.map(list(canvas_pos))
             
             px, py = local_pos[0], local_pos[1]
             
             if self.image._data is None: return None
             h, w = self.image._data.shape[:2]
             
             # Normalize 0..1
             nx = px / w
             ny = py / h
             
             # Map to World
             scale = self.terrain_data.scale
             
             # World Coordinates are centered: [-scale/2, scale/2]
             # Image (0,0) (Top-Left?) maps to World (-scale/2, scale/2) (Top-Left)
             # Vispy Image Origin: Usually Bottom-Left (0,0) unless flipped.
             # Standard GL convention.
             # Let's assume standard normalization:
             
             wx = (nx - 0.5) * scale
             wz = (ny - 0.5) * scale # Z is Y in 2D view
             
             # Flip Y if necessary?
             # Usually Terrain XZ plane: Z increases downwards in grid? Or Upwards?
             # If Z increases "South", and Image Y increases "Up", we might need flip.
             # For now, assume consistent.
             
             return wx, wz
        except Exception:
             return None

    def on_mouse_press(self, event):
        if event.button == 1:
            wpos = self.get_world_pos(event.pos)
            if wpos and self.on_paint_callback:
                # Try to paint
                if self.on_paint_callback(wpos[0], wpos[1], 0):
                    self.is_painting = True
                    event.handled = True # Block camera
        
    def on_mouse_move(self, event):
        if self.is_painting:
            wpos = self.get_world_pos(event.pos)
            if wpos and self.on_paint_callback:
                self.on_paint_callback(wpos[0], wpos[1], 0)
            event.handled = True
            
    def on_mouse_release(self, event):
        if self.is_painting:
            self.is_painting = False
            event.handled = True
        
    def update_image(self):
        from src.core.backend import to_cpu

        # Vispy Image expects (H, W) or (H, W, 3/4)
        if self.mask_data is not None:
             # Render Mask (ensure CPU)
             mask_cpu = to_cpu(self.mask_data)
             self.image.set_data(mask_cpu)
             self.image.clim = (0, 1)
             self.image.cmap = 'grays' # Black=0, White=1
             
        elif hasattr(self.terrain_data, 'heightmap'):
            data = self.terrain_data.heightmap
            data_cpu = to_cpu(data)
            self.image.set_data(data_cpu)
            self.image.clim = (-50, 250)
            self.image.cmap = 'grays'
            
        self.canvas.update()
