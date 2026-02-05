from PyQt6.QtWidgets import (QTreeWidget, QTreeWidgetItem, QMenu, QWidget, QVBoxLayout, 
                             QToolBar, QAbstractItemView)
from PyQt6.QtGui import QAction, QIcon, QBrush
from PyQt6.QtCore import Qt
from src.core.scene import TerrainEntity, FilterEntity, MaskEntity, GeneratorEntity, EntityType


class HierarchyPanel(QWidget):
    def __init__(self, root_entity, parent=None):
        super().__init__(parent)
        self.root_entity = root_entity
        self.items_map = {} # Map Entity.id -> Item
        self.id_map = {} # Map Item -> Entity.id (Reverse lookup helper, or store in UserRole as string)
        self.entity_lookup = {} # Map Entity.id -> Entity Object (for retrieval)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        
        # Toolbar
        self.toolbar = QToolBar()
        self.layout.addWidget(self.toolbar)
        
        self.add_gen_action = self.toolbar.addAction("Gen")
        self.add_gen_action.triggered.connect(lambda: self.add_entity_to_selection(EntityType.GENERATOR))
        
        self.add_filter_action = self.toolbar.addAction("Filter")
        self.add_filter_action.triggered.connect(lambda: self.add_entity_to_selection(EntityType.FILTER))
        
        self.add_mask_action = self.toolbar.addAction("Mask")
        self.add_mask_action.triggered.connect(lambda: self.add_entity_to_selection(EntityType.MASK))
        
        # Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Hierarchy")
        self.tree.itemClicked.connect(self.on_item_clicked)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)
        
        # Drag & Drop Support
        self.tree.setDragEnabled(True)
        self.tree.setAcceptDrops(True)
        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        
        self.tree.setAcceptDrops(True)
        self.tree.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        
        # Override dropEvent and dragMoveEvent
        self.tree.dropEvent = self.on_drop_event
        self.tree.dragMoveEvent = self.on_drag_move_event
        
        self.layout.addWidget(self.tree)
        self.setLayout(self.layout)
        
        self.refresh_tree()
        
    def refresh_tree(self):
        # Save expanded state
        expanded_ids = set()
        if hasattr(self, 'items_map'):
             for eid, item in self.items_map.items():
                 if item.isExpanded():
                     expanded_ids.add(eid)

        self.tree.clear()
        self.items_map = {} 
        self.entity_lookup = {}
        
        self.add_node(self.root_entity, self.tree.invisibleRootItem())
        
        # Restore expansion
        for eid, item in self.items_map.items():
            if eid in expanded_ids:
                item.setExpanded(True)
            elif self.root_entity and eid == self.root_entity.id:
                item.setExpanded(True)
                
        # Update UI state (toolbar)
        self.update_ui_state()

    def add_node(self, entity, parent_item):
        item = QTreeWidgetItem([entity.name])
        # STORE ID STRING INSTEAD OF OBJECT to fix QVariant warning
        item.setData(0, Qt.ItemDataRole.UserRole, entity.id)
        
        # Register
        self.items_map[entity.id] = item
        self.entity_lookup[entity.id] = entity
        
        parent_item.addChild(item)
        
        # Apply initial visual state
        self.update_item_style(item, entity)
        
        for child in entity.get_children():
            self.add_node(child, item)

    def update_item_style(self, item, entity):
        is_enabled = entity.get_property("Enabled")
        
        if is_enabled:
            # Default color (None resets to theme default)
            item.setForeground(0, QBrush()) 
        else:
            # Grayed out
            item.setForeground(0, QBrush(Qt.GlobalColor.gray))

    def get_entity_from_item(self, item):
        if not item: return None
        eid = item.data(0, Qt.ItemDataRole.UserRole)
        return self.entity_lookup.get(eid)

    def on_item_clicked(self, item, column):
        entity = self.get_entity_from_item(item)
        self.update_ui_state()
        pass

    def can_accept_child(self, parent_entity, child_type):
        """
        Constraints:
        - Terrain (ROOT) -> [Generator, Filter, Mask]
        - Mask -> [Generator, Filter, Mask]
        - Generator -> []
        - Filter -> []
        child_type: EntityType
        """
        if not parent_entity:
            return False
            
        pt = parent_entity.entity_type
        
        # Leaves
        if pt == EntityType.GENERATOR or pt == EntityType.FILTER:
            return False
            
        # Containers
        if pt == EntityType.ROOT or pt == EntityType.MASK:
            return True
            
        return False

    def on_drag_move_event(self, event):
        # Validate drop target
        # QTreeWidget logic tries to put it 'on', 'above', 'below'
        # We only really care about reparenting ('on').
        # If 'above'/'below', the parent is the target's parent.
        
        item = self.tree.itemAt(event.position().toPoint())
        if not item:
            event.ignore()
            return
            
        target_entity = self.get_entity_from_item(item)
        
        # Get source item (single selection)
        sel = self.tree.selectedItems()
        if not sel:
            event.ignore()
            return
            
        source_entity = self.get_entity_from_item(sel[0])
        
        # We need to know IF strict internal move logic considers this "re-parenting" (ON) or Reordering (Above/Below)
        # Visual cues in QTreeWidget are obscure to code access.
        # But generally:
        # If dropping ON a Generator/Filter -> Invalid (unless reordering siblings, but QTreeWidget might interpret ON as add child)
        # To simplify: We just allow QTreeWidget default, but then on DROP we check.
        # However, improved UX is to reject drag if hovering invalid parent.
        
        # Let's rely on QTreeWidget default mostly but verify logic:
        # If target can't accept children, we should ideally NOT highlight "ON" action.
        # But we can't easily detect the drop action type (On/Above/Below) in pure PyQt without complex calculations.
        
        # Compromise: Allow drag, but in dropEvent we validate.
        QTreeWidget.dragMoveEvent(self.tree, event)

    def on_drop_event(self, event):
        # 1. Get Source and Destination
        target_item = self.tree.itemAt(event.position().toPoint())
        
        # Note: QTreeWidget drop behavior is complex (can be child or sibling).
        # We will let QTreeWidget perform the visual move first.
        # THEN we verify the structure. If invalid, we REVERT (refresh tree).
        
        QTreeWidget.dropEvent(self.tree, event)
        
        # Sync and Validate
        valid = self.sync_hierarchy_from_visuals()
        
        if not valid:
            print("Invalid Move Reverted")
            self.refresh_tree()
        else:
            self.root_entity.structure_changed.emit()

    def sync_hierarchy_from_visuals(self):
        # Rebuild hierarchy from visual tree
        # AND check constraints. Returns False if invalid.
        
        root_item = self.tree.invisibleRootItem()
        # The root item itself corresponds to... nothing? No, invisible root contains our Root Entity item.
        # Wait, simple add_node logic adds root_entity to invisibleRoot.
        # So invisibleRoot has 1 child: Terrain.
        
        if root_item.childCount() != 1:
            # User dragged Terrain to be a child of something? or deleted it?
            return False
            
        terrain_item = root_item.child(0)
        terrain_ent = self.get_entity_from_item(terrain_item)
        
        if not terrain_ent or terrain_ent.entity_type != EntityType.ROOT:
            return False
            
        return self._sync_recursive(terrain_item, terrain_ent)
        
    def _sync_recursive(self, parent_item, parent_entity):
        # 1. Clear children
        new_children = []
        
        count = parent_item.childCount()
        for i in range(count):
            child_item = parent_item.child(i)
            child_entity = self.get_entity_from_item(child_item)
            
            if not child_entity: return False
            
            # Constraint Check
            if not self.can_accept_child(parent_entity, child_entity.entity_type):
                return False
                
            child_entity._parent = parent_entity
            new_children.append(child_entity)
            
            # Recurse
            if not self._sync_recursive(child_item, child_entity):
                return False
                
        parent_entity._children = new_children
        return True

    def update_ui_state(self):
        # Enable/Disable toolbar based on selection
        items = self.tree.selectedItems()
        if not items:
            self.add_gen_action.setEnabled(False)
            self.add_filter_action.setEnabled(False)
            self.add_mask_action.setEnabled(False)
            return
            
        ent = self.get_entity_from_item(items[0])
        # Can we add to this entity?
        # Check if it can accept Generic (Generator/Filter/Mask)
        # Since all our leaves (Gen/Filter) accept NOTHING, we disable all.
        
        can_add = self.can_accept_child(ent, EntityType.GENERATOR) # Generator is representative
        
        self.add_gen_action.setEnabled(can_add)
        self.add_filter_action.setEnabled(can_add)
        self.add_mask_action.setEnabled(can_add)

    def add_entity_to_selection(self, e_type):
        items = self.tree.selectedItems()
        parent = self.root_entity
        if items:
            sel_ent = self.get_entity_from_item(items[0])
            if self.can_accept_child(sel_ent, e_type):
                parent = sel_ent
            else:
                # If selected is leaf, maybe add to its parent? (Sibling)
                # UX Choice: "Insert After" behavior?
                # For now, strict: Only add if container selected, OR fall back to Root.
                if self.can_accept_child(sel_ent._parent, e_type):
                   parent = sel_ent._parent
        
        # Final safety
        if not self.can_accept_child(parent, e_type):
            return
            
        new_ent = self.create_entity(e_type)
        if new_ent:
            new_ent.set_parent(parent)
            self.refresh_tree()
            self.root_entity.structure_changed.emit()

    def create_entity(self, e_type):
        if e_type == EntityType.GENERATOR:
            return GeneratorEntity("New Generator")
        elif e_type == EntityType.FILTER:
            return FilterEntity("New Filter")
        elif e_type == EntityType.MASK:
            return MaskEntity("New Mask")
        return None

    def open_context_menu(self, position):
        item = self.tree.itemAt(position)
        if not item:
            return
            
        entity = self.get_entity_from_item(item)
        if not entity: return
        
        menu = QMenu()
        
        # Add actions only if valid
        if self.can_accept_child(entity, EntityType.GENERATOR):
            menu.addAction("Add Generator", lambda: self.safe_add(entity, EntityType.GENERATOR))
            menu.addAction("Add Filter", lambda: self.safe_add(entity, EntityType.FILTER))
            menu.addAction("Add Mask", lambda: self.safe_add(entity, EntityType.MASK))
            menu.addSeparator()
            
        # Toggle Enable
        is_enabled = entity.get_property("Enabled")
        toggle_text = "Disable" if is_enabled else "Enable"
        toggle_action = menu.addAction(toggle_text)
        
        menu.addSeparator()
        del_action = menu.addAction("Delete")
        
        action = menu.exec(self.tree.viewport().mapToGlobal(position))
        
        if action == toggle_action:
            new_state = not is_enabled
            entity.set_property("Enabled", new_state)
            # Update visual style immediately (though changed signal might trigger full refresh)
            self.update_item_style(item, entity)
            # Also trigger main window update handled by entity.changed signal
        
        elif action == del_action:
            if entity != self.root_entity:
                entity.set_parent(None)
                self.refresh_tree()
                self.root_entity.structure_changed.emit()

    def safe_add(self, parent, e_type):
        new_ent = self.create_entity(e_type)
        new_ent.set_parent(parent)
        self.refresh_tree()
        self.root_entity.structure_changed.emit()

    def add_entity_descendant(self, parent, e_type):
        self.safe_add(parent, e_type)

