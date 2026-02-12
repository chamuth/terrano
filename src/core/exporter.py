"""
Export utilities for heightmaps, masks, and meshes.
Supports multiple formats (TIFF 32-bit, PNG 16-bit, JPEG 8-bit, OBJ mesh) and resolutions.
"""

import numpy as np
from PIL import Image
from scipy import ndimage
import os
from src.core.backend import to_cpu
from src.core.scene import EntityType


def resample_array(data, target_resolution):
    """
    Resample array to target resolution using high-quality interpolation.
    
    Args:
        data: 2D numpy array
        target_resolution: int, target size (assumes square)
    
    Returns:
        Resampled 2D numpy array
    """
    if data is None:
        return None
    
    # Ensure data is on CPU
    data = to_cpu(data)
    
    current_size = data.shape[0]
    if current_size == target_resolution:
        return data
    
    # Calculate zoom factor
    zoom_factor = target_resolution / current_size
    
    # Use high-quality spline interpolation
    resampled = ndimage.zoom(data, zoom_factor, order=3)
    
    return resampled


def export_heightmap(heightmap, filepath, resolution, format_str):
    """
    Export heightmap to file.
    
    Args:
        heightmap: 2D numpy array (heightmap data)
        filepath: str, output file path
        resolution: int, target resolution
        format_str: str, one of "TIFF (32-bit)", "PNG (16-bit)", "JPEG (8-bit)"
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Ensure data is on CPU
        data = to_cpu(heightmap)
        
        # Resample to target resolution
        data = resample_array(data, resolution)
        
        # Export based on format
        if format_str == "TIFF (32-bit)":
            # Save as 32-bit float TIFF (preserves full precision)
            img = Image.fromarray(data.astype(np.float32), mode='F')
            img.save(filepath, format='TIFF')
            
        elif format_str == "PNG (16-bit)":
            # Normalize to 0-65535 range for 16-bit PNG
            data_min = data.min()
            data_max = data.max()
            
            if data_max > data_min:
                normalized = (data - data_min) / (data_max - data_min) * 65535.0
            else:
                normalized = np.zeros_like(data)
            
            img = Image.fromarray(normalized.astype(np.uint16), mode='I;16')
            img.save(filepath, format='PNG')
            
        elif format_str == "JPEG (8-bit)":
            # Normalize to 0-255 range for 8-bit JPEG
            data_min = data.min()
            data_max = data.max()
            
            if data_max > data_min:
                normalized = (data - data_min) / (data_max - data_min) * 255.0
            else:
                normalized = np.zeros_like(data)
            
            img = Image.fromarray(normalized.astype(np.uint8), mode='L')
            img.save(filepath, format='JPEG', quality=95)
            
        else:
            return False, f"Unknown format: {format_str}"
        
        return True, f"Exported heightmap to {os.path.basename(filepath)}"
        
    except Exception as e:
        return False, f"Export failed: {str(e)}"


def export_mask(mask_data, filepath, resolution, format_str):
    """
    Export mask to file.
    
    Args:
        mask_data: 2D numpy array (mask data, 0-1 range)
        filepath: str, output file path
        resolution: int, target resolution
        format_str: str, one of "TIFF (32-bit)", "PNG (16-bit)", "JPEG (8-bit)"
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Ensure data is on CPU
        data = to_cpu(mask_data)
        
        # Resample to target resolution
        data = resample_array(data, resolution)
        
        # Ensure 0-1 range
        data = np.clip(data, 0.0, 1.0)
        
        # Export based on format
        if format_str == "TIFF (32-bit)":
            # Save as 32-bit float TIFF
            img = Image.fromarray(data.astype(np.float32), mode='F')
            img.save(filepath, format='TIFF')
            
        elif format_str == "PNG (16-bit)":
            # Convert to 16-bit PNG
            normalized = (data * 65535.0).astype(np.uint16)
            img = Image.fromarray(normalized, mode='I;16')
            img.save(filepath, format='PNG')
            
        elif format_str == "JPEG (8-bit)":
            # Convert to 8-bit JPEG
            normalized = (data * 255.0).astype(np.uint8)
            img = Image.fromarray(normalized, mode='L')
            img.save(filepath, format='JPEG', quality=95)
            
        else:
            return False, f"Unknown format: {format_str}"
        
        return True, f"Exported mask to {os.path.basename(filepath)}"
        
    except Exception as e:
        return False, f"Export failed: {str(e)}"


def export_mesh(heightmap, filepath, resolution, terrain_size):
    """
    Export terrain as OBJ mesh file.
    
    Args:
        heightmap: 2D numpy array (heightmap data)
        filepath: str, output file path (.obj)
        resolution: int, mesh resolution (vertex grid size)
        terrain_size: float, physical size of terrain
    
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # Ensure data is on CPU
        data = to_cpu(heightmap)
        
        # Resample to target resolution
        data = resample_array(data, resolution)
        
        # Generate mesh vertices and faces
        vertices = []
        faces = []
        
        # Calculate step size for terrain coordinates
        step = terrain_size / (resolution - 1)
        
        # Generate vertices
        for y in range(resolution):
            for x in range(resolution):
                # Calculate world position
                world_x = x * step - terrain_size / 2.0
                world_z = y * step - terrain_size / 2.0
                world_y = data[y, x]
                
                vertices.append((world_x, world_y, world_z))
        
        # Generate faces (two triangles per quad)
        for y in range(resolution - 1):
            for x in range(resolution - 1):
                # Vertex indices (OBJ uses 1-based indexing)
                v1 = y * resolution + x + 1
                v2 = y * resolution + (x + 1) + 1
                v3 = (y + 1) * resolution + x + 1
                v4 = (y + 1) * resolution + (x + 1) + 1
                
                # Two triangles per quad
                faces.append((v1, v2, v3))
                faces.append((v2, v4, v3))
        
        # Write OBJ file
        with open(filepath, 'w') as f:
            f.write("# Terrain mesh exported from Terrano\n")
            f.write(f"# Resolution: {resolution}x{resolution}\n")
            f.write(f"# Terrain size: {terrain_size}\n\n")
            
            # Write vertices
            for v in vertices:
                f.write(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n")
            
            f.write("\n")
            
            # Write faces
            for face in faces:
                f.write(f"f {face[0]} {face[1]} {face[2]}\n")
        
        return True, f"Exported mesh to {os.path.basename(filepath)}"
        
    except Exception as e:
        return False, f"Mesh export failed: {str(e)}"


def get_export_filename(entity, format_str):
    """
    Generate filename for entity export.
    Uses entity name if custom, otherwise entity ID.
    
    Args:
        entity: Entity object
        format_str: str, format string like "TIFF (32-bit)"
    
    Returns:
        str: filename with extension
    """
    # Determine extension from format
    if "TIFF" in format_str:
        ext = ".tiff"
    elif "PNG" in format_str:
        ext = ".png"
    elif "JPEG" in format_str:
        ext = ".jpg"
    elif "OBJ" in format_str:
        ext = ".obj"
    else:
        ext = ".tiff"
    
    # Use entity name if custom, otherwise ID
    if hasattr(entity, '_has_custom_name') and entity._has_custom_name:
        # Sanitize filename
        filename = entity.name.replace("/", "_").replace("\\", "_")
    else:
        filename = entity.id
    
    return filename + ext


def export_all(root_entity, render_data, output_folder, progress_callback=None):
    """
    Batch export all terrain and mask entities.
    
    Args:
        root_entity: Root terrain entity
        render_data: TerrainData object with current heightmap
        output_folder: str, output directory path
        progress_callback: callable(entity_name, current, total), optional
    
    Returns:
        tuple: (success: bool, message: str, exported_files: list)
    """
    try:
        # Create output folder if it doesn't exist
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        # Collect all exportable entities
        exportable = []
        
        def collect_entities(entity):
            if entity.entity_type == EntityType.ROOT:
                # Export terrain heightmap
                exportable.append(('terrain', entity))
            elif entity.entity_type == EntityType.MASK:
                # Export mask
                exportable.append(('mask', entity))
            
            # Recurse
            for child in entity.get_children():
                collect_entities(child)
        
        collect_entities(root_entity)
        
        if not exportable:
            return False, "No exportable entities found", []
        
        # Export each entity
        exported_files = []
        total = len(exportable)
        
        for idx, (entity_type, entity) in enumerate(exportable):
            # Get export settings from entity
            resolution = int(entity.get_property("Export Resolution"))
            format_str = entity.get_property("Export Format")
            filename = entity.get_property("Export Filename").strip()
            export_dir = entity.get_property("Export Directory").strip()
            
            # Use entity ID/name if no filename
            if not filename:
                if hasattr(entity, '_has_custom_name') and entity._has_custom_name:
                    filename = entity.name
                else:
                    filename = entity.id
            
            # Add extension based on format
            if "TIFF" in format_str:
                ext = ".tiff"
            elif "PNG" in format_str:
                ext = ".png"
            elif "JPEG" in format_str:
                ext = ".jpg"
            elif "OBJ" in format_str:
                ext = ".obj"
            else:
                ext = ".tiff"
            
            if not filename.endswith(ext):
                filename += ext
            
            # Build full path
            if export_dir:
                # Use entity's export directory (relative to output folder)
                full_output_dir = os.path.join(output_folder, export_dir)
                if not os.path.exists(full_output_dir):
                    os.makedirs(full_output_dir)
                filepath = os.path.join(full_output_dir, filename)
            else:
                filepath = os.path.join(output_folder, filename)
            
            # Progress callback
            if progress_callback:
                entity_name = entity.name if hasattr(entity, 'name') else str(entity.id)
                progress_callback(entity_name, idx + 1, total)
            
            # Export
            if entity_type == 'terrain':
                if "OBJ" in format_str:
                    # Export as mesh
                    terrain_size = entity.get_property("Size")
                    success, msg = export_mesh(render_data.heightmap, filepath, resolution, terrain_size)
                else:
                    # Export as heightmap
                    success, msg = export_heightmap(render_data.heightmap, filepath, resolution, format_str)
            else:  # mask
                # Generate mask
                res = int(root_entity.get_property("Resolution"))
                size = root_entity.get_property("Size")
                
                if hasattr(render_data, 'heightmap') and render_data.heightmap is not None:
                    heightmap = render_data.heightmap
                    mask = entity.generate_mask(heightmap, size)
                else:
                    mask = entity.generate_mask((res, res), size)
                
                success, msg = export_mask(mask, filepath, resolution, format_str)
            
            if success:
                exported_files.append(filepath)
        
        summary = f"Exported {len(exported_files)} file(s) to {output_folder}"
        return True, summary, exported_files
        
    except Exception as e:
        return False, f"Batch export failed: {str(e)}", []
