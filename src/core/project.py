import os
import json
from src.core.serializer import SceneSerializer

class ProjectManager:
    def __init__(self):
        self.current_project_path = None # Folder path
        self.is_dirty = False
        self.project_name = "Untitled"
        
    def new_project(self):
        """Reset state."""
        self.current_project_path = None
        self.is_dirty = False
        self.project_name = "Untitled"
        
    def save_project(self, root_entity, folder_path):
        """Save project to the specified folder."""
        try:
            # 1. Determine filename
            # The project name is the folder name usually? Or we use 'project.json'?
            # User requirement: "{project_name}.json at the root of project folder"
            # If folder_path is ".../MyTerrain", then "MyTerrain.json"
            
            project_name = os.path.basename(os.path.normpath(folder_path))
            file_path = os.path.join(folder_path, f"{project_name}.terrano")
            
            # 2. Serialize
            data = SceneSerializer.serialize_tree(root_entity)
            
            # 3. Write
            # Create folder if not exists (though user likely selected an existing one)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
                
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
                
            self.current_project_path = folder_path
            self.project_name = project_name
            self.is_dirty = False
            return True, "Project saved successfully."
            
        except Exception as e:
            return False, f"Error saving project: {str(e)}"

    def load_project(self, file_path):
        """Load project from a JSON file."""
        try:
            if not os.path.exists(file_path):
                return None, "File not found."
                
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            root_entity = SceneSerializer.deserialize_tree(data)
            
            # Update state
            # Folder is dirname of file
            self.current_project_path = os.path.dirname(file_path)
            # Project name is filename no ext
            self.project_name = os.path.splitext(os.path.basename(file_path))[0]
            self.is_dirty = False
            
            return root_entity, "Project loaded."
            
        except Exception as e:
            return None, f"Error loading project: {str(e)}"
