
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, 
                             QMenu, QMessageBox, QApplication, QSplitter, QListWidget, QListWidgetItem, QAbstractItemView)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction, QIcon

from src.core.commands import ApplyPresetCommand
import os

class ResourcesPanel(QWidget):
    def __init__(self, resource_manager, editor_window=None):
        super().__init__()
        self.resource_manager = resource_manager
        self.editor_window = editor_window 
        
        self.init_ui()
        
        # Connect signals
        self.resource_manager.resources_changed.connect(self.populate_categories)
        self.populate_categories()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Splitter for Categories | Content
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left: Categories (List of folders/types)
        self.category_list = QListWidget()
        self.category_list.currentItemChanged.connect(self.on_category_changed)
        self.splitter.addWidget(self.category_list)
        
        # Right: Content (Grid/List of resources)
        self.content_list = QListWidget()
        self.content_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.content_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.content_list.setSpacing(10)
        self.content_list.setIconSize(QSize(64, 64))
        self.content_list.setMovement(QListWidget.Movement.Static)
        
        # Context Menu Policy
        self.content_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.content_list.customContextMenuRequested.connect(self.open_context_menu)
        
        # Drag and Drop
        self.content_list.setDragEnabled(True)
        
        self.splitter.addWidget(self.content_list)
        
        # Set initial sizes (30% left, 70% right)
        self.splitter.setSizes([100, 300])
        
        layout.addWidget(self.splitter)
        
    def populate_categories(self):
        current_row = self.category_list.currentRow()
        self.category_list.clear()
        
        # Hardcoded categories based on ResourceManager structure
        categories = ["Generators", "Filters", "Images", "Other"]
        
        for cat in categories:
            item = QListWidgetItem(cat)
            self.category_list.addItem(item)
            
        if current_row >= 0 and current_row < self.category_list.count():
            self.category_list.setCurrentRow(current_row)
        elif self.category_list.count() > 0:
            self.category_list.setCurrentRow(0)

    def on_category_changed(self, current, previous):
        if not current: return
        
        category = current.text()
        self.populate_content(category)
        
    def populate_content(self, category):
        self.content_list.clear()
        
        resources = self.resource_manager.resources.get(category, [])
        
        for res in resources:
            item = QListWidgetItem(res["name"])
            item.setData(Qt.ItemDataRole.UserRole, res)
            # Todo: Set Icon based on type/image content
            self.content_list.addItem(item)

    def open_context_menu(self, position):
        item = self.content_list.itemAt(position)
        if not item: return
        
        payload = item.data(Qt.ItemDataRole.UserRole)
        if not payload: return
        
        menu = QMenu()
        file_path = payload["path"]
        
        if payload["type"] == "Preset":
            action_apply = QAction("Apply to Selected", self)
            action_apply.triggered.connect(lambda: self.apply_preset(file_path))
            menu.addAction(action_apply)
            
            menu.addSeparator()
            
            action_delete = QAction("Delete Preset", self)
            action_delete.triggered.connect(lambda: self.delete_resource(file_path))
            menu.addAction(action_delete)
            
        elif payload["type"] == "Image":
            action_copy = QAction("Copy Path", self)
            action_copy.triggered.connect(lambda: self.copy_path(file_path))
            menu.addAction(action_copy)
            
        menu.exec(self.content_list.viewport().mapToGlobal(position))
        
    def apply_preset(self, path):
        if not self.editor_window: return
        
        entity = self.editor_window.inspector.current_entity
        if not entity:
            QMessageBox.warning(self, "No Selection", "Please select an entity in the Hierarchy to apply the preset.")
            return
            
        # Read Data
        properties, msg = self.resource_manager.read_preset_data(entity, path)
        if properties is None:
            QMessageBox.critical(self, "Error", msg)
            return

        # Push Command
        preset_name = os.path.basename(path)
        cmd = ApplyPresetCommand(entity, preset_name, properties)
        
        if hasattr(self.editor_window, "undo_stack"):
             self.editor_window.undo_stack.push(cmd)
             self.editor_window.status_label.setText(f"Applied preset {preset_name}")
        else:
             # Fallback if no undo stack (shouldn't happen in EditorWindow)
             cmd.redo() 
             self.editor_window.status_label.setText(f"Applied preset {preset_name} (No Undo)")

    def copy_path(self, path):
        clipboard = QApplication.clipboard()
        clipboard.setText(path)
        if self.editor_window:
            self.editor_window.status_label.setText("Path copied to clipboard.")

    def delete_resource(self, path):
        confirm = QMessageBox.question(self, "Confirm Delete", f"Delete {os.path.basename(path)}?", 
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            try:
                os.remove(path)
                self.resource_manager.refresh()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete file: {e}")
