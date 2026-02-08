import numpy as np
from src.core.backend import xp, ndimage, to_cpu, to_device, synchronize
from PIL import Image
# from scipy.ndimage import gaussian_filter, laplace # Removed, using backend.ndimage
import os
import uuid
import time
from enum import Enum
from PyQt6.QtCore import QObject, pyqtSignal

class EntityType(Enum):
    ROOT = 0
    GENERATOR = 1
    FILTER = 2
    MASK = 3

class Entity(QObject):
    # Signal when properties change so Inspector/Viewport can update
    changed = pyqtSignal()
    renamed = pyqtSignal() # Signal specifically for renaming (no recompute needed)
    structure_changed = pyqtSignal() # When children are added/removed
    status_changed = pyqtSignal(object) # Emit self when is_dirty changes

    def __init__(self, name="Entity", parent=None, entity_type=EntityType.ROOT):
        super().__init__()
        self.id = str(uuid.uuid4())
        self._name = name
        self.entity_type = entity_type
        self._parent = None
        self._children = []
        
        # Track if user has manually renamed this entity
        self._has_custom_name = False
        
        # _enabled is now redundant with properties["Enabled"], but helpful for quick access
        # However, plan says "Add property" so UI can see it.
        # We'll sync them.
        
        # Generic Properties Dictionary using a custom schema
        # { "prop_name": { "type": float, "value": 1.0, "min": 0, "max": 100, "options": [] } }
        self.properties = {} 
        
        # Add Enabled Property (default True)
        self.define_property("Enabled", bool, True)

        if parent:
            self.set_parent(parent)
            
        # Caching
        self.is_dirty = True
        self._cached_output = None
        self.last_input_version = None
        self.cache_dir = os.path.join(os.getcwd(), ".cache")
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
            
    def set_cache_dir(self, directory, recursive=True):
        """Update cache directory (e.g. when project is saved/loaded)"""
        self.cache_dir = directory
        if not os.path.exists(self.cache_dir):
             os.makedirs(self.cache_dir, exist_ok=True)
             
        if recursive:
            for child in self._children:
                child.set_cache_dir(directory, recursive=True)
            
    def mark_dirty(self):
        # Always emit changed because properties changed
        self.changed.emit()
        
        if self.is_dirty:
            return
            
        self.is_dirty = True
        self.status_changed.emit(self)
        
        if self._parent:
            self._parent.mark_dirty()
        
    def get_cache_path(self):
        return os.path.join(self.cache_dir, f"{self.id}.npy")

    def save_cache(self, data):
        try:
            # Validating data is on CPU before saving (numpy.save requires it)
            cpu_data = to_cpu(data)
            np.save(self.get_cache_path(), cpu_data)
        except Exception as e:
            print(f"Failed to save cache for {self.name}: {e}")

    def load_cache(self):
        path = self.get_cache_path()
        if os.path.exists(path):
            try:
                return np.load(path)
            except:
                return None
        return None
            
    @property
    def name(self):
        return self._name
        
    @name.setter
    def name(self, value):
        if self._name != value:
            self._name = value
            self._has_custom_name = True
            self.renamed.emit()
            
    def set_name_automatic(self, new_name):
        """Sets name ONLY if user hasn't customized it."""
        if not self._has_custom_name and self._name != new_name:
            self._name = new_name
            self.renamed.emit()

    def set_parent(self, parent):
        if self._parent == parent:
            return

        if self._parent:
            self._parent.remove_child(self)
        
        self._parent = parent
        if self._parent:
            self._parent.add_child(self)
    
    def add_child(self, child, index=-1):
        if child not in self._children:
            if index != -1 and 0 <= index <= len(self._children):
                self._children.insert(index, child)
            else:
                self._children.append(child)
            child._parent = self
            
            try:
                child.changed.connect(self.on_child_changed)
                child.structure_changed.connect(self.on_child_structure_changed)
            except:
                pass
                
            # Propagate cache dir
            child.set_cache_dir(self.cache_dir, recursive=True)
            
            self.mark_dirty()
            self.structure_changed.emit()
            
    def remove_child(self, child):
        if child in self._children:
            # Disconnect bubbling
            try:
                child.changed.disconnect(self.on_child_changed)
                child.structure_changed.disconnect(self.on_child_structure_changed)
            except:
                pass

            self._children.remove(child)
            child._parent = None
            self.mark_dirty()
            self.structure_changed.emit()

    def on_child_changed(self):
        self.mark_dirty()

    def on_child_structure_changed(self):
        # Bubble up structure changes
        self.structure_changed.emit()

    def get_children(self):
        return self._children

    def process(self, input_heightmap, mask=None, terrain_size=1000.0, input_version=None):
        """
        Recursive processing pipeline.
        input_heightmap: Input array (READ ONLY ideally, or copy).
        mask: The current scoped mask.
        terrain_size: Physical size.
        input_version: Unique ID of the input data state.
        Returns: (output_heightmap, output_version)
        """
        if not self.get_property("Enabled"):
            # Pass through input
            return input_heightmap, input_version

        # 1. Caching Check
        if not self.is_dirty and input_version is not None and input_version == self.last_input_version:
            if self._cached_output is not None:
                # Ensure cached output is on the correct device
                return to_device(self._cached_output), self.id
            
            loaded = self.load_cache()
            if loaded is not None:
                self._cached_output = loaded
                return to_device(loaded), self.id

        # 2. Process
        # Copy input to avoid mutating ancestor's buffer
        if input_heightmap is not None:
             # Ensure input is on device
             input_heightmap = to_device(input_heightmap)
             current_heightmap = input_heightmap.copy()
        else:
             current_heightmap = None
        
        # Self Logic
        if current_heightmap is not None:
             self.on_process(current_heightmap, mask, terrain_size)
        
        # Children Logic
        # We generate a strict version ID for the flow between children
        current_version = str(uuid.uuid4())
        
        if self.entity_type != EntityType.MASK:
            for child in self._children:
                current_heightmap, current_version = child.process(current_heightmap, mask, terrain_size, current_version)
                
        # 3. Update Cache
        # Store on CPU to save VRAM? Or keep on GPU for speed?
        # Let's keep on CPU for cache to save VRAM, but this means to_cpu every time?
        # Actually, self._cached_output should probably match output device for speed.
        # But if VRAM is tight... let's keep it on same device as execution.
        self._cached_output = current_heightmap
        self.last_input_version = input_version
        
        if self.is_dirty:
            self.is_dirty = False
            self.status_changed.emit(self) # Notify UI we are clean
            
        self.save_cache(current_heightmap)
        
        # Our output version is roughly our ID + input_version? 
        # Or just a new unique ID since we just recomputed.
        return current_heightmap, str(uuid.uuid4())

    def on_process(self, heightmap, mask, terrain_size):
        pass

    def define_property(self, name, dtype, value, min_val=None, max_val=None, options=None, group="General"):
        self.properties[name] = {
            "type": dtype,
            "value": value,
            "min": min_val,
            "max": max_val,
            "options": options, # For Dropdowns (list of strings)
            "visible": True,
            "group": group
        }

    def set_property(self, name, value):
        if name in self.properties:
            # Type safety check could go here
            self.properties[name]["value"] = value
            self.on_property_changed(name, value)

            self.mark_dirty()
            # self.changed.emit() # mark_dirty emits changed
            
    def set_property_visible(self, name, visible):
        if name in self.properties:
            if self.properties[name].get("visible", True) != visible:
                self.properties[name]["visible"] = visible
                self.changed.emit() # Rebuild inspector
    
    def get_property(self, name):
        return self.properties[name]["value"]
        
    def on_property_changed(self, name, value):
        pass


class TerrainEntity(Entity):
    def __init__(self):
        super().__init__("Terrain", entity_type=EntityType.ROOT)
        # Resolution as options
        self.define_property("Resolution", str, "512", options=["512", "1024", "2048", "4096"], group="Dimensions")
        self.define_property("Size", float, 1000.0, 100.0, 10000.0, group="Dimensions") # Physical Size
        self.define_property("Base Height", float, 0.0, -1000.0, 1000.0, group="General")
        
    def on_process(self, heightmap, mask, terrain_size):
        # Base terrain just clears the heightmap to base height
        # But commonly Generators will overwrite this immediately.
        # If no generators, we likely want a flat plane.
        
        # Note: Resolution change handling usually is done at the worker/engine level
        # before processing starts, to resize the array.
        
        base = self.get_property("Base Height")
        # We assume heightmap is already allocated to correct size by the Engine
        heightmap[:] = base

    def on_property_changed(self, name, value):
        if name == "Resolution":
            # Engine needs to know to resize
            pass


class GeneratorEntity(Entity):
    def __init__(self, name="Generator"):
        super().__init__(name, entity_type=EntityType.GENERATOR)
        self.define_property("Type", str, "Perlin Noise", options=[
            "Perlin Noise", "Simplex Noise", "Gabor Noise", "Alligator Noise", 
            "Voronoi", "Pattern", "Constant"
        ], group="General")
        
        # Check if name is generic, if so, auto-name immediately
        if name in ["Generator", "New Generator"]:
            self.set_name_automatic("Perlin Noise")
            
        self.define_property("Strength", float, 1.0, 0.0, 1.0, group="General")
        self.define_property("Operation", str, "Add", options=["Add", "Subtract", "Replace", "Multiply"], group="General")
        
        # Common properties (Perlin, Simplex)
        self.define_property("Scale", float, 100.0, 10.0, 1000.0, group="Fractal Settings")
        self.define_property("Octaves", int, 6, 1, 12, group="Fractal Settings")
        self.define_property("Persistence", float, 0.5, 0.0, 1.0, group="Fractal Settings")
        self.define_property("Lacunarity", float, 2.0, 1.0, 4.0, group="Fractal Settings")
        self.define_property("Perlin Style", str, "Standard", options=["Standard", "Billowy", "Ridged", "Plateau"], group="Fractal Settings")
        self.define_property("Amplitude", float, 50.0, 0.0, 1000.0, group="General")
        self.define_property("Seed", int, 42, 0, 99999, group="General")
        self.define_property("Height Offset", float, 0.0, -500.0, 500.0, group="General")
        
        # Gabor properties
        self.define_property("Gabor Frequency", float, 0.05, 0.01, 0.2, group="Gabor Settings")
        self.define_property("Gabor Orientation", float, 0.0, -180.0, 180.0, group="Gabor Settings")
        self.define_property("Gabor Bandwidth", float, 1.0, 0.1, 5.0, group="Gabor Settings")
        self.define_property("Gabor Impulses", int, 50, 10, 200, group="Gabor Settings")
        
        # Alligator properties
        self.define_property("Alligator Scale", float, 100.0, 10.0, 500.0, group="Alligator Settings")
        self.define_property("Alligator Jitter", float, 1.0, 0.0, 1.0, group="Alligator Settings")
        
        # Voronoi properties
        self.define_property("Voronoi Scale", float, 100.0, 10.0, 500.0, group="Voronoi Settings")
        self.define_property("Voronoi Metric", str, "F1", options=["F1", "F2", "F2-F1"], group="Voronoi Settings")
        self.define_property("Distance Type", str, "euclidean", options=["euclidean", "manhattan", "chebyshev"], group="Voronoi Settings")
        self.define_property("Invert Voronoi", bool, False, group="Voronoi Settings")
        
        # Pattern properties
        self.define_property("Pattern Type", str, "Linear Ramp", options=["Linear Ramp", "Radial", "Grid", "Checker"], group="Pattern Settings")
        self.define_property("Pattern Direction", float, 0.0, -180.0, 180.0, group="Pattern Settings")
        self.define_property("Pattern Center X", float, 0.5, 0.0, 1.0, group="Pattern Settings")
        self.define_property("Pattern Center Y", float, 0.5, 0.0, 1.0, group="Pattern Settings")
        self.define_property("Pattern Frequency", float, 4.0, 1.0, 20.0, group="Pattern Settings")
        
        # Initial Update
        self.update_property_visibility()

    def on_property_changed(self, name, value):
        if name == "Type":
            self.update_property_visibility()
            self.set_name_automatic(value)
        # Mark dirty on any property change

        self.mark_dirty()

    def update_property_visibility(self):
        gen_type = self.get_property("Type")
        
        # Common
        self.set_property_visible("Strength", True)
        self.set_property_visible("Operation", True)
        self.set_property_visible("Seed", gen_type != "Constant" and gen_type != "Pattern")
        self.set_property_visible("Amplitude", gen_type != "Constant")
        self.set_property_visible("Height Offset", True)
        
        # Perlin / Simplex
        is_fractal = gen_type in ["Perlin Noise", "Simplex Noise"]
        self.set_property_visible("Scale", is_fractal)
        self.set_property_visible("Octaves", is_fractal)
        self.set_property_visible("Persistence", is_fractal)
        self.set_property_visible("Lacunarity", is_fractal)
        # Style only for Perlin
        self.set_property_visible("Perlin Style", gen_type == "Perlin Noise")
        
        # Gabor
        is_gabor = gen_type == "Gabor Noise"
        self.set_property_visible("Gabor Frequency", is_gabor)
        self.set_property_visible("Gabor Orientation", is_gabor)
        self.set_property_visible("Gabor Bandwidth", is_gabor)
        self.set_property_visible("Gabor Impulses", is_gabor)
        
        # Alligator
        is_alligator = gen_type == "Alligator Noise"
        self.set_property_visible("Alligator Scale", is_alligator)
        self.set_property_visible("Alligator Jitter", is_alligator)
        
        # Voronoi
        is_voronoi = gen_type == "Voronoi"
        self.set_property_visible("Voronoi Scale", is_voronoi)
        self.set_property_visible("Voronoi Metric", is_voronoi)
        self.set_property_visible("Distance Type", is_voronoi)
        self.set_property_visible("Invert Voronoi", is_voronoi)
        
        # Pattern
        is_pattern = gen_type == "Pattern"
        self.set_property_visible("Pattern Type", is_pattern)
        self.set_property_visible("Pattern Direction", is_pattern)
        self.set_property_visible("Pattern Center X", is_pattern)
        self.set_property_visible("Pattern Center Y", is_pattern)
        self.set_property_visible("Pattern Frequency", is_pattern)

    def on_process(self, heightmap, mask, terrain_size):
        gen_type = self.get_property("Type")
        op = self.get_property("Operation")
        strength = self.get_property("Strength")
        
        # Ensure correct backend array initialization
        generated = xp.zeros_like(heightmap)
        
        # Temporary var to hold raw generator output (likely NumPy)
        raw_generated = None
        
        if gen_type == "Perlin Noise":
            from src.generators.perlin_noise import PerlinNoiseGenerator
            scale = self.get_property("Scale")
            octaves = self.get_property("Octaves")
            pers = self.get_property("Persistence")
            lac = self.get_property("Lacunarity")
            seed = self.get_property("Seed")
            amp = self.get_property("Amplitude")
            offset = self.get_property("Height Offset")
            style = self.get_property("Perlin Style")
            
            gen = PerlinNoiseGenerator(scale, octaves, pers, lac, seed, amp, style)
            # Generators usually return numpy array.
            raw_generated = gen.generate(heightmap.shape[0], terrain_size) + offset
            
        elif gen_type == "Simplex Noise":
            from src.generators.noise_library import SimplexNoiseGenerator
            scale = self.get_property("Scale")
            octaves = self.get_property("Octaves")
            pers = self.get_property("Persistence")
            lac = self.get_property("Lacunarity")
            seed = self.get_property("Seed")
            amp = self.get_property("Amplitude")
            offset = self.get_property("Height Offset")
            
            gen = SimplexNoiseGenerator(scale, octaves, pers, lac, seed, amp)
            raw_generated = gen.generate(heightmap.shape[0], terrain_size) + offset
            
        elif gen_type == "Gabor Noise":
            from src.generators.noise_library import GaborNoiseGenerator
            freq = self.get_property("Gabor Frequency")
            orient = self.get_property("Gabor Orientation")
            bandwidth = self.get_property("Gabor Bandwidth")
            impulses = self.get_property("Gabor Impulses")
            seed = self.get_property("Seed")
            amp = self.get_property("Amplitude")
            
            gen = GaborNoiseGenerator(freq, orient, bandwidth, impulses, seed, amp)
            raw_generated = gen.generate(heightmap.shape[0], terrain_size)
            
        elif gen_type == "Alligator Noise":
            from src.generators.noise_library import AlligatorNoiseGenerator
            scale = self.get_property("Alligator Scale")
            jitter = self.get_property("Alligator Jitter")
            seed = self.get_property("Seed")
            amp = self.get_property("Amplitude")
            
            gen = AlligatorNoiseGenerator(scale, jitter, seed, amp)
            raw_generated = gen.generate(heightmap.shape[0], terrain_size)
            
        elif gen_type == "Voronoi":
            from src.generators.noise_library import VoronoiGenerator
            scale = self.get_property("Voronoi Scale")
            metric = self.get_property("Voronoi Metric")
            dist_type = self.get_property("Distance Type")
            seed = self.get_property("Seed")
            amp = self.get_property("Amplitude")
            invert = self.get_property("Invert Voronoi")
            
            gen = VoronoiGenerator(scale, metric, dist_type, seed, amp, invert)
            raw_generated = gen.generate(heightmap.shape[0], terrain_size)
            
        elif gen_type == "Pattern":
            from src.generators.noise_library import PatternGenerator
            pattern_type = self.get_property("Pattern Type")
            direction = self.get_property("Pattern Direction")
            center_x = self.get_property("Pattern Center X")
            center_y = self.get_property("Pattern Center Y")
            frequency = self.get_property("Pattern Frequency")
            amp = self.get_property("Amplitude")
            
            gen = PatternGenerator(pattern_type, direction, (center_x, center_y), frequency, amp)
            raw_generated = gen.generate(heightmap.shape[0], terrain_size)
            
        elif gen_type == "Constant":
            offset = self.get_property("Height Offset")
            # Fill directly on GPU if relevant
            generated[:] = offset
            
        # Move raw_generated to device
        if raw_generated is not None:
            generated = to_device(raw_generated)

        # Blend Logic
        # Apply mask
        eff_mask = mask if mask is not None else 1.0
        
        if op == "Replace":
            # Lerp: Current * (1 - strength*mask) + New * (strength*mask)
            alpha = strength * eff_mask
            heightmap[:] = heightmap * (1.0 - alpha) + generated * alpha
            
        elif op == "Add":
            heightmap += generated * strength * eff_mask
            
        elif op == "Subtract":
            heightmap -= generated * strength * eff_mask
            
        elif op == "Multiply":
            # Lerp towards multiply result
            # Target = Current * New
            target = heightmap * generated
            alpha = strength * eff_mask
            heightmap[:] = heightmap * (1.0 - alpha) + target * alpha



class FilterEntity(Entity):
    def __init__(self, name="Filter"):
        super().__init__(name, entity_type=EntityType.FILTER)
        self.define_property("Type", str, "Erosion", options=[
            "Erosion", "Thermal", "Smooth", "Sharpen", 
            "Distort by Noise", "Terrace", "Clip", "River"
        ], group="General")
        
        # Check if name is generic, if so, auto-name immediately
        if name in ["Filter", "New Filter"]:
             self.set_name_automatic("Erosion")
        
        # Hydraulic Erosion
        self.define_property("H-Iterations", int, 50, 1, 200, group="Hydraulic Erosion")
        self.define_property("H-Rain Amount", float, 0.01, 0.0, 1.0, group="Hydraulic Erosion")
        self.define_property("H-Sediment Capacity", float, 0.05, 0.0, 1.0, group="Hydraulic Erosion")
        self.define_property("H-Erosion Rate", float, 0.01, 0.0, 1.0, group="Hydraulic Erosion")
        self.define_property("H-Deposition Rate", float, 0.01, 0.0, 1.0, group="Hydraulic Erosion")
        self.define_property("H-Evaporation Rate", float, 0.02, 0.0, 1.0, group="Hydraulic Erosion")
        
        # Thermal Erosion
        self.define_property("T-Iterations", int, 10, 1, 100, group="Thermal Erosion")
        self.define_property("T-Strength", float, 0.5, 0.0, 1.0, group="Thermal Erosion")
        self.define_property("T-Talus Angle", float, 45.0, 0.0, 90.0, group="Thermal Erosion")
        
        # Smooth / Sharpen
        self.define_property("Smooth Sigma", float, 2.0, 0.1, 10.0, group="Smooth Settings")
        self.define_property("Sharpen Sigma", float, 2.0, 0.1, 10.0, group="Sharpen Settings")
        self.define_property("Sharpen Strength", float, 1.0, 0.0, 5.0, group="Sharpen Settings")
        
        # Distort by Noise
        self.define_property("Distort Noise Type", str, "Perlin", options=["Perlin", "Simplex", "Curl"], group="Distortion")
        self.define_property("Distort Amplitude", float, 10.0, 0.1, 100.0, group="Distortion")
        self.define_property("Distort Element Size", float, 50.0, 10.0, 500.0, group="Distortion")
        self.define_property("Distort Substeps", int, 3, 1, 10, group="Distortion")
        self.define_property("Distort Seed", int, 42, 0, 99999, group="Distortion")
        
        # Terrace
        self.define_property("Terrace Step Count", int, 10, 2, 50, group="Terracing")
        self.define_property("Terrace Smoothness", float, 0.1, 0.0, 1.0, group="Terracing")
        
        # Clip
        self.define_property("Clip Min Height", float, -100.0, -1000.0, 1000.0, group="Clipping")
        self.define_property("Clip Max Height", float, 100.0, -1000.0, 1000.0, group="Clipping")
        self.define_property("Clip Soft Strength", float, 0.2, 0.0, 1.0, group="Clipping")
        self.define_property("Use Min Clip", bool, False, group="Clipping")
        self.define_property("Use Max Clip", bool, False, group="Clipping")
        
        # River
        self.define_property("River Threshold", float, 100.0, 1.0, 10000.0, group="River Settings")
        self.define_property("River Strength", float, 5.0, 0.1, 50.0, group="River Settings")
        self.define_property("River Width", float, 1.0, 0.0, 10.0, group="River Settings")

        # Initial Update
        self.update_visibility()

    def on_property_changed(self, name, value):
        if name == "Type":
            self.update_visibility()
            self.set_name_automatic(value)
        self.mark_dirty()

    def update_visibility(self):
        f_type = self.get_property("Type")
        
        # Hydraulic / Simple Erosion
        is_erosion = (f_type == "Erosion")
        self.set_property_visible("H-Iterations", is_erosion)
        self.set_property_visible("H-Rain Amount", is_erosion)
        self.set_property_visible("H-Sediment Capacity", is_erosion)
        self.set_property_visible("H-Erosion Rate", is_erosion)
        self.set_property_visible("H-Deposition Rate", is_erosion)
        self.set_property_visible("H-Evaporation Rate", is_erosion)
        
        # Thermal
        is_thermal = (f_type == "Thermal")
        self.set_property_visible("T-Iterations", is_thermal)
        self.set_property_visible("T-Strength", is_thermal)
        self.set_property_visible("T-Talus Angle", is_thermal)
        
        # Distortion
        is_distort = (f_type == "Distort by Noise")
        self.set_property_visible("Distort Noise Type", is_distort)
        self.set_property_visible("Distort Amplitude", is_distort)
        self.set_property_visible("Distort Element Size", is_distort)
        self.set_property_visible("Distort Substeps", is_distort)
        self.set_property_visible("Distort Seed", is_distort)
        
        # Terrace
        is_terrace = (f_type == "Terrace")
        self.set_property_visible("Terrace Step Count", is_terrace)
        self.set_property_visible("Terrace Smoothness", is_terrace)
        
        # Clip
        is_clip = (f_type == "Clip")
        self.set_property_visible("Clip Min Height", is_clip)
        self.set_property_visible("Clip Max Height", is_clip)
        self.set_property_visible("Clip Soft Strength", is_clip)
        self.set_property_visible("Use Min Clip", is_clip)
        self.set_property_visible("Use Max Clip", is_clip)
        
        # Smooth
        is_smooth = (f_type == "Smooth")
        self.set_property_visible("Smooth Sigma", is_smooth)
        
        # Sharpen
        is_sharpen = (f_type == "Sharpen")
        self.set_property_visible("Sharpen Sigma", is_sharpen)
        self.set_property_visible("Sharpen Strength", is_sharpen)
        
        # River
        is_river = (f_type == "River")
        self.set_property_visible("River Threshold", is_river)
        self.set_property_visible("River Strength", is_river)
        self.set_property_visible("River Width", is_river)
        
    def on_process(self, heightmap, mask, terrain_size):
        f_type = self.get_property("Type")
        
        if f_type == "River":
            from src.core.hydrology import fill_sinks, compute_flow_accumulation, carve_rivers
            
            # 1. Fill Sinks (CPU-heavy)
            filled = fill_sinks(heightmap)
            
            # 2. Flow Accumulation (CPU-heavy)
            acc = compute_flow_accumulation(filled)
            
            # 3. Carve (GPU/CPU)
            threshold = self.get_property("River Threshold")
            strength = self.get_property("River Strength")
            width = self.get_property("River Width")
            
            result = carve_rivers(heightmap, acc, threshold, strength, width)
            
            # Update heightmap in place (or copy back)
            # Since carve_rivers likely returns a new array (on device), we copy it back
            # Ensure shape matches
            heightmap[:] = result
            
            return

        if f_type == "Erosion":
            # Hydraulic Erosion (Pipe Model / Shallow Water)
            rain_amount = self.get_property("H-Rain Amount")
            passes = self.get_property("H-Iterations")
            k_cap = self.get_property("H-Sediment Capacity")
            k_erode = self.get_property("H-Erosion Rate")
            k_dep = self.get_property("H-Deposition Rate")
            k_evap = self.get_property("H-Evaporation Rate")
            
            # Initialization
            water = xp.zeros_like(heightmap)
            sediment = xp.zeros_like(heightmap)
            h, w = heightmap.shape
            
            # Precompute neighbor offsets for vectorization
            # N, S, W, E
            
            for _ in range(passes):
                # 1. Add Water (Rain)
                # Normalize water to prevent explosion
                xp.clip(water, 0, 1000.0, out=water)
                
                # Only rain on unmasked areas if mask is present, or globally
                if mask is not None:
                     water += rain_amount * mask
                else:
                     water += rain_amount
                
                # 2. Flux Calculation (Outflow)
                # Height + Water = Total Height
                total_height = heightmap + water
                
                # Calculate diffs
                # Pad for boundary - Use constant (abyss) to allow drainage!
                padded = xp.pad(total_height, 1, mode='constant', constant_values=-10000.0)
                
                d_n = total_height - padded[:-2, 1:-1]
                d_s = total_height - padded[2:, 1:-1]
                d_w = total_height - padded[1:-1, :-2]
                d_e = total_height - padded[1:-1, 2:]
                
                # Flux (only flow to lower)
                flux_n = xp.maximum(0, d_n)
                flux_s = xp.maximum(0, d_s)
                flux_w = xp.maximum(0, d_w)
                flux_e = xp.maximum(0, d_e)
                
                # Normalize flux to prevent negative water
                flux_sum = flux_n + flux_s + flux_w + flux_e
                
                # Avoid div by zero
                flux_sum_safe = xp.maximum(flux_sum, 1e-6)
                
                # If sum > water, scale down magnitude
                scale_factor = xp.minimum(1.0, water / flux_sum_safe)
                
                # Sanity check scale factor
                scale_factor = xp.nan_to_num(scale_factor)
                
                flux_n *= scale_factor
                flux_s *= scale_factor
                flux_w *= scale_factor
                flux_e *= scale_factor
                
                # Clamp fluxes to be safe
                flux_n = xp.nan_to_num(flux_n)
                flux_s = xp.nan_to_num(flux_s)
                flux_w = xp.nan_to_num(flux_w)
                flux_e = xp.nan_to_num(flux_e)
                
                # 3. Water Transport
                # Calculate inflow from neighbors (Note: Inflow N comes from S neighbor of N-shifted cell)
                inflow = xp.zeros_like(water)
                
                # Outflow
                outflow = flux_n + flux_s + flux_w + flux_e
                
                # Inflow logic:
                pad_Fn = xp.pad(flux_n, ((1,1),(0,0)), mode='constant')
                pad_Fs = xp.pad(flux_s, ((1,1),(0,0)), mode='constant')
                pad_Fw = xp.pad(flux_w, ((0,0),(1,1)), mode='constant')
                pad_Fe = xp.pad(flux_e, ((0,0),(1,1)), mode='constant')
                
                in_n = pad_Fs[:-2, :] # Flux S from N neighbor
                in_s = pad_Fn[2:, :]  # Flux N from S neighbor
                in_w = pad_Fe[:, :-2] # Flux E from W neighbor
                in_e = pad_Fw[:, 2:]  # Flux W from E neighbor
                
                inflow = in_n + in_s + in_w + in_e
                
                water += (inflow - outflow)
                
                # 4. Erosion / Deposition
                # Velocity estimation based on total flux
                flux_avg = (inflow + outflow) * 0.5
                
                velocity = flux_avg / (water + 1.0)
                
                # Sediment Capacity
                capacity = k_cap * velocity
                
                # Erosion/Deposition
                diff = capacity - sediment
                
                # Erode (add to sediment, remove from terrain)
                erode_amt = xp.maximum(0, diff * k_erode)
                
                # Deposit (remove from sediment, add to terrain)
                deposit_amt = xp.maximum(0, -diff * k_dep)
                
                # Masking application:
                change = deposit_amt - erode_amt
                
                if mask is not None:
                     change *= mask
                
                heightmap += change
                sediment -= change
                
                # 5. Sediment Transport
                total_water_safe = xp.maximum(water, 1e-6)
                
                # Ratio of water leaving in each direction
                r_n = flux_n / total_water_safe
                r_s = flux_s / total_water_safe
                r_w = flux_w / total_water_safe
                r_e = flux_e / total_water_safe
                
                # Sanity check ratios
                r_n = xp.clip(xp.nan_to_num(r_n), 0, 1)
                r_s = xp.clip(xp.nan_to_num(r_s), 0, 1)
                r_w = xp.clip(xp.nan_to_num(r_w), 0, 1)
                r_e = xp.clip(xp.nan_to_num(r_e), 0, 1)
                
                # Clamp sediment before multiplication to avoid overflow
                xp.clip(sediment, 0, 1000.0, out=sediment)
                
                sem_out = sediment * (r_n + r_s + r_w + r_e)
                
                # Inflow calculation similar to water
                pad_sem = xp.pad(sediment, 1, mode='constant')
                
                # Precalc Outflow Sediment per direction
                s_out_n = sediment * r_n
                s_out_s = sediment * r_s
                s_out_w = sediment * r_w
                s_out_e = sediment * r_e
                
                pad_Son = xp.pad(s_out_n, ((1,1),(0,0)), mode='constant')
                pad_Sos = xp.pad(s_out_s, ((1,1),(0,0)), mode='constant')
                pad_Sow = xp.pad(s_out_w, ((0,0),(1,1)), mode='constant')
                pad_Soe = xp.pad(s_out_e, ((0,0),(1,1)), mode='constant')
                
                s_in_n = pad_Sos[:-2, :] # S coming from N neighbor (its South flow)
                s_in_s = pad_Son[2:, :]  # S coming from S neighbor (its North flow)
                s_in_w = pad_Soe[:, :-2]
                s_in_e = pad_Sow[:, 2:]
                
                sem_in = s_in_n + s_in_s + s_in_w + s_in_e
                
                sediment += (sem_in - sem_out)
                
                # Stability Check for Sediment
                if xp.any(xp.isnan(sediment)) or xp.any(xp.isinf(sediment)):
                    sediment = xp.nan_to_num(sediment)
                
                # Clamp again - Tight bounds to prevent spikes
                xp.clip(sediment, 0, 5.0, out=sediment)
                
                # 6. Evaporation
                water *= (1.0 - k_evap)
                
                # Stability Check for Water
                if xp.any(xp.isnan(water)) or xp.any(xp.isinf(water)):
                    water = xp.nan_to_num(water)
            
            # Final Step: Pass (discard sediment)
            pass
            
        elif f_type == "Thermal":
            # Thermal Weathering with Talus Angle
            iterations = self.get_property("T-Iterations")
            strength = self.get_property("T-Strength")
            talus_deg = self.get_property("T-Talus Angle")
            
            # Convert degrees to slope threshold (dy/dx)
            # Assuming dx=1 for simplicity, or we can use terrain_size if needed.
            # Using pixel-space gradient for now
            talus_threshold = xp.tan(xp.radians(talus_deg))
            
            for _ in range(iterations):
                # Calculate gradients to neighbors (N, S, E, W)
                padded = xp.pad(heightmap, 1, mode='edge')
                
                # Diff: neighbor - current (negative means neighbor is lower)
                # actually we want current - neighbor (force towards neighbor)
                
                d_n = heightmap - padded[:-2, 1:-1]
                d_s = heightmap - padded[2:, 1:-1]
                d_w = heightmap - padded[1:-1, :-2]
                d_e = heightmap - padded[1:-1, 2:]
                
                # Identify where slope > threshold
                # Only move if d > talus_threshold
                
                move_n = xp.maximum(0, d_n - talus_threshold)
                move_s = xp.maximum(0, d_s - talus_threshold)
                move_w = xp.maximum(0, d_w - talus_threshold)
                move_e = xp.maximum(0, d_e - talus_threshold)
                
                # Total material to move
                total_move = move_n + move_s + move_w + move_e
                
                # Scale by strength and limit (don't move more than diff?)
                # We distribute the movement.
                # Factor 0.5 to avoid oscillation (mass conservation stability)
                # Actually, simpler: amount = diff * strength / 4 (if neighbors > threshold)
                
                # Normalize factor to prevent moving more than available excess
                # We can just use a rate parameter
                
                rate = strength * 0.1 # Small steps for stability
                
                out_n = move_n * rate
                out_s = move_s * rate
                out_w = move_w * rate
                out_e = move_e * rate
                
                total_out = out_n + out_s + out_w + out_e
                
                # Update current cell (lose material)
                change = -total_out
                
                # Update neighbors (gain material)
                # Vectorized inflow accumulation
                
                pad_On = xp.pad(out_n, ((1,1),(0,0)), mode='constant')
                pad_Os = xp.pad(out_s, ((1,1),(0,0)), mode='constant')
                pad_Ow = xp.pad(out_w, ((0,0),(1,1)), mode='constant')
                pad_Oe = xp.pad(out_e, ((0,0),(1,1)), mode='constant')
                
                # Inflow logic:
                # inflow from N neighbor comes from his South flow (move_s of N)
                
                in_n = pad_Os[:-2, :] # Material coming FROM North neighbor (its South flow)
                in_s = pad_On[2:, :]  # FROM South (its North flow)
                in_w = pad_Oe[:, :-2] # FROM West (its East flow)
                in_e = pad_Ow[:, 2:]  # FROM East (its West flow)
                
                change += (in_n + in_s + in_w + in_e)
                
                # Stability Check
                if xp.any(xp.isnan(change)) or xp.any(xp.isinf(change)):
                    change = xp.nan_to_num(change)
                
                # Clamp Thermal Change
                xp.clip(change, -100.0, 100.0, out=change)
                
                if mask is not None:
                    heightmap[:] += change * mask
                else:
                    heightmap[:] += change

        elif f_type == "Smooth":
            sigma = self.get_property("Smooth Sigma")
            # Apply Gaussian Filter (using backend ndimage)
            smoothed = ndimage.gaussian_filter(heightmap, sigma=sigma)
            
            if mask is not None:
                heightmap[:] = heightmap * (1.0 - mask) + smoothed * mask
            else:
                heightmap[:] = smoothed
        
        elif f_type == "Sharpen":
            # Unsharp mask
            sigma = self.get_property("Sharpen Sigma")
            strength = self.get_property("Sharpen Strength")
            
            # Blurred version
            blurred = ndimage.gaussian_filter(heightmap, sigma=sigma)
            
            # Unsharp mask: Original + (Original - Blurred) * Strength
            mask_detail = heightmap - blurred
            sharpened = heightmap + mask_detail * strength
            
            if mask is not None:
                heightmap[:] = heightmap * (1.0 - mask) + sharpened * mask
            else:
                heightmap[:] = sharpened
        
        elif f_type == "Distort by Noise":
            from src.filters.terrain_filters import DistortByNoiseFilter
            noise_type = self.get_property("Distort Noise Type")
            amplitude = self.get_property("Distort Amplitude")
            element_size = self.get_property("Distort Element Size")
            substeps = self.get_property("Distort Substeps")
            seed = self.get_property("Distort Seed")
            
            filter_op = DistortByNoiseFilter(noise_type, amplitude, element_size, substeps, seed)
            result = filter_op.apply(heightmap, terrain_size)
            
            if mask is not None:
                heightmap[:] = heightmap * (1.0 - mask) + result * mask
            else:
                heightmap[:] = result
        
        elif f_type == "Terrace":
            from src.filters.terrain_filters import TerraceFilter
            step_count = self.get_property("Terrace Step Count")
            smoothness = self.get_property("Terrace Smoothness")
            
            filter_op = TerraceFilter(step_count, None, smoothness)
            result = filter_op.apply(heightmap, terrain_size)
            
            if mask is not None:
                heightmap[:] = heightmap * (1.0 - mask) + result * mask
            else:
                heightmap[:] = result
        
        elif f_type == "Clip":
            from src.filters.terrain_filters import ClipFilter
            use_min = self.get_property("Use Min Clip")
            use_max = self.get_property("Use Max Clip")
            min_h = self.get_property("Clip Min Height") if use_min else None
            max_h = self.get_property("Clip Max Height") if use_max else None
            soft_strength = self.get_property("Clip Soft Strength")
            
            filter_op = ClipFilter(min_h, max_h, soft_strength)
            result = filter_op.apply(heightmap, terrain_size)
            
            if mask is not None:
                heightmap[:] = heightmap * (1.0 - mask) + result * mask
            else:
                heightmap[:] = result


class MaskEntity(Entity):
    def __init__(self, name="Mask"):
        super().__init__(name, entity_type=EntityType.MASK)
        
        # Main Settings
        self.define_property("Type", str, "Primitive", options=["Primitive", "Draw", "Image", "Feature"], group="General")
        self.define_property("Opacity", float, 1.0, 0.0, 1.0, group="General")
        self.define_property("Blur", float, 0.0, 0.0, 100.0, group="General")
        self.define_property("Invert", bool, False, group="General")

        # Draw Settings
        self.define_property("Brush Size", float, 50.0, 1.0, 500.0, group="Draw Settings")
        self.define_property("Brush Strength", float, 0.5, 0.0, 1.0, group="Draw Settings")
        self.define_property("Brush Opacity", float, 1.0, 0.0, 1.0, group="Draw Settings")
        self.define_property("Mask Resolution", int, 512, options=[512, 1024, 2048, 4096], group="Draw Settings")
        
        # Internal Data
        self.mask_data = None


        # Primitive Settings
        self.define_property("Primitive Shape", str, "Circle", options=["Circle", "Square"], group="Primitive Settings")
        self.define_property("Size", float, 500.0, 10.0, 2048.0, group="Primitive Settings")
        self.define_property("Falloff", float, 0.0, 0.0, 500.0, group="Primitive Settings") # Keep for potential soft primitves
        self.define_property("X", float, 0.0, -2048.0, 2048.0, group="Primitive Settings")
        self.define_property("Y", float, 0.0, -2048.0, 2048.0, group="Primitive Settings")
        
        # Image Settings
        self.define_property("Image Path", str, "", group="Image Settings")

        # Feature Settings
        self.define_property("Feature Type", str, "Height", options=["Height", "Slope", "Curvature"], group="Feature Settings")
        self.define_property("Min Val", float, 0.0, -10000.0, 10000.0, group="Feature Settings")
        self.define_property("Max Val", float, 1000.0, -10000.0, 10000.0, group="Feature Settings")
        self.define_property("Ramp", float, 0.0, 0.0, 1.0, group="Feature Settings")
        
        # Initial visibility update
        self.update_visibility()

    def on_property_changed(self, name, value):
        if name == "Type":
            self.update_visibility()

    def update_visibility(self):
        m_type = self.get_property("Type")
        
        # Primitive
        show_prim = (m_type == "Primitive")
        self.set_property_visible("Primitive Shape", show_prim)
        self.set_property_visible("Size", show_prim)
        self.set_property_visible("Falloff", show_prim)
        self.set_property_visible("X", show_prim)
        self.set_property_visible("Y", show_prim)
        
        # Draw
        show_draw = (m_type == "Draw")
        self.set_property_visible("Brush Size", show_draw)
        self.set_property_visible("Brush Strength", show_draw)
        self.set_property_visible("Brush Opacity", show_draw)
        self.set_property_visible("Mask Resolution", show_draw)

        
        # Image
        show_img = (m_type == "Image")
        self.set_property_visible("Image Path", show_img)
        
        # Feature
        show_feat = (m_type == "Feature")
        self.set_property_visible("Feature Type", show_feat)
        self.set_property_visible("Min Val", show_feat)
        self.set_property_visible("Max Val", show_feat)
        self.set_property_visible("Ramp", show_feat)

    def process(self, input_heightmap, parent_mask=None, terrain_size=1000.0, input_version=None):
        if not self.get_property("Enabled"):
             return input_heightmap, input_version
             
        # Mask process is slightly different:
        # It doesn't cache the *heightmap* result of itself (since it doesn't modify it),
        # but it caches the result of its children?
        # Actually, MaskEntity behaves like a pass-through that modifies the MASK context for children.
        # But if we want to cache the result of the *entire mask branch*, we should handle it same as Entity.
        
        # 1. Caching Check
        if not self.is_dirty and input_version is not None and input_version == self.last_input_version:
             if self._cached_output is not None:
                 return self._cached_output, self.id
             loaded = self.load_cache()
             if loaded is not None:
                 self._cached_output = loaded
                 return loaded, self.id

        # 2. Compute
        current_heightmap = input_heightmap.copy() if input_heightmap is not None else None
        
        # Generate local mask
        local_mask = self.generate_mask(current_heightmap, terrain_size)
        
        # Combine with parent mask
        effective_mask = local_mask
        if parent_mask is not None:
            effective_mask = local_mask * parent_mask
            
        current_version = str(uuid.uuid4())
            
        # Process children with this NEW mask
        for child in self._children:
            current_heightmap, current_version = child.process(current_heightmap, effective_mask, terrain_size, current_version)
            
        # 3. Update Cache
        self._cached_output = current_heightmap
        self.last_input_version = input_version
        
        if self.is_dirty:
            self.is_dirty = False
            self.status_changed.emit(self)
            
        self.save_cache(current_heightmap)
        
        return current_heightmap, str(uuid.uuid4())
            
    def generate_mask(self, heightmap, terrain_size):
        # Allow passing shape tuple or full heightmap array
        if isinstance(heightmap, tuple):
             shape = heightmap
             hm_data = None
        else:
             shape = heightmap.shape
             hm_data = heightmap

        m_type = self.get_property("Type")
        h, w = shape
        # Calculate pixels per unit (assuming square pixels)
        # terrain_size is physical width
        pixels_per_unit = w / terrain_size
        
        mask = xp.zeros(shape, dtype=xp.float32)

        # --- GENERATION ---
        if m_type == "Primitive":
            shape_type = self.get_property("Primitive Shape")
            
            # Scale properties from physical to pixels
            size_px = self.get_property("Size") * pixels_per_unit
            x_px = self.get_property("X") * pixels_per_unit
            y_px = self.get_property("Y") * pixels_per_unit
            
            cx = w//2 + x_px
            cy = h//2 + y_px
            
            # Generate grid on device
            y = xp.arange(h).reshape(-1, 1)
            x = xp.arange(w).reshape(1, -1)
            
            if shape_type == "Circle":
                dist_sq = (x - cx)**2 + (y - cy)**2
                radius_sq = (size_px/2)**2
                # Simple hard edge
                mask = (dist_sq <= radius_sq).astype(xp.float32)
                
            elif shape_type == "Square":
                half_size = size_px / 2
                mask = ((xp.abs(x - cx) <= half_size) & (xp.abs(y - cy) <= half_size)).astype(xp.float32)
                
        elif m_type == "Image":
            path = self.get_property("Image Path")
            if path and os.path.exists(path):
                try:
                    img = Image.open(path).convert('L') # Grayscale
                    img = img.resize((w, h))
                    img_data = np.array(img, dtype=np.float32) / 255.0
                    mask = to_device(img_data)
                except Exception as e:
                    print(f"Error loading mask image: {e}")

        elif m_type == "Feature":
            if hm_data is None:
                # Fallback if no heightmap data provided
                return mask 
            
            f_type = self.get_property("Feature Type")
            min_v = self.get_property("Min Val")
            max_v = self.get_property("Max Val")
            
            # Needed for slope/curvature scaling
            dx = terrain_size / w if w > 0 else 1.0
            
            # Ensure hm_data is on device
            hm_data = to_device(hm_data)
            
            feature_map = xp.zeros_like(hm_data)
            
            if f_type == "Height":
                feature_map = hm_data
                
            elif f_type == "Slope":
                # Gradient magnitude
                # Scale by 1/dx to get dy/dx
                # xp.gradient returns a list of arrays (gradient along each axis)
                grads = xp.gradient(hm_data, dx)
                gy, gx = grads[0], grads[1]
                slope = xp.sqrt(gx**2 + gy**2)
                feature_map = slope
                
            elif f_type == "Curvature":
                # Laplacian
                feature_map = ndimage.laplace(hm_data) / (dx**2)
            
            # Thresholding
            mask = ((feature_map >= min_v) & (feature_map <= max_v)).astype(xp.float32)
            
        elif m_type == "Draw":
            res = self.get_property("Mask Resolution")
            if self.mask_data is None:
                self.mask_data = xp.zeros((res, res), dtype=xp.float32)
                
            # Handle resolution change? 
            # For now, if size mismatches, we assume we should use what we have, 
            # or maybe resize mask_data?
            # Let's enforce mask_data to match property if it was just changed?
            # Complexity: Users might change res and lose data.
            # Best to keep data as is, and resize on consumption if needed.
            
            # Match output shape (h, w)
            if self.mask_data.shape != (h, w):
                # Resize
                zh = h / self.mask_data.shape[0]
                zw = w / self.mask_data.shape[1]
                mask = ndimage.zoom(self.mask_data, (zh, zw), order=1)
            else:
                mask = self.mask_data.copy()

            
        # --- POST PROCESSING ---
        
        # 1. Blur (Physical units)
        blur_amt_phys = self.get_property("Blur")
        if blur_amt_phys > 0:
            sigma = blur_amt_phys * pixels_per_unit
            mask = ndimage.gaussian_filter(mask, sigma=sigma)
            
        # 2. Invert
        if self.get_property("Invert"):
            mask = 1.0 - mask
            
        # 3. Opacity
        opacity = self.get_property("Opacity")
        mask = mask * opacity
        
        return mask

    def paint(self, world_x, world_z, radius, strength, opacity, erase=False, terrain_size=1000.0):
        t0 = time.time()
        
        res = self.get_property("Mask Resolution")
        if self.mask_data is None:
            self.mask_data = xp.zeros((res, res), dtype=xp.float32)
        elif self.mask_data.shape[0] != res:
            # Resize existing data if resolution property changed
            # (Simple resize for now)
            zoom_fac = res / self.mask_data.shape[0]
            self.mask_data = ndimage.zoom(self.mask_data, zoom_fac, order=1)
            
        h, w = self.mask_data.shape
        
        # Map World to Pixel
        # World: [-size/2, size/2] -> [0, w]
        x_px = (world_x + terrain_size/2) / terrain_size * w
        y_px = (world_z + terrain_size/2) / terrain_size * h
        r_px = radius / terrain_size * w
        
        # Create ROI
        roi_r = int(np.ceil(r_px))
        x0 = int(max(0, x_px - roi_r))
        x1 = int(min(w, x_px + roi_r + 1))
        y0 = int(max(0, y_px - roi_r))
        y1 = int(min(h, y_px + roi_r + 1))
        
        if x0 >= x1 or y0 >= y1: return
        
        # Grid
        # Optimization: Don't create full meshgrid if not needed?
        # ROI meshgrid is fast enough usually.
        y_grid, x_grid = xp.meshgrid(xp.arange(y0, y1), xp.arange(x0, x1), indexing='ij')
        dist_sq = (x_grid - x_px)**2 + (y_grid - y_px)**2
        
        # Soft Brush (Linear Falloff)
        # 1 at center, 0 at radius
        # dist = sqrt(dist_sq)
        # val = clip(1 - dist/r, 0, 1)
        
        dist = xp.sqrt(dist_sq)
        brush_val = xp.clip(1.0 - dist/r_px, 0.0, 1.0)
        
        # Apply Logic
        # Additive: value += strength * brush_val
        # But capped by opacity?
        # Let's say Opacity is the max value we can reach with this brush?
        # Or Opacity is global alpha?
        # Simple painting: Add
        
        change = brush_val * strength
        
        target = self.mask_data[y0:y1, x0:x1]
        
        if erase:
            target -= change
        else:
            target += change
            
        xp.clip(target, 0.0, 1.0, out=target)
        t1 = time.time()
        print(f"DEBUG: MaskEntity.paint took {(t1-t0)*1000:.2f} ms")
        self.mask_data[y0:y1, x0:x1] = target
        
        # Mark dirty to update previews
        self.is_dirty = True
        self.changed.emit()

    def save_data(self, project_path):
        if self.mask_data is not None:
            # Save as NPY
            filename = f"mask_{self.id}.npy"
            path = os.path.join(project_path, "masks")
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
                
            filepath = os.path.join(path, filename)
            
            # Ensure CPU
            data_cpu = to_cpu(self.mask_data)
            np.save(filepath, data_cpu)
            
    def load_data(self, project_path):
        filename = f"mask_{self.id}.npy"
        filepath = os.path.join(project_path, "masks", filename)
        if os.path.exists(filepath):
            try:
                data = np.load(filepath)
                # Convert to Float32
                data = data.astype(np.float32)
                self.mask_data = to_device(data)
                
                # Sync resolution property
                self.set_property("Mask Resolution", data.shape[0])
            except Exception as e:
                print(f"Failed to load mask data: {e}")

