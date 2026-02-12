import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QDockWidget, QStatusBar, QLabel, QProgressBar, QWidget,
                             QMenuBar, QMenu, QInputDialog, QMessageBox, QDialog, QListWidget, QDialogButtonBox, QVBoxLayout, QPushButton)
from PyQt6.QtCore import Qt, QTimer, QSettings
from PyQt6.QtGui import QAction, QUndoStack, QKeySequence

from src.core.scene import TerrainEntity
from src.core.terrain_data import TerrainData
from src.ui.panels.hierarchy import HierarchyPanel
from src.ui.panels.inspector import InspectorPanel
from src.ui.panels.export import ExportPanel
from src.ui.viewport import TerrainViewport
from src.ui.heightmap_viewport import HeightmapViewport
from src.core.roads import RoadNetwork
from src.ui.terrain_worker import TerrainWorker
from src.ui.panels.resources import ResourcesPanel
from src.ui.terrain_worker import TerrainWorker
from src.ui.widgets.progress_indicator import QProgressIndicator
from src.core.project import ProjectManager
from src.core.scene import EntityType
from PyQt6.QtWidgets import QFileDialog

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
        self.render_data = TerrainData(size=512)
        self.road_net = RoadNetwork()
        
        # Project Management
        self.project_manager = ProjectManager()
        
        # Undo Stack
        self.undo_stack = QUndoStack(self)
        
        # Threading
        self.terrain_worker = None
        self.pending_update = False
        self.initial_fit_done = False
        
        # Debounce timer (wait for user to stop adjusting before regenerating)
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.reprocess_terrain)
        
        # Draw Mode State
        self.is_drawing_mode = False
        
        self.init_ui()
        
        # Connect Signals
        # Use itemSelectionChanged to capture programmatic changes (Undo/Redo) too
        self.hierarchy.tree.itemSelectionChanged.connect(self.on_selection_changed)
        
        # Listen to entity structure changes (add/remove/reorder)
        # We assume the HierarchyPanel emits structure_changed on the root for Drag/Drop
        # But we also need to catch additions/removals if they happen elsewhere?
        # For now, HierarchyPanel actions trigger root.structure_changed.
        self.root_terrain.structure_changed.connect(self.schedule_update)
        # Also mark project as dirty when structure changes
        self.root_terrain.structure_changed.connect(self.mark_dirty)
        
        self.root_terrain.changed.connect(self.schedule_update)
        # Also mark dirty on property changes
        self.root_terrain.changed.connect(self.mark_dirty)
        
        # Also need to listen to undo stack for changes?
        # Undo/Redo modifies scene -> triggers signals -> marks dirty.
        # But we could also just mark dirty on any undo stack change if simpler.
        # Actually signals are safer.
        
        self.update_title()
        
        # Connect mesh stats
        self.viewport_3d.mesh_stats_changed.connect(self.update_mesh_stats)
        
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
        self.viewport_3d = TerrainViewport(self.render_data, self.road_net, on_paint_callback=self.on_paint)
        self.dock_viewport_3d.setWidget(self.viewport_3d)
        self.dock_viewport_3d.setMinimumSize(0, 0)
        self.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea, self.dock_viewport_3d)
        
        # 2D Viewport Dock
        self.dock_viewport_2d = QDockWidget("2D Heightmap", self)
        self.dock_viewport_2d.setObjectName("Viewport2D")
        # Ensure HeightmapViewport accepts callback (Update class separately)
        try:
             self.viewport_2d = HeightmapViewport(self.render_data, on_paint_callback=self.on_paint)
        except TypeError:
             self.viewport_2d = HeightmapViewport(self.render_data)

        self.dock_viewport_2d.setWidget(self.viewport_2d)
        self.dock_viewport_2d.setMinimumSize(0, 0)
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
        # Pass resource_manager and EDITOR reference
        self.inspector = InspectorPanel(self.undo_stack, resource_manager=self.project_manager.resource_manager, editor_window=self)
        self.inspector.save_preset_callback = self.on_save_preset # Callback
        self.dock_inspector.setWidget(self.inspector)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_inspector)
        
        # 3b. Export Panel (Dock Right, Tabbed with Inspector)
        self.dock_export = QDockWidget("Export", self)
        self.dock_export.setObjectName("Export")
        self.export_panel = ExportPanel(editor_window=self)
        self.dock_export.setWidget(self.export_panel)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dock_export)
        
        # Tabify Export with Inspector
        self.tabifyDockWidget(self.dock_inspector, self.dock_export)
        
        # 3c. Resources (Dock Left, Tabbed with Hierarchy usually or Bottom)
        self.dock_resources = QDockWidget("Resources", self)
        self.dock_resources.setObjectName("Resources")
        # We need to access project_manager from editor
        self.resources_panel = ResourcesPanel(self.project_manager.resource_manager, self)
        self.dock_resources.setWidget(self.resources_panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock_resources)
        
        # Refresh Inspector Presets when resources change
        self.project_manager.resource_manager.resources_changed.connect(lambda: self.inspector.set_entity(self.inspector.current_entity))
        
        # Tabify with Hierarchy
        self.tabifyDockWidget(self.dock_hierarchy, self.dock_resources)
        
        # 4. Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Left Side Stats
        self.lbl_verts = QLabel("Verts: 0")
        self.lbl_faces = QLabel("Faces: 0")
        
        # Add some spacing style
        style = "QLabel { padding: 0 10px; color: #888; }"
        self.lbl_verts.setStyleSheet(style)
        self.lbl_faces.setStyleSheet(style)
        
        self.status_bar.addWidget(self.lbl_verts)
        self.status_bar.addWidget(self.lbl_faces)
        
        self.status_label = QLabel("Ready")
        
        # Custom Spinner
        self.progress_indicator = QProgressIndicator()
        self.progress_indicator.hide()
        
        # Add to right side (Permanent widgets)
        # Order: Spinner then Label (Left to Right)
        self.status_bar.addPermanentWidget(self.progress_indicator)
        self.status_bar.addPermanentWidget(self.status_label)
        
        # Set initial dock sizes
        # self.dock_hierarchy.setMinimumWidth(300)
        # self.dock_inspector.setMinimumWidth(350)

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
        
        new_action = QAction("&New Project", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction("&Open Project...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_project_dialog)
        file_menu.addAction(open_action)
        
        save_action = QAction("&Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        export_all_action = QAction("Export &All...", self)
        export_all_action.setShortcut("Ctrl+E")
        export_all_action.triggered.connect(self.export_all_dialog)
        file_menu.addAction(export_all_action)
        
        file_menu.addSeparator()
        
        self.recent_menu = file_menu.addMenu("Open &Recent")
        self.update_recent_menu()
        
        file_menu.addSeparator()
        
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
        
        # -- View Menu --
        view_menu = menu_bar.addMenu("&View")
        fit_action = QAction("Fit to View", self)
        fit_action.setShortcut("F")
        fit_action.triggered.connect(self.fit_to_view)
        view_menu.addAction(fit_action)

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

    def update_mesh_stats(self, v_count, f_count):
        self.lbl_verts.setText(f"Verts: {v_count:,}")
        self.lbl_faces.setText(f"Faces: {f_count:,}")

    def fit_to_view(self):
        """Reset cameras to fit content"""
        # Fit 3D
        if self.viewport_3d:
            self.viewport_3d.reset_camera()
            
        # Fit 2D
        if self.viewport_2d:
            self.viewport_2d.reset_camera()

    def fit_to_view(self):
        """Reset cameras to fit content"""
        # Fit 3D
        if self.viewport_3d:
            self.viewport_3d.reset_camera()
            
        # Fit 2D
        if self.viewport_2d:
            self.viewport_2d.reset_camera()


    def on_selection_changed(self):
        # Get selected items
        items = self.hierarchy.tree.selectedItems()
        if not items:
            self.inspector.set_entity(None)
            self.export_panel.set_entity(None)
            self.viewport_2d.set_mask(None)
            if hasattr(self, 'viewport_3d'):
                self.viewport_3d.set_mask(None)
            return
            
        item = items[0]
        
        # The HierarchyPanel now stores IDs, not objects.
        # Use helper method to retrieve the entity.
        entity = self.hierarchy.get_entity_from_item(item)
        if not entity: 
            self.inspector.set_entity(None)
            self.viewport_2d.set_mask(None)
            return
        
        self.inspector.set_entity(entity)
        self.export_panel.set_entity(entity)
        
        # We need to listen to changes on ANY selected entity to update the view
        try:
            entity.changed.disconnect(self.on_current_entity_changed)
        except:
             try:
                 # Try disconnecting old direct connection if it exists
                 entity.changed.disconnect(self.schedule_update)
             except:
                 pass
            
        entity.changed.connect(self.on_current_entity_changed)
        
        self.update_mask_view()
        
    def on_current_entity_changed(self):
        """Handle changes from the currently selected entity"""
        # If drawing, we handle updates manually in on_paint to avoid lag
        if self.is_drawing_mode:
            return

        self.schedule_update()
        self.update_mask_view()

    def update_mask_view(self):
        """Check if selected entity is a mask and update 2D viewport"""
        entity = self.inspector.current_entity
        if entity and entity.entity_type == EntityType.MASK:
            # Generate mask preview
            # We need the terrain size and resolution
            # Resolution comes from root terrain
            res = int(self.root_terrain.get_property("Resolution"))
            size = self.root_terrain.get_property("Size")
            
            # Pass heightmap for Feature masks
            if hasattr(self, 'render_data') and self.render_data.heightmap is not None:
                heightmap = self.render_data.heightmap
                mask = entity.generate_mask(heightmap, size)
            else:
                # Fallback
                mask = entity.generate_mask((res, res), size)

            self.viewport_2d.set_mask(mask)
            if hasattr(self, 'viewport_3d'):
                self.viewport_3d.set_mask(mask)
        else:
            self.viewport_2d.set_mask(None)
            if hasattr(self, 'viewport_3d'):
                self.viewport_3d.set_mask(None)
    
    def schedule_update(self):
        """Debounce terrain updates - wait 300ms after last change"""
        
        # Update Hierarchy Visuals
        if self.inspector.current_entity:
             ent = self.inspector.current_entity
             if ent.id in self.hierarchy.items_map:
                 item = self.hierarchy.items_map[ent.id]
                 self.hierarchy.update_item_style(item, ent)
        
        self.update_mask_view()
        
        # Pause update if drawing
        if self.is_drawing_mode:
            return

        self.update_timer.stop()
        self.update_timer.start(300)  # 300ms debounce

    def reprocess_terrain(self):
        """Generate terrain in background thread"""
        # Cancel existing worker if running
        if self.terrain_worker and self.terrain_worker.isRunning():
            self.terrain_worker.stop()
            try:
                self.terrain_worker.finished.disconnect()
            except:
                pass
            # Connect to deleteLater to ensure cleanup
            self.terrain_worker.finished.connect(self.terrain_worker.deleteLater)
            # DO NOT WAIT: blocking call freezes UI
            # self.terrain_worker.wait()
        
        # UI Feedback
        self.status_label.setText("Generating Terrain...")
        self.progress_indicator.startAnimation()
        
        # Start new worker
        self.terrain_worker = TerrainWorker(self.root_terrain)
        self.terrain_worker.finished.connect(self.on_terrain_generated)
        self.terrain_worker.start()
    
    def on_terrain_generated(self, heightmap, phys_size, elapsed_time=0.0):
        """Called when background terrain generation completes"""
        
        # Check if resolution or scale changed
        if self.render_data.heightmap.shape != heightmap.shape or self.render_data.scale != phys_size:
            # Re-initialize render data with new size
            current_scale = phys_size
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
        self.status_label.setText(f"Ready ({elapsed_time*1000:.1f} ms)")
        self.progress_indicator.stopAnimation()
        
        # Initial Fit
        if not self.initial_fit_done:
            self.fit_to_view()
        if not self.initial_fit_done:
            self.fit_to_view()
            self.initial_fit_done = True

    def start_drawing(self):
        if not self.inspector.current_entity: return
        ent = self.inspector.current_entity
        if ent.entity_type != EntityType.MASK or ent.get_property("Type") != "Draw":
            return
            
        self.is_drawing_mode = True
        self.status_label.setText("DRAW MODE: Left Click to Paint. Stop to exit.")
        
        # Sync Brush Size and Visibility
        if hasattr(self, 'viewport_3d'):
             self.viewport_3d.brush_radius = ent.get_property("Brush Size")
             self.viewport_3d.set_brush_visible(True)
        
        # Lock UI
        self.dock_hierarchy.setDisabled(True)
        self.dock_resources.setDisabled(True)
        
        # Refresh Inspector to show Stop button
        self.inspector.build_ui()
        
    def stop_drawing(self):
        self.is_drawing_mode = False
        self.status_label.setText("Ready")
        
        # Disable Brush Cursor
        if hasattr(self, 'viewport_3d'):
             self.viewport_3d.set_brush_visible(False)
             # Ensure final mask state is visible
             if hasattr(self.viewport_3d, 'force_mask_update'):
                 self.viewport_3d.force_mask_update()
        
        self.dock_hierarchy.setDisabled(False)
        self.dock_resources.setDisabled(False)
        
        # Create Undo Command? 
        # Drawing operations modify the mask data directly.
        # We might want to snapshot the mask data before/after for undo?
        # For now, no undo for brush strokes (complex).
        
        self.inspector.build_ui()
        
        # Trigger terrain update
        self.schedule_update()
        # Force update
        self.reprocess_terrain()

    def on_paint(self, world_x, world_z, radius):
        if not self.is_drawing_mode: return False
        
        ent = self.inspector.current_entity
        if not ent: return False
        
        # DEBUG
        # print(f"Paint Event: pos=({world_x:.2f}, {world_z:.2f}), radius={radius}")
        
        # Get properties (Override radius with Brush Size)
        # Radius passed from viewport might be cursor size, but we trust the Property
        strength = ent.get_property("Brush Strength")
        opacity = ent.get_property("Brush Opacity")
        brush_size = ent.get_property("Brush Size")
        terrain_size = self.root_terrain.get_property("Size")
        
        # Sync Brush Size
        if hasattr(self, 'viewport_3d'):
             self.viewport_3d.brush_radius = brush_size
        
        ent.paint(world_x, world_z, brush_size, strength, opacity, terrain_size=terrain_size)
        
        # Update Preview (Optimized)
        if hasattr(self, 'viewport_3d'):
             # Direct update with raw data to avoid overhead
             self.viewport_3d.set_mask(ent.mask_data)
             
        # No need to call this explicitly; entity.changed signal triggers schedule_update -> update_mask_view
        # if hasattr(self, 'update_mask_view'):
        #    self.update_mask_view()
            
        return True


    def closeEvent(self, event):
        if not self.check_unsaved_changes():
            event.ignore()
            return
            
        # Save Session State
        self.settings.setValue("window/state", self.saveState())
        self.settings.setValue("window/geometry", self.saveGeometry())
        event.accept()

    # --- Project Management Slots ---
    
    def update_title(self):
        dirty = "*" if self.project_manager.is_dirty else ""
        self.setWindowTitle(f"{self.project_manager.project_name}{dirty} - Terrano")
        
    def mark_dirty(self):
        if not self.project_manager.is_dirty:
            self.project_manager.is_dirty = True
            self.update_title()
            
    def check_unsaved_changes(self):
        if self.project_manager.is_dirty:
            reply = QMessageBox.question(self, "Unsaved Changes", 
                                         "You have unsaved changes. Save before continuing?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Cancel:
                return False
            elif reply == QMessageBox.StandardButton.Yes:
                return self.save_project()
        return True

    def new_project(self):
        if not self.check_unsaved_changes(): return
        
        self.project_manager.new_project()
        
        # Reset Scene
        self.root_terrain = TerrainEntity()
        self.reload_scene(self.root_terrain)
        self.undo_stack.clear()
        
        self.update_title()
        self.status_label.setText("New project created.")

    def save_project(self):
        if not self.project_manager.current_project_path:
            return self.save_project_as()
            
        success, msg = self.project_manager.save_project(self.root_terrain, self.project_manager.current_project_path)
        if success:
             # Add file path to recent, not folder path
             project_name = self.project_manager.project_name
             fpath = os.path.join(self.project_manager.current_project_path, f"{project_name}.terrano")
             self.add_recent_project(fpath)
             
        self.status_label.setText(msg)
        self.update_title()
        return success
    
    def on_save_preset(self, entity, name):
        if not self.project_manager.resource_manager: return
        
        success, msg = self.project_manager.resource_manager.save_preset(entity, name)
        self.status_label.setText(msg)
        if not success:
             QMessageBox.critical(self, "Error", msg)

    def save_project_as(self):
        # Prompt for FOLDER
        folder = QFileDialog.getExistingDirectory(self, "Select Project Folder")
        if not folder: return False
        
        success, msg = self.project_manager.save_project(self.root_terrain, folder)
        if success:
             # Folder is project path? Project manager saves a file. 
             # Wait, save_project ensures correct path in project_manager if successful.
             # but we need the exact file path.
             # Actually, project_manager tracks `current_project_path` as FOLDER.
             # So we construct path:
             project_name = self.project_manager.project_name
             import os
             fpath = os.path.join(folder, f"{project_name}.terrano")
             self.add_recent_project(fpath)
             
        self.status_label.setText(msg)
        self.update_title()
        return success

    def open_project_dialog(self):
        if not self.check_unsaved_changes(): return
        
        # Select JSON file
        # Filter: JSON files
        fpath, _ = QFileDialog.getOpenFileName(self, "Open Project", "", "Terrano Project (*.terrano)")
        if not fpath: return
        
        root, msg = self.project_manager.load_project(fpath)
        if root:
             # Manual Refresh after load? ProjectManager does it.
             # self.resources_panel.populate_tree() # listener should handle it
             pass 
        
        if root:
            self.reload_scene(root)
            self.undo_stack.clear()
            self.update_title()
            self.status_label.setText(msg)
            self.add_recent_project(fpath)
        else:
            QMessageBox.critical(self, "Error", msg)
            
    def reload_scene(self, new_root):
        """Apply new root entity to the application state"""
        self.root_terrain = new_root
        
        # Reconnect Global Signals
        try:
             # Disconnect old if possible? Reference is lost anyway, but signals?
             pass
        except: pass
        
        # Connect new
        self.root_terrain.structure_changed.connect(self.schedule_update)
        self.root_terrain.structure_changed.connect(self.mark_dirty)
        self.root_terrain.changed.connect(self.schedule_update)
        self.root_terrain.changed.connect(self.mark_dirty)
        
        # Update Panels
        self.hierarchy.set_root(self.root_terrain)
        self.inspector.set_entity(None) # Deselect
        
        # Reset Render Data
        # Read from new root properties
        size = self.root_terrain.get_property("Resolution")
        scale = self.root_terrain.get_property("Size")
        try:
            sz = int(size)
        except: sz = 512
        if not scale: scale = 1000.0
        
        self.render_data = TerrainData(size=sz, scale=scale)
        self.viewport_3d.set_data(self.render_data)
        self.viewport_2d.set_data(self.render_data)
        
        # Trigger Generation
        self.reprocess_terrain()
        
        # Reset View (Feature request from before)
        self.fit_to_view()

    def add_recent_project(self, path):
        recents = self.settings.value("recent_projects", [], type=list)
        if not isinstance(recents, list): recents = []
        
        # Remove if exists to move to top
        if path in recents:
            recents.remove(path)
            
        recents.insert(0, path)
        
        # Limit to 10
        if len(recents) > 10:
            recents = recents[:10]
            
        self.settings.setValue("recent_projects", recents)
        self.update_recent_menu()
        
    def update_recent_menu(self):
        self.recent_menu.clear()
        recents = self.settings.value("recent_projects", [], type=list)
        if not isinstance(recents, list): recents = []
        
        # Filter out folder paths (keep only .terrano files)
        valid_recents = [p for p in recents if isinstance(p, str) and p.endswith('.terrano')]
        if len(valid_recents) != len(recents):
            recents = valid_recents
            self.settings.setValue("recent_projects", recents)
        
        if not recents:
            action = QAction("No Recent Files", self)
            action.setEnabled(False)
            self.recent_menu.addAction(action)
            return
            
        for path in recents:
             action = QAction(path, self)
             action.triggered.connect(lambda checked, p=path: self.open_recent_project(p))
             self.recent_menu.addAction(action)
             
        self.recent_menu.addSeparator()
        clear_action = QAction("Clear Recent List", self)
        clear_action.triggered.connect(self.clear_recent_projects)
        self.recent_menu.addAction(clear_action)

    def clear_recent_projects(self):
        self.settings.setValue("recent_projects", [])
        self.update_recent_menu()

    def open_recent_project(self, path):
        if not self.check_unsaved_changes(): return
        
        root, msg = self.project_manager.load_project(path)
        if root:
            self.reload_scene(root)
            self.undo_stack.clear()
            self.update_title()
            self.status_label.setText(msg)
            # Move to top again
            self.add_recent_project(path)
        else:
            QMessageBox.critical(self, "Error", msg)
            # Optionally remove from list if not found
            # self.remove_recent(path)
    
    def get_current_heightmap(self):
        """Return current terrain heightmap for export."""
        if hasattr(self, 'render_data') and self.render_data.heightmap is not None:
            return self.render_data.heightmap
        return None
    
    def export_all_dialog(self):
        """Show Export All dialog with progress tracking."""
        from PyQt6.QtWidgets import QProgressDialog
        from src.core.exporter import export_all
        
        # Default to project_folder/output if project is saved
        default_folder = ""
        if self.project_manager.current_project_path:
            default_folder = os.path.join(
                self.project_manager.current_project_path,
                "output"
            )
        
        # Prompt for output folder
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Export Folder",
            default_folder,
            QFileDialog.Option.ShowDirsOnly
        )
        
        if not folder:
            return
        
        # Count exportable entities
        def count_exportable(entity):
            count = 0
            if entity.entity_type == EntityType.ROOT or entity.entity_type == EntityType.MASK:
                count = 1
            for child in entity.get_children():
                count += count_exportable(child)
            return count
        
        total_count = count_exportable(self.root_terrain)
        
        if total_count == 0:
            QMessageBox.information(self, "Export All", "No exportable entities found.")
            return
        
        # Create progress dialog
        progress = QProgressDialog("Exporting...", "Cancel", 0, total_count, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        
        # Progress callback
        def update_progress(entity_name, current, total):
            progress.setLabelText(f"Exporting: {entity_name}")
            progress.setValue(current)
            QApplication.processEvents()  # Keep UI responsive
            
            if progress.wasCanceled():
                return False
            return True
        
        # Perform export
        success, message, exported_files = export_all(
            self.root_terrain,
            self.render_data,
            folder,
            progress_callback=update_progress
        )
        
        progress.close()
        
        # Show result
        if success:
            summary = f"Successfully exported {len(exported_files)} file(s) to:\n{folder}"
            QMessageBox.information(self, "Export All Complete", summary)
            self.status_label.setText(f"Exported {len(exported_files)} file(s)")
        else:
            QMessageBox.critical(self, "Export All Failed", message)
            self.status_label.setText("Export failed")

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
