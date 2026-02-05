import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QDockWidget, QStatusBar, QLabel, QProgressBar, QWidget)
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
        self.root_terrain = TerrainEntity()
        
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
        
        # Listen to entity structure changes (add/remove/reorder)
        # We assume the HierarchyPanel emits structure_changed on the root for Drag/Drop
        # But we also need to catch additions/removals if they happen elsewhere?
        # For now, HierarchyPanel actions trigger root.structure_changed.
        self.root_terrain.structure_changed.connect(self.schedule_update)
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
        
        # 4. Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label)
        
        # Progress Bar next to label
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) # Indeterminate
        self.progress_bar.setFixedWidth(250)
        self.progress_bar.setVisible(False)
        
        # Style it to be visible (Blue chunk)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bbb;
                border-radius: 3px;
                text-align: center;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #3daee9;
                width: 20px;
            }
        """)
        
        self.status_bar.addWidget(self.progress_bar)
        
        # Set initial dock sizes
        self.dock_hierarchy.setMinimumWidth(300)
        self.dock_inspector.setMinimumWidth(350)

    # ... on_selection_changed, schedule_update ...

    def on_selection_changed(self, item, column):
        # The HierarchyPanel now stores IDs, not objects.
        # Use helper method to retrieve the entity.
        entity = self.hierarchy.get_entity_from_item(item)
        if not entity: return
        
        self.inspector.set_entity(entity)
        
        # We need to listen to changes on ANY selected entity to update the view
        try:
            entity.changed.disconnect(self.schedule_update)
        except:
            pass # Was not connected
            
        entity.changed.connect(self.schedule_update)
    
    def schedule_update(self):
        """Debounce terrain updates - wait 300ms after last change"""
        # Also update hierarchy visual for the changed entity if needed
        if self.inspector.current_entity:
             # Find item for this entity
             ent = self.inspector.current_entity
             if ent.id in self.hierarchy.items_map:
                 item = self.hierarchy.items_map[ent.id]
                 self.hierarchy.update_item_style(item, ent)
        
        self.update_timer.stop()
        self.update_timer.start(300)  # 300ms debounce

    def reprocess_terrain(self):
        """Generate terrain in background thread"""
        # Cancel existing worker if running
        if self.terrain_worker and self.terrain_worker.isRunning():
            self.terrain_worker.stop()
            self.terrain_worker.wait()
        
        # UI Feedback
        self.status_label.setText("Generating Terrain...")
        self.progress_bar.setVisible(True)
        
        # Start new worker
        self.terrain_worker = TerrainWorker(self.root_terrain)
        self.terrain_worker.finished.connect(self.on_terrain_generated)
        self.terrain_worker.start()
    
    def on_terrain_generated(self, heightmap):
        """Called when background terrain generation completes"""
        
        # Check if resolution changed
        if self.render_data.heightmap.shape != heightmap.shape:
            # Re-initialize render data with new size
            current_scale = self.render_data.scale
            new_size = heightmap.shape[0]
            
            # Create new container
            self.render_data = TerrainData(size=new_size, scale=current_scale)
            
            # Update viewport reference
            if hasattr(self.viewport, 'set_data'):
                self.viewport.set_data(self.render_data)
            else:
                self.viewport.terrain_data = self.render_data

        # Update render data content
        self.render_data.heightmap[:] = heightmap
        
        # Update viewport mesh
        self.viewport.update_mesh()
        
        # UI Feedback
        self.status_label.setText("Ready")
        self.progress_bar.setVisible(False)
