
from PyQt6.QtCore import QThread, pyqtSignal
import numpy as np

class TerrainWorker(QThread):
    """Background worker thread for terrain generation"""
    finished = pyqtSignal(np.ndarray)  # Emits the generated heightmap
    
    def __init__(self, terrain_entity, parent=None):
        super().__init__(parent)
        self.terrain_entity = terrain_entity
        self.should_stop = False
        
    def run(self):
        """Generate terrain in background thread"""
        try:
            # Get terrain size
            size = self.terrain_entity.get_property("Size")
            
            # Create empty heightmap
            heightmap = np.zeros((size, size), dtype=np.float32)
            
            # Process terrain (this is the heavy computation)
            self.terrain_entity.process(heightmap)
            
            # Emit result if not cancelled
            if not self.should_stop:
                self.finished.emit(heightmap)
        except Exception as e:
            print(f"Terrain generation error: {e}")
    
    def stop(self):
        """Request thread to stop"""
        self.should_stop = True
