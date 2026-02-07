
from PyQt6.QtCore import QThread, pyqtSignal
import numpy as np

class TerrainWorker(QThread):
    """Background worker thread for terrain generation"""
    finished = pyqtSignal(object, float, float)  # Emits (heightmap, terrain_size, elapsed_time)
    
    def __init__(self, terrain_entity, parent=None):
        super().__init__(parent)
        self.terrain_entity = terrain_entity
        self.should_stop = False
        
    def run(self):
        """Generate terrain in background thread"""
        from src.core.backend import to_cpu, xp
        import time
        try:
            start_time = time.perf_counter()
            
            # Get terrain resolution (grid size)
            size_str = self.terrain_entity.get_property("Resolution")
            try:
                size = int(size_str) if size_str else 512
            except ValueError:
                size = 512

            # Get physical size (default 1000.0)
            phys_size = self.terrain_entity.get_property("Size")
            if phys_size is None or phys_size <= 0: phys_size = 1000.0
            
            # Create empty heightmap on device
            initial_heightmap = xp.zeros((size, size), dtype=xp.float32)
            
            # Process terrain (this is the heavy computation)
            # New functional signature with caching
            heightmap, _ = self.terrain_entity.process(initial_heightmap, terrain_size=phys_size, input_version="ROOT")
            
            # Ensure data is on CPU for UI (and synchronize)
            heightmap_cpu = to_cpu(heightmap)
            
            elapsed_time = time.perf_counter() - start_time
            
            # Emit result if not cancelled
            if not self.should_stop:
                self.finished.emit(heightmap_cpu, phys_size, elapsed_time)
        except Exception as e:
            print(f"Terrain generation error: {e}")
            import traceback
            traceback.print_exc()
    
    def stop(self):
        """Request thread to stop"""
        self.should_stop = True
