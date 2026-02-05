
import json
import os
import numpy as np
from PIL import Image

class BeamNGExporter:
    """
    Exports Terrain and Road data to BeamNG compatible formats.
    """
    def export_heightmap(self, terrain_data, filepath):
        """
        Exports heightmap as 16-bit grayscale PNG.
        """
        # BeamNG expects 16-bit PNG.
        # Height data needs to be normalized to 0-65535 range based on max height.
        # Usually BeamNG uses a terrain scaler. 
        # For simplicity, we'll map current min-max to full range or 0-max_height.
        
        hm = terrain_data.heightmap
        
        # Shift to positive only if needed, but usually 0 is sea level or base.
        # Let's assume input is generic floats.
        
        min_val = np.min(hm)
        max_val = np.max(hm)
        
        # Avoid div by zero
        if max_val == min_val:
            normalized = np.zeros_like(hm)
        else:
            normalized = (hm - min_val) / (max_val - min_val)
            
        # Scale to 16-bit
        # 65535
        uint16_data = (normalized * 65535).astype(np.uint16)
        
        image = Image.fromarray(uint16_data, mode='I;16')
        image.save(filepath)
        
        # Return metadata about scale for the .json
        return {
            "minHeight": float(min_val),
            "maxHeight": float(max_val),
            "size": terrain_data.size
        }

    def export_roads(self, road_network, filepath):
        """
        Exports roads to BeamNG lua/json format (DecalRoads).
        BeamNG uses a specific JSON structure for items in the level.
        
        Example item:
        {
            "class": "DecalRoad",
            "breakAngle": 3,
            "drivability": 1,
            "material": "road_asphalt_2line",
            "nodes": [
                [x, y, z, width],
                ...
            ],
            "position": [0,0,0],
            ...
        }
        """
        items = []
        
        # We need to reconstruct "roads" from the network segments.
        # Our RoadNetwork currently just has a list of nodes and segments.
        # If we treat the whole sequence as one road:
        
        if not road_network.nodes:
            with open(filepath, 'w') as f:
                json.dump([], f)
            return

        # Prepare nodes list: [x, y, z, width]
        # Note: BeamNG coordinates might be different (Z-up vs Y-up).
        # We are using Y-up in our tool (x, height, z).
        # BeamNG is Z-up? 
        # Usually Game Engines are:
        # Unity: Y-up
        # Unreal: Z-up
        # BeamNG (Torque3D): Z-up.
        
        # So inputs (x, y, z) in our tool (where y is height) -> (x, z, y) in BeamNG?
        # Let's check standard. If our viewport is Y-up, we are consistent.
        # If Beam is Z-up, we swap Y and Z on export.
        
        nodes_data = []
        for node in road_network.nodes:
            # Swap Y and Z for BeamNG (assuming Z-up export)
            # Tool: x, y=height, z
            # BeamNG: x, y=z, z=height
            
            # For now let's assume our Z in tool maps to Y in BeamNG (North)
            # and Y in tool maps to Z in BeamNG (Up).
            
            bx = node.position[0]
            by = node.position[2] 
            bz = node.position[1] # Height
            width = node.width
            
            nodes_data.append([bx, by, bz, width])
            
        road_item = {
            "class": "DecalRoad",
            "__parent": "MissionGroup",
            "material": "road_asphalt_2_lanes",
            "breakAngle": 3,
            "drivability": 1,
            "friction": 1,
            "nodes": nodes_data,
            "position": [0, 0, 0],
            "rotation": [0, 0, 0, 1],
            "scale": [1, 1, 1],
            "textureLength": 5
        }
        
        export_data = [road_item]
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=4)

