"""
Export Panel UI - Context-aware export interface for heightmaps and masks.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QComboBox, 
                             QPushButton, QLabel, QFileDialog, QMessageBox,
                             QLineEdit, QHBoxLayout, QToolButton)
from PyQt6.QtCore import Qt
from src.core.scene import EntityType
from src.core.exporter import export_heightmap, export_mask, get_export_filename
import os


class ExportPanel(QWidget):
    def __init__(self, editor_window=None, parent=None):
        super().__init__(parent)
        self.editor_window = editor_window
        self.current_entity = None
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        
        # Title
        self.title_label = QLabel("Export")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #e0e0e0;")
        layout.addWidget(self.title_label)
        
        # Form layout for settings
        self.form_widget = QWidget()
        self.form_layout = QFormLayout()
        self.form_layout.setContentsMargins(0, 0, 0, 0)
        self.form_layout.setSpacing(8)
        self.form_widget.setLayout(self.form_layout)
        
        # Filename field
        self.filename_edit = QLineEdit()
        self.filename_edit.setPlaceholderText("(entity ID)")
        self.filename_edit.textChanged.connect(self.on_filename_changed)
        self.form_layout.addRow("Filename:", self.filename_edit)
        
        # Directory field with browse button
        dir_widget = QWidget()
        dir_layout = QHBoxLayout()
        dir_layout.setContentsMargins(0, 0, 0, 0)
        dir_layout.setSpacing(4)
        dir_widget.setLayout(dir_layout)
        
        self.directory_edit = QLineEdit()
        self.directory_edit.setPlaceholderText("output")
        self.directory_edit.textChanged.connect(self.on_directory_changed)
        dir_layout.addWidget(self.directory_edit)
        
        browse_btn = QToolButton()
        browse_btn.setText("...")
        browse_btn.clicked.connect(self.browse_directory)
        dir_layout.addWidget(browse_btn)
        
        self.form_layout.addRow("Directory:", dir_widget)
        
        # Resolution dropdown
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["512", "1024", "2048", "4096", "8192"])
        self.resolution_combo.currentTextChanged.connect(self.on_resolution_changed)
        self.form_layout.addRow("Resolution:", self.resolution_combo)
        
        # Format dropdown
        self.format_combo = QComboBox()
        self.format_combo.addItems(["TIFF (32-bit)", "PNG (16-bit)", "JPEG (8-bit)", "OBJ Mesh"])
        self.format_combo.currentTextChanged.connect(self.on_format_changed)
        self.form_layout.addRow("Format:", self.format_combo)
        
        # Current resolution info
        self.info_label = QLabel("")
        self.info_label.setStyleSheet("color: #888; font-size: 11px;")
        self.info_label.setWordWrap(True)
        self.form_layout.addRow("", self.info_label)
        
        # Full path preview
        self.path_preview_label = QLabel("")
        self.path_preview_label.setStyleSheet("color: #888; font-size: 10px;")
        self.path_preview_label.setWordWrap(True)
        self.form_layout.addRow("Output:", self.path_preview_label)
        
        layout.addWidget(self.form_widget)
        
        # Export button
        self.export_button = QPushButton("Export")
        self.export_button.setStyleSheet("""
            QPushButton {
                background-color: #3daee9;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #4dbef9;
            }
            QPushButton:pressed {
                background-color: #2d9ed9;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        self.export_button.clicked.connect(self.on_export_clicked)
        layout.addWidget(self.export_button)
        
        # No selection message
        self.no_selection_label = QLabel("Select terrain or mask to export")
        self.no_selection_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.no_selection_label.setStyleSheet("color: #888; padding: 20px;")
        layout.addWidget(self.no_selection_label)
        
        # Stretch
        layout.addStretch()
        
        self.setLayout(layout)
        
        # Initial state
        self.set_entity(None)
    
    def set_entity(self, entity):
        """Update panel based on selected entity."""
        self.current_entity = entity
        
        # Check if entity is exportable
        is_exportable = (entity is not None and 
                        (entity.entity_type == EntityType.ROOT or 
                         entity.entity_type == EntityType.MASK))
        
        # Show/hide appropriate widgets
        self.form_widget.setVisible(is_exportable)
        self.export_button.setVisible(is_exportable)
        self.no_selection_label.setVisible(not is_exportable)
        
        if is_exportable:
            # Load settings from entity
            self.load_entity_settings()
            
            # Update title and button text based on entity type and format
            if entity.entity_type == EntityType.ROOT:
                format_str = entity.get_property("Export Format")
                if "OBJ" in format_str:
                    self.title_label.setText("Export Mesh")
                    self.export_button.setText("Export Mesh")
                else:
                    self.title_label.setText("Export Heightmap")
                    self.export_button.setText("Export Heightmap")
            else:  # MASK
                self.title_label.setText("Export Mask")
                self.export_button.setText("Export Mask")
            
            # Update info label
            self.update_info_label()
            
            # Update path preview
            self.update_path_preview()
    
    def load_entity_settings(self):
        """Load export settings from current entity."""
        if not self.current_entity:
            return
        
        # Block signals to prevent triggering property updates
        self.filename_edit.blockSignals(True)
        self.directory_edit.blockSignals(True)
        self.resolution_combo.blockSignals(True)
        self.format_combo.blockSignals(True)
        
        # Load filename
        filename = self.current_entity.get_property("Export Filename")
        self.filename_edit.setText(filename)
        
        # Load directory
        directory = self.current_entity.get_property("Export Directory")
        self.directory_edit.setText(directory)
        
        # Load resolution
        resolution = self.current_entity.get_property("Export Resolution")
        idx = self.resolution_combo.findText(resolution)
        if idx >= 0:
            self.resolution_combo.setCurrentIndex(idx)
        
        # Load format
        format_str = self.current_entity.get_property("Export Format")
        idx = self.format_combo.findText(format_str)
        if idx >= 0:
            self.format_combo.setCurrentIndex(idx)
        
        # Unblock signals
        self.filename_edit.blockSignals(False)
        self.directory_edit.blockSignals(False)
        self.resolution_combo.blockSignals(False)
        self.format_combo.blockSignals(False)
    
    def update_info_label(self):
        """Update the info label with current terrain/mask resolution."""
        if not self.current_entity:
            return
        
        if self.current_entity.entity_type == EntityType.ROOT:
            # Get terrain resolution
            current_res = self.current_entity.get_property("Resolution")
            self.info_label.setText(f"Current terrain resolution: {current_res}")
        else:  # MASK
            # Get mask resolution if it's a draw mask
            mask_type = self.current_entity.get_property("Type")
            if mask_type == "Draw":
                mask_res = self.current_entity.get_property("Mask Resolution")
                self.info_label.setText(f"Current mask resolution: {mask_res}")
            else:
                self.info_label.setText("")
    
    def update_path_preview(self):
        """Update the full path preview."""
        if not self.current_entity or not self.editor_window:
            self.path_preview_label.setText("")
            return
        
        # Get filename
        filename = self.filename_edit.text().strip()
        if not filename:
            # Use entity ID or name
            if hasattr(self.current_entity, '_has_custom_name') and self.current_entity._has_custom_name:
                filename = self.current_entity.name
            else:
                filename = self.current_entity.id
        
        # Add extension based on format
        format_str = self.format_combo.currentText()
        if "TIFF" in format_str:
            ext = ".tiff"
        elif "PNG" in format_str:
            ext = ".png"
        elif "JPEG" in format_str:
            ext = ".jpg"
        elif "OBJ" in format_str:
            ext = ".obj"
        else:
            ext = ""
        
        if not filename.endswith(ext):
            filename += ext
        
        # Get directory
        directory = self.directory_edit.text().strip()
        if not directory:
            directory = "output"
        
        # Build full path
        if self.editor_window.project_manager.current_project_path:
            full_path = os.path.join(
                self.editor_window.project_manager.current_project_path,
                directory,
                filename
            )
            self.path_preview_label.setText(full_path)
        else:
            self.path_preview_label.setText(f"{directory}/{filename}")
    
    def on_filename_changed(self, value):
        """Handle filename change."""
        if self.current_entity:
            self.current_entity.set_property("Export Filename", value)
            self.update_path_preview()
    
    def on_directory_changed(self, value):
        """Handle directory change."""
        if self.current_entity:
            self.current_entity.set_property("Export Directory", value)
            self.update_path_preview()
    
    def on_resolution_changed(self, value):
        """Handle resolution change."""
        if self.current_entity:
            self.current_entity.set_property("Export Resolution", value)
    
    def on_format_changed(self, value):
        """Handle format change."""
        if self.current_entity:
            self.current_entity.set_property("Export Format", value)
            self.update_path_preview()
            
            # Update title and button text for terrain entities
            if self.current_entity.entity_type == EntityType.ROOT:
                if "OBJ" in value:
                    self.title_label.setText("Export Mesh")
                    self.export_button.setText("Export Mesh")
                else:
                    self.title_label.setText("Export Heightmap")
                    self.export_button.setText("Export Heightmap")
    
    def browse_directory(self):
        """Show directory selection dialog."""
        if not self.editor_window:
            return
        
        # Default to project folder
        default_dir = ""
        if self.editor_window.project_manager.current_project_path:
            default_dir = self.editor_window.project_manager.current_project_path
        
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Export Directory",
            default_dir,
            QFileDialog.Option.ShowDirsOnly
        )
        
        if directory:
            # Make relative to project if possible
            if self.editor_window.project_manager.current_project_path:
                try:
                    rel_path = os.path.relpath(directory, self.editor_window.project_manager.current_project_path)
                    self.directory_edit.setText(rel_path)
                except ValueError:
                    # Different drive, use absolute
                    self.directory_edit.setText(directory)
            else:
                self.directory_edit.setText(directory)
    
    def on_export_clicked(self):
        """Handle export button click."""
        if not self.current_entity or not self.editor_window:
            return
        
        # Get export settings
        resolution = int(self.current_entity.get_property("Export Resolution"))
        format_str = self.current_entity.get_property("Export Format")
        filename = self.current_entity.get_property("Export Filename").strip()
        directory = self.current_entity.get_property("Export Directory").strip()
        
        # Use entity ID/name if no filename
        if not filename:
            if hasattr(self.current_entity, '_has_custom_name') and self.current_entity._has_custom_name:
                filename = self.current_entity.name
            else:
                filename = self.current_entity.id
        
        # Add extension if missing
        if "TIFF" in format_str:
            ext = ".tiff"
        elif "PNG" in format_str:
            ext = ".png"
        elif "JPEG" in format_str:
            ext = ".jpg"
        elif "OBJ" in format_str:
            ext = ".obj"
        else:
            ext = ""
        
        if not filename.endswith(ext):
            filename += ext
        
        # Use default directory if empty
        if not directory:
            directory = "output"
        
        # Build full path
        if self.editor_window.project_manager.current_project_path:
            output_dir = os.path.join(
                self.editor_window.project_manager.current_project_path,
                directory
            )
        else:
            output_dir = directory
        
        # Create directory if it doesn't exist
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to create directory: {str(e)}")
                return
        
        filepath = os.path.join(output_dir, filename)
        
        # Perform export
        if self.current_entity.entity_type == EntityType.ROOT:
            # Get heightmap
            heightmap = self.editor_window.render_data.heightmap
            
            # Export heightmap or mesh
            if "OBJ" in format_str:
                # Export as mesh
                from src.core.exporter import export_mesh
                terrain_size = self.current_entity.get_property("Size")
                success, message = export_mesh(heightmap, filepath, resolution, terrain_size)
            else:
                # Export as heightmap
                success, message = export_heightmap(heightmap, filepath, resolution, format_str)
        else:  # MASK
            # Generate and export mask
            root = self.editor_window.root_terrain
            res = int(root.get_property("Resolution"))
            size = root.get_property("Size")
            
            if hasattr(self.editor_window, 'render_data') and self.editor_window.render_data.heightmap is not None:
                heightmap = self.editor_window.render_data.heightmap
                mask = self.current_entity.generate_mask(heightmap, size)
            else:
                mask = self.current_entity.generate_mask((res, res), size)
            
            success, message = export_mask(mask, filepath, resolution, format_str)
        
        # Show result
        if success:
            self.editor_window.status_label.setText(message)
            QMessageBox.information(self, "Export Complete", f"Successfully exported to:\n{filepath}")
        else:
            QMessageBox.critical(self, "Export Error", message)
            self.editor_window.status_label.setText("Export failed")
