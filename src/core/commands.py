from PyQt6.QtGui import QUndoCommand
from src.core.scene import Entity

class AddEntityCommand(QUndoCommand):
    def __init__(self, parent, entity, row=None):
        super().__init__(f"Add {entity.name}")
        self.parent = parent
        self.entity = entity
        self.row = row
        
    def redo(self):
        if self.row is not None:
            self.parent.add_child(self.entity, self.row)
        else:
            self.parent.add_child(self.entity)
        # Signal is emitted by Entity.add_child
        
    def undo(self):
        self.entity.set_parent(None)
        # Signal is emitted by Entity.set_parent

class RemoveEntityCommand(QUndoCommand):
    def __init__(self, entity):
        super().__init__(f"Delete {entity.name}")
        self.entity = entity
        self.parent = entity._parent
        self.row = -1
        if self.parent:
            try:
                self.row = self.parent._children.index(entity)
            except ValueError:
                self.row = -1

    def redo(self):
        if self.entity._parent:
            self.entity.set_parent(None)
            
    def undo(self):
        if self.parent and self.row != -1:
            self.parent.add_child(self.entity, self.row)

class RenameEntityCommand(QUndoCommand):
    def __init__(self, entity, new_name):
        super().__init__(f"Rename to {new_name}")
        self.entity = entity
        self.old_name = entity.name
        self.new_name = new_name
        
    def redo(self):
        self.entity.name = self.new_name
        
    def undo(self):
        self.entity.name = self.old_name

class PropertyChangeCommand(QUndoCommand):
    def __init__(self, entity, prop_name, new_value):
        super().__init__(f"Change {prop_name}")
        self.entity = entity
        self.prop_name = prop_name
        self.new_value = new_value
        self.old_value = entity.get_property(prop_name)
        
    def redo(self):
        self.entity.set_property(self.prop_name, self.new_value)
        
    def undo(self):
        self.entity.set_property(self.prop_name, self.old_value)

class MoveEntityCommand(QUndoCommand):
    def __init__(self, entity, new_parent, new_index):
        super().__init__(f"Move {entity.name}")
        self.entity = entity
        self.new_parent = new_parent
        self.new_index = new_index
        
        self.old_parent = entity._parent
        self.old_index = -1
        if self.old_parent:
            try:
                self.old_index = self.old_parent._children.index(entity)
            except ValueError:
                self.old_index = -1
                
    def redo(self):
        # Remove from old parent first
        current_parent = self.entity._parent
        if current_parent:
            current_parent.remove_child(self.entity)
        
        # Add to new parent at index
        if self.new_parent:
             self.new_parent.add_child(self.entity, self.new_index)
        
    def undo(self):
        if self.old_parent:
            self.old_parent.add_child(self.entity, self.old_index)
