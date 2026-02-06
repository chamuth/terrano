
from PyQt6.QtCore import QThread, pyqtSignal
import numpy as np

class TerrainWorker(QThread):
    """Background worker thread for terrain generation"""
    finished = pyqtSignal(object, float)  # Emits (heightmap, terrain_size)
    
    def __init__(self, terrain_entity, parent=None):
        super().__init__(parent)
        self.terrain_entity = terrain_entity
        self.should_stop = False
        
    def run(self):
        """Generate terrain in background thread"""
        try:
            # Get terrain resolution (grid size)
            size_str = self.terrain_entity.get_property("Resolution")
            size = int(size_str) if size_str else 512

            # Get physical size (default 1000.0)
            phys_size = self.terrain_entity.get_property("Size")
            if phys_size is None or phys_size <= 0: phys_size = 1000.0
            
            # Create empty heightmap
            heightmap = np.zeros((size, size), dtype=np.float32)
            
            # Process terrain (this is the heavy computation)
            self.terrain_entity.process(heightmap, terrain_size=phys_size)
            
            # Emit result if not cancelled
            if not self.should_stop:
                self.finished.emit(heightmap, phys_size)
        except Exception as e:
            print(f"Terrain generation error: {e}")
    
    def stop(self):
        """Request thread to stop"""
        self.should_stop = True
