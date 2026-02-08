
import os
import json
from PyQt6.QtCore import QObject, pyqtSignal
from src.core.serializer import SceneSerializer

class ResourceManager(QObject):
    """
    Manages project resources (files like images, presets).
    Scanning is currently done on demand or refresh.
    """
    resources_changed = pyqtSignal()
    
    def __init__(self, project_manager):
        super().__init__()
        self.project_manager = project_manager
        
        # Structure: { "Generators": [], "Filters": [], "Presets": [], "Images": [], "Other": [] }
        # Items are dicts: { "name": "...", "path": "...", "type": "..." }
        self.resources = {
            "Generators": [],
            "Filters": [],
            "Presets": [], # Fallback for unknown preset types or generic ones
            "Images": [],
            "Other": []
        }
        
    def refresh(self):
        """Scan project directory for resources."""
        if not self.project_manager.current_project_path:
            self.clear()
            return

        self.clear_resources()
        
        root_path = self.project_manager.current_project_path
        
        for root, dirs, files in os.walk(root_path):
            # Skip hidden folders like .cache or .git
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if file.startswith('.'): continue
                
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, root_path)
                
                ext = os.path.splitext(file)[1].lower()
                
                item = {
                    "name": file,
                    "path": full_path,
                    "rel_path": rel_path,
                    "dir": os.path.dirname(rel_path)
                }
                
                if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff']:
                    item["type"] = "Image"
                    self.resources["Images"].append(item)
                elif ext in ['.json', '.preset']:
                    # Simple check if it's a preset
                    try:
                        with open(full_path, 'r') as f:
                            data = json.load(f)
                            if "type" in data and "properties" in data:
                                item["type"] = "Preset"
                                preset_type = data.get("type")
                                item["preset_type"] = preset_type
                                
                                if preset_type == "GENERATOR":
                                    self.resources["Generators"].append(item)
                                elif preset_type == "FILTER":
                                    self.resources["Filters"].append(item)
                                else:
                                    self.resources["Presets"].append(item)

                            elif "terrano" in ext:
                                # Project file, ignore or list as Project
                                pass 
                            else:
                                item["type"] = "Other"
                                self.resources["Other"].append(item)
                    except:
                        pass # specific handling for errors?
                else:
                    item["type"] = "Other"
                    # self.resources["Other"].append(item) 
                    
        self.resources_changed.emit()

    def clear(self):
        self.clear_resources()
        self.resources_changed.emit()
        
    def clear_resources(self):
        self.resources = {
            "Generators": [],
            "Filters": [],
            "Presets": [],
            "Images": [],
            "Other": []
        }

    def get_presets(self, entity_type_name):
        """Get all presets matching the given entity type name (e.g. 'GENERATOR')."""
        matching = []
        # Decide which list to search based on type name
        source_list = []
        if entity_type_name == "GENERATOR":
            source_list = self.resources["Generators"]
        elif entity_type_name == "FILTER":
            source_list = self.resources["Filters"]
        else:
            source_list = self.resources["Presets"]
            
        for item in source_list:
            if item.get("preset_type") == entity_type_name:
                matching.append(item)
        return matching

    def save_preset(self, entity, filename):
        """Save entity properties as a preset."""
        if not self.project_manager.current_project_path:
            return False, "No project open."
            
        # Ensure filename has extension
        if not filename.endswith(".json") and not filename.endswith(".preset"):
            filename += ".preset"
            
        # Determine folder based on entity type
        folder_name = "Presets"
        if entity.entity_type.name == "GENERATOR":
            folder_name = "Generators"
        elif entity.entity_type.name == "FILTER":
            folder_name = "Filters"
            
        target_dir = os.path.join(self.project_manager.current_project_path, folder_name)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            
        full_path = os.path.join(target_dir, filename)
        
        try:
            data = SceneSerializer.serialize_entity(entity)
            
            # Add metadata that it is a preset
            data["meta_type"] = "Preset"
            
            with open(full_path, 'w') as f:
                json.dump(data, f, indent=4)
                
            self.refresh() # Refresh UI
            return True, f"Preset saved to {filename}"
        except Exception as e:
            return False, f"Error saving preset: {e}"

    def read_preset_data(self, entity, preset_path):
        """Read and validate preset data for an entity."""
        try:
            with open(preset_path, 'r') as f:
                data = json.load(f)
                
            # Validation
            if data.get("type") != entity.entity_type.name:
                return None, f"Preset type mismatch. Expected {entity.entity_type.name}, got {data.get('type')}"
            
            return data.get("properties", {}), "Success"
        except Exception as e:
            return None, f"Error reading preset: {e}"

    def load_preset(self, entity, preset_path):
        """Apply preset properties to an entity (Directly)."""
        properties, msg = self.read_preset_data(entity, preset_path)
        if properties is None:
            return False, msg
            
        try:
            # 1. Apply "Type" first if exists
            if "Type" in properties:
                entity.set_property("Type", properties["Type"])
                
            for key, value in properties.items():
                if key != "Type": 
                    entity.set_property(key, value)
                        
            return True, "Preset loaded successfully."
            
        except Exception as e:
            return False, f"Error application preset: {e}"
