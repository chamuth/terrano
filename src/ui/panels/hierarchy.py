
from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QMenu, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt
from src.core.scene import TerrainEntity, FilterEntity, MaskEntity

class HierarchyPanel(QWidget):
    def __init__(self, root_entity, parent=None):
        super().__init__(parent)
        self.root_entity = root_entity
        
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Entities")
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)
        
        self.layout.addWidget(self.tree)
        self.setLayout(self.layout)
        
        self.refresh_tree()
        
        # Listen for changes
        # In a real app we'd connect specific signals.
        
    def refresh_tree(self):
        self.tree.clear()
        self.items_map = {} # Map Entity -> Item
        
        self.add_node(self.root_entity, self.tree.invisibleRootItem())
        
        self.tree.expandAll()

    def add_node(self, entity, parent_item):
        item = QTreeWidgetItem([entity.name])
        item.setData(0, Qt.ItemDataRole.UserRole, entity)
        parent_item.addChild(item)
        self.items_map[entity] = item
        
        for child in entity.get_children():
            self.add_node(child, item)

    def on_item_clicked(self, item, column):
        entity = item.data(0, Qt.ItemDataRole.UserRole)
        # We need to signal the inspector.
        # MainWindow will handle this connection usually.
        pass

    def open_context_menu(self, position):
        item = self.tree.itemAt(position)
        if not item:
            return
            
        entity = item.data(0, Qt.ItemDataRole.UserRole)
        
        menu = QMenu()
        
        add_filter_action = menu.addAction("Add Filter")
        add_mask_action = menu.addAction("Add Mask")
        menu.addSeparator()
        delete_action = menu.addAction("Delete")
        
        action = menu.exec(self.tree.viewport().mapToGlobal(position))
        
        if action == add_filter_action:
            new_filter = FilterEntity("New Filter", "Noise")
            new_filter.set_parent(entity)
            self.refresh_tree() # Naive refresh
        elif action == add_mask_action:
            new_mask = MaskEntity("New Mask")
            new_mask.set_parent(entity)
            self.refresh_tree()
        elif action == delete_action:
            if entity != self.root_entity: # Prevent deleting root
                entity.set_parent(None) # Detach
                self.refresh_tree()
