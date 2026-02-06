import json
from src.core.scene import Entity, TerrainEntity, GeneratorEntity, FilterEntity, MaskEntity, EntityType

class SceneSerializer:
    @staticmethod
    def serialize_entity(entity):
        """Recursively serialize an entity into a dictionary."""
        data = {
            "id": entity.id,
            "type": entity.entity_type.name, # Use Enum name string e.g. "ROOT", "GENERATOR"
            "name": entity.name,
            "properties": {},
            "children": []
        }
        
        # Serialize Properties (Value only, schema is hardcoded in class def)
        # We only save values to keep JSON clean.
        # But wait, if schema changes in potential updates, loading might be tricky?
        # Standard approach: Save values. Class __init__ defines schema.
        # We assume backward compatibility handling will be in deserialize/class code.
        for prop_name, prop_data in entity.properties.items():
            data["properties"][prop_name] = prop_data["value"]
            
        # Recurse
        for child in entity.get_children():
            data["children"].append(SceneSerializer.serialize_entity(child))
            
        return data

    @staticmethod
    def serialize_tree(root_entity):
        """Serialize the entire tree starting from root."""
        return SceneSerializer.serialize_entity(root_entity)

    @staticmethod
    def deserialize_tree(data):
        """Reconstruct the entity tree from dictionary."""
        # 1. Create Root (or current node)
        type_str = data.get("type", "ROOT")
        name = data.get("name", "Entity")
        
        entity = None
        
        # Factory
        if type_str == "ROOT":
            entity = TerrainEntity() # Handles defaults
        elif type_str == "GENERATOR":
            entity = GeneratorEntity(name)
        elif type_str == "FILTER":
            entity = FilterEntity(name)
        elif type_str == "MASK":
            entity = MaskEntity(name)
        else:
            # Fallback or error
            print(f"Unknown entity type: {type_str}")
            return None
            
        # 2. Restore ID
        if "id" in data:
            entity.id = data["id"]
            
        # 3. Restore Properties
        props = data.get("properties", {})
        for key, value in props.items():
            # We use set_property to ensure checks/signals (though signals might not be bound yet)
            # Safe set: only if property exists
            if key in entity.properties:
                entity.set_property(key, value)
                
        # 4. Restore Children
        children_data = data.get("children", [])
        for child_data in children_data:
            child_ent = SceneSerializer.deserialize_tree(child_data)
            if child_ent:
                entity.add_child(child_ent)
                
        return entity
