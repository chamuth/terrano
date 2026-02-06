import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QDockWidget, QStatusBar, QLabel, QProgressBar, QWidget,
                             QMenuBar, QMenu, QInputDialog, QMessageBox, QDialog, QListWidget, QDialogButtonBox, QVBoxLayout, QPushButton)
from PyQt6.QtCore import Qt, QTimer, QSettings
from PyQt6.QtGui import QAction, QUndoStack, QKeySequence

from src.core.scene import TerrainEntity
from src.core.terrain_data import TerrainData
from src.ui.panels.hierarchy import HierarchyPanel
from src.ui.panels.inspector import InspectorPanel
from src.ui.viewport import TerrainViewport
from src.ui.heightmap_viewport import HeightmapViewport
from src.core.roads import RoadNetwork
from src.ui.terrain_worker import TerrainWorker

class EditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Terrano")
        self.resize(1920, 900)
        # Enable Tabbed Docks (and keep nested/animated)
        self.setDockOptions(self.dockOptions() | 
                            QMainWindow.DockOption.AllowNestedDocks | 
                            QMainWindow.DockOption.AllowTabbedDocks |
                            QMainWindow.DockOption.AnimatedDocks)
        # Data Persistence
        self.settings = QSettings("SleekSoft", "TerranoEditor")
        
        # Data Model
        self.root_terrain = TerrainEntity()
        
        # We also need the raw TerrainData for the Viewport to render
        self.render_data = TerrainData(size=1024)
        self.road_net = RoadNetwork()
        
        # Undo Stack
        self.undo_stack = QUndoStack(self)
        
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
        # 1. Dock Viewports (No Central Widget)
        self.setCentralWidget(QWidget()) # Dummy central widget, or None if allowing docks to fill
        # Ideally, we want Docks to take up space. 
        # Using a dummy central widget with 0 size often helps QMainWindow logic.
        self.centralWidget().hide() # Hide it so docks fill space
        self.setDockNestingEnabled(True)

        # 3D Viewport Dock
        self.dock_viewport_3d = QDockWidget("3D Scene", self)
        self.dock_viewport_3d.setObjectName("Viewport3D")
        self.viewport_3d = TerrainViewport(self.render_data, self.road_net)
        self.dock_viewport_3d.setWidget(self.viewport_3d)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self.dock_viewport_3d)
        
        # 2D Viewport Dock
        self.dock_viewport_2d = QDockWidget("2D Heightmap", self)
        self.dock_viewport_2d.setObjectName("Viewport2D")
        self.viewport_2d = HeightmapViewport(self.render_data)
        self.dock_viewport_2d.setWidget(self.viewport_2d)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self.dock_viewport_2d)
        
        # Split them side-by-side
        self.splitDockWidget(self.dock_viewport_3d, self.dock_viewport_2d, Qt.Orientation.Horizontal)
        
        # 2. Hierarchy (Dock Left)
        self.dock_hierarchy = QDockWidget("Component Browser", self)
        self.dock_hierarchy.setObjectName("Hierarchy")
        self.hierarchy = HierarchyPanel(self.root_terrain, self.undo_stack)
        self.dock_hierarchy.setWidget(self.hierarchy)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_hierarchy)
        
        # 3. Inspector (Dock Right)
        self.dock_inspector = QDockWidget("Properties", self)
        self.dock_inspector.setObjectName("Inspector")
        self.inspector = InspectorPanel(self.undo_stack)
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

        # 5. Menu Bar
        self.create_menu_bar()

        # 6. Restore Session
        state = self.settings.value("window/state")
        geom = self.settings.value("window/geometry")
        if state and geom:
            self.restoreState(state)
            self.restoreGeometry(geom)

    def create_menu_bar(self):
        menu_bar = self.menuBar()
        # Reduce padding to resemble standard Windows desktop apps (compact)
        menu_bar.setStyleSheet("""
            QMenuBar {
                background-color: #303030;
                color: #e0e0e0;
                border-bottom: 1px solid #404040;
            }
            QMenuBar::item {
                spacing: 3px; 
                padding: 4px 8px;
                background: transparent;
                border-radius: 4px;
            }
            QMenuBar::item:selected { 
                background-color: #454545;
            }
            QMenu {
                background-color: #303030;
                color: #e0e0e0;
                border: 1px solid #505050;
            }
            QMenu::item {
                padding: 4px 20px 4px 20px;
            }
            QMenu::item:selected {
                background-color: #3daee9;
                color: #ffffff;
            }
        """)
        
        # -- File Menu --
        file_menu = menu_bar.addMenu("&File")
        exit_action = QAction("E&xit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # -- Edit Menu --
        edit_menu = menu_bar.addMenu("&Edit")
        
        undo_action = self.undo_stack.createUndoAction(self, "&Undo")
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        edit_menu.addAction(undo_action)
        
        redo_action = self.undo_stack.createRedoAction(self, "&Redo")
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        edit_menu.addAction(QAction("Preferences...", self, enabled=False))
        
        # -- Window Menu --
        self.window_menu = menu_bar.addMenu("&Window")
        self.update_window_menu()
        self.window_menu.aboutToShow.connect(self.update_window_menu)
        
        # -- Help Menu --
        help_menu = menu_bar.addMenu("&Help")
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def update_window_menu(self):
        self.window_menu.clear()
        
        # 1. Dock Visibility Toggles
        docks = [self.dock_viewport_3d, self.dock_viewport_2d, self.dock_hierarchy, self.dock_inspector]
        for dock in docks:
            action = dock.toggleViewAction()
            self.window_menu.addAction(action)
            
        self.window_menu.addSeparator()
        
        # 2. Layout Management Actions
        save_layout_action = QAction("Save Layout As...", self)
        save_layout_action.triggered.connect(self.save_layout_dialog)
        self.window_menu.addAction(save_layout_action)
        
        manage_action = QAction("Manage Layouts...", self)
        manage_action.triggered.connect(self.manage_layouts_dialog)
        self.window_menu.addAction(manage_action)
        
        self.window_menu.addSeparator()
        self.window_menu.addAction(QAction("Switch Layout:", self, enabled=False))
        
        # 3. List Existing Layouts
        layouts = self.settings.value("layouts/list", [], type=list)
        # Ensure it's a list (QSettings can return different types if empty)
        if not isinstance(layouts, list): layouts = []
        
        for name in layouts:
            # We use a closure or partial to capture 'name'
            action = QAction(name, self)
            action.triggered.connect(lambda checked, n=name: self.load_layout(n))
            self.window_menu.addAction(action)

        # Add Default Reset
        self.window_menu.addSeparator()
        reset_action = QAction("Reset to Default", self)
        # We don't have a hardcoded default restore yet, but we could implement one.
        # For now, maybe just "Restore Last Saved" logic? 
        # Or better, just let users save their own.
        
    def save_layout_dialog(self):
        name, ok = QInputDialog.getText(self, "Save Layout", "Layout Name:")
        if ok and name:
            self.save_layout(name)
            
    def save_layout(self, name):
        # 1. Update List
        layouts = self.settings.value("layouts/list", [], type=list)
        if not isinstance(layouts, list): layouts = []
        
        if name not in layouts:
            layouts.append(name)
            self.settings.setValue("layouts/list", layouts)
            
        # 2. Save State
        self.settings.setValue(f"layouts/{name}/state", self.saveState())
        self.settings.setValue(f"layouts/{name}/geometry", self.saveGeometry())
        
        self.status_label.setText(f"Layout '{name}' saved.")
        
    def load_layout(self, name):
        state = self.settings.value(f"layouts/{name}/state")
        geom = self.settings.value(f"layouts/{name}/geometry")
        
        if state and geom:
            self.restoreState(state)
            self.restoreGeometry(geom)
            self.status_label.setText(f"Layout '{name}' loaded.")
        else:
            self.status_label.setText(f"Error loading layout '{name}'.")

    def manage_layouts_dialog(self):
        dialog = ManageLayoutsDialog(self.settings, self)
        dialog.exec()
        # Refresh menu handled by aboutToShow
        
    def show_about(self):
        QMessageBox.about(self, "About Terrano", "Terrano Editor\n\nA modern terrain generation tool.")


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
            if hasattr(self.viewport_3d, 'set_data'):
                self.viewport_3d.set_data(self.render_data)
                
            self.viewport_2d.set_data(self.render_data)

        # Update render data content
        self.render_data.heightmap[:] = heightmap
        
        # Update viewports
        self.viewport_3d.update_mesh()
        self.viewport_2d.update_image()
        
        # UI Feedback
        self.status_label.setText("Ready")
        self.progress_bar.setVisible(False)

    def closeEvent(self, event):
        # Save Session State
        self.settings.setValue("window/state", self.saveState())
        self.settings.setValue("window/geometry", self.saveGeometry())
        event.accept()

class ManageLayoutsDialog(QDialog):
    def __init__(self, settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manage Layouts")
        self.settings = settings
        self.resize(300, 250)
        
        layout = QVBoxLayout()
        
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        
        self.refresh_list()
        
        # Buttons
        btn_rename = QPushButton("Rename")
        btn_rename.clicked.connect(self.rename_layout)
        layout.addWidget(btn_rename)
        
        btn_delete = QPushButton("Delete")
        btn_delete.clicked.connect(self.delete_layout)
        layout.addWidget(btn_delete)
        
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)
        
        self.setLayout(layout)
        
    def refresh_list(self):
        self.list_widget.clear()
        layouts = self.settings.value("layouts/list", [], type=list)
        if not isinstance(layouts, list): layouts = []
        self.list_widget.addItems(layouts)
        
    def delete_layout(self):
        item = self.list_widget.currentItem()
        if not item: return
        
        name = item.text()
        confirm = QMessageBox.question(self, "Confirm Delete", f"Delete layout '{name}'?", 
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if confirm == QMessageBox.StandardButton.Yes:
            # Remove from list
            layouts = self.settings.value("layouts/list", [], type=list)
            if not isinstance(layouts, list): layouts = []
            
            if name in layouts:
                layouts.remove(name)
                self.settings.setValue("layouts/list", layouts)
                
            # Remove keys (optional, but clean)
            self.settings.remove(f"layouts/{name}")
            
            self.refresh_list()

    def rename_layout(self):
        item = self.list_widget.currentItem()
        if not item: return
        
        old_name = item.text()
        new_name, ok = QInputDialog.getText(self, "Rename Layout", "New Name:", text=old_name)
        
        if ok and new_name and new_name != old_name:
            # Update List
            layouts = self.settings.value("layouts/list", [], type=list)
            if not isinstance(layouts, list): layouts = []
            
            if old_name in layouts:
                idx = layouts.index(old_name)
                layouts[idx] = new_name
                self.settings.setValue("layouts/list", layouts)
            
            # Move Data
            state = self.settings.value(f"layouts/{old_name}/state")
            geom = self.settings.value(f"layouts/{old_name}/geometry")
            
            self.settings.setValue(f"layouts/{new_name}/state", state)
            self.settings.setValue(f"layouts/{new_name}/geometry", geom)
            
            self.settings.remove(f"layouts/{old_name}")
            
            self.refresh_list()
