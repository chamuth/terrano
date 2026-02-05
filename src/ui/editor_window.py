import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QDockWidget)
from PyQt6.QtCore import Qt, QTimer

from src.core.scene import TerrainEntity
from src.core.terrain_data import TerrainData
from src.ui.panels.hierarchy import HierarchyPanel
from src.ui.panels.inspector import InspectorPanel
from src.ui.viewport import TerrainViewport
from src.core.roads import RoadNetwork
from src.ui.terrain_worker import TerrainWorker

class EditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Terrano Editor")
        self.resize(1600, 900)
        self.setDockNestingEnabled(True)
        
        # Data Model
        self.root_terrain = TerrainEntity(size=1024)
        
        # We also need the raw TerrainData for the Viewport to render
        self.render_data = TerrainData(size=1024)
        self.road_net = RoadNetwork()
        
        # Threading
        self.terrain_worker = None
        self.pending_update = False
        
        # Debounce timer (wait for user to stop adjusting before regenerating)
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.reprocess_terrain)
        
        self.init_ui()
        
        # Connect Signals
        self.hierarchy.tree.itemClicked.connect(self.on_selection_changed)
        
        # Listen to entity changes to re-process terrain
        self.root_terrain.changed.connect(self.schedule_update)
        
        # Generate initial terrain
        self.reprocess_terrain()
    
    def init_ui(self):
        # 1. Viewport (Central)
        self.viewport = TerrainViewport(self.render_data, self.road_net)
        self.setCentralWidget(self.viewport)
        
        # 2. Hierarchy (Dock Left)
        self.dock_hierarchy = QDockWidget("Component Browser", self)
        self.hierarchy = HierarchyPanel(self.root_terrain)
        self.dock_hierarchy.setWidget(self.hierarchy)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_hierarchy)
        
        # 3. Inspector (Dock Right)
        self.dock_inspector = QDockWidget("Properties", self)
        self.inspector = InspectorPanel()
        self.dock_inspector.setWidget(self.inspector)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_inspector)
        
        # Set initial dock sizes
        self.dock_hierarchy.setMinimumWidth(300)
        self.dock_inspector.setMinimumWidth(350)

    def on_selection_changed(self, item, column):
        entity = item.data(0, Qt.ItemDataRole.UserRole)
        self.inspector.set_entity(entity)
        # Connect change signal of CURRENT entity to reprocess
        try:
            entity.changed.disconnect(self.schedule_update)
        except:
            pass
        entity.changed.connect(self.schedule_update)
    
    def schedule_update(self):
        """Debounce terrain updates - wait 300ms after last change"""
        self.update_timer.stop()
        self.update_timer.start(300)  # 300ms debounce

    def reprocess_terrain(self):
        """Generate terrain in background thread"""
        # Cancel existing worker if running
        if self.terrain_worker and self.terrain_worker.isRunning():
            self.terrain_worker.stop()
            self.terrain_worker.wait()
        
        # Start new worker
        self.terrain_worker = TerrainWorker(self.root_terrain)
        self.terrain_worker.finished.connect(self.on_terrain_generated)
        self.terrain_worker.start()
    
    def on_terrain_generated(self, heightmap):
        """Called when background terrain generation completes"""
        # Update render data
        self.render_data.heightmap[:] = heightmap
        
        # Update viewport
        self.viewport.update_mesh()
