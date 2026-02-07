
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
import vispy.scene
from vispy.scene import visuals
import numpy as np

class HeightmapViewport(QWidget):
    def __init__(self, terrain_data, road_network=None, parent=None):
        super().__init__(parent)
        self.terrain_data = terrain_data
        self.mask_data = None # Store mask data for visualization
        
        # Vispy Canvas
        self.canvas = vispy.scene.SceneCanvas(keys='interactive', show=True, parent=self, bgcolor='#202020')
        self.view = self.canvas.central_widget.add_view()
        
        # 2D Camera
        self.view.camera = vispy.scene.cameras.PanZoomCamera(aspect=1)
        self.view.camera.set_range(x=(-50, 1050), y=(-50, 1050))
        
        # Layout
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
        
        
        
    def update_image(self):
        from src.core.backend import to_cpu

        # Vispy Image expects (H, W) or (H, W, 3/4)
        # TerrainData is (N, 3), we need to maintain a 2D grid representation
        # Assuming TerrainData might have raw buffer or we reshape
        
        # Check if terrain_data exposes a 2D grid directly
        if self.mask_data is not None:
             # Render Mask (ensure CPU)
             mask_cpu = to_cpu(self.mask_data)
             self.image.set_data(mask_cpu)
             self.image.clim = (0, 1)
             self.image.cmap = 'grays' # Black=0, White=1
             
        elif hasattr(self.terrain_data, 'heightmap'):
            # It's a 2D array of floats
            data = self.terrain_data.heightmap
            
            # Normalize for visualization if needed, or rely on clim
            # Vispy image handles float data, but cmap needs range
            
            # Rotate/Flip to match 3D view orientation (X/Z)
            # Usually heightmap[x, z] or [row, col]
            # Standard: Image (0,0) is top-left.
            # Terrain (0,0) is usually corner.
            
            # Ensure CPU
            data_cpu = to_cpu(data)
            self.image.set_data(data_cpu)
            
            # Set clim based on actual data range for better visibility?
            # Or keep fixed? Fixed is better for consistent editing.
            # But maybe adaptive texturing.
            self.image.clim = (-50, 250) # Increased range
            self.image.cmap = 'grays'
            
        self.canvas.update()
