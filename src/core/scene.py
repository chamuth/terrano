import numpy as np
import uuid
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

    def __init__(self, name="Entity", parent=None, entity_type=EntityType.ROOT):
        super().__init__()
        self.id = str(uuid.uuid4())
        self._name = name
        self.entity_type = entity_type
        self._parent = None
        self._children = []
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
            
    @property
    def name(self):
        return self._name
        
    @name.setter
    def name(self, value):
        self._name = value
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
            self.structure_changed.emit()
            
    def remove_child(self, child):
        if child in self._children:
            self._children.remove(child)
            child._parent = None
            self.structure_changed.emit()

    def get_children(self):
        return self._children

    def process(self, heightmap, mask=None, terrain_size=1000.0):
        """
        Recursive processing pipeline.
        heightmap: The shared heightmap array (modified in-place).
        mask: The current scoped mask (0.0 - 1.0). None implies 1.0 everywhere.
        terrain_size: Physical size of the terrain (for scale-independent generation)
        """
        # Check property instead of private flag
        if not self.get_property("Enabled"):
            return

        # 1. Apply Self Logic
        self.on_process(heightmap, mask, terrain_size)
        
        # 2. Process Children
        # If we are a Mask, we handle children differently (scoped)
        if self.entity_type != EntityType.MASK:
            for child in self._children:
                child.process(heightmap, mask, terrain_size)
                
    def on_process(self, heightmap, mask, terrain_size):
        pass

    def define_property(self, name, dtype, value, min_val=None, max_val=None, options=None):
        self.properties[name] = {
            "type": dtype,
            "value": value,
            "min": min_val,
            "max": max_val,
            "options": options, # For Dropdowns (list of strings)
            "visible": True
        }

    def set_property(self, name, value):
        if name in self.properties:
            # Type safety check could go here
            self.properties[name]["value"] = value
            self.on_property_changed(name, value)
            self.changed.emit()
            
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
        self.define_property("Resolution", str, "512", options=["512", "1024", "2048", "4096"])
        self.define_property("Size", float, 1000.0, 100.0, 10000.0) # Physical Size
        self.define_property("Base Height", float, 0.0, -1000.0, 1000.0)
        
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
        ])
        self.define_property("Strength", float, 1.0, 0.0, 1.0)
        self.define_property("Operation", str, "Add", options=["Add", "Subtract", "Replace", "Multiply"])
        
        # Common properties (Perlin, Simplex)
        self.define_property("Scale", float, 100.0, 10.0, 1000.0)
        self.define_property("Octaves", int, 6, 1, 12)
        self.define_property("Persistence", float, 0.5, 0.0, 1.0)
        self.define_property("Lacunarity", float, 2.0, 1.0, 4.0)
        self.define_property("Amplitude", float, 50.0, 0.0, 1000.0)
        self.define_property("Seed", int, 42, 0, 99999)
        self.define_property("Height Offset", float, 0.0, -500.0, 500.0)
        
        # Gabor properties
        self.define_property("Gabor Frequency", float, 0.05, 0.01, 0.2)
        self.define_property("Gabor Orientation", float, 0.0, -180.0, 180.0)
        self.define_property("Gabor Bandwidth", float, 1.0, 0.1, 5.0)
        self.define_property("Gabor Impulses", int, 50, 10, 200)
        
        # Alligator properties
        self.define_property("Alligator Scale", float, 100.0, 10.0, 500.0)
        self.define_property("Alligator Jitter", float, 1.0, 0.0, 1.0)
        
        # Voronoi properties
        self.define_property("Voronoi Scale", float, 100.0, 10.0, 500.0)
        self.define_property("Voronoi Metric", str, "F1", options=["F1", "F2", "F2-F1"])
        self.define_property("Distance Type", str, "euclidean", options=["euclidean", "manhattan", "chebyshev"])
        self.define_property("Invert Voronoi", bool, False)
        
        # Pattern properties
        self.define_property("Pattern Type", str, "Linear Ramp", options=["Linear Ramp", "Radial", "Grid", "Checker"])
        self.define_property("Pattern Direction", float, 0.0, -180.0, 180.0)
        self.define_property("Pattern Center X", float, 0.5, 0.0, 1.0)
        self.define_property("Pattern Center Y", float, 0.5, 0.0, 1.0)
        self.define_property("Pattern Frequency", float, 4.0, 1.0, 20.0)

    def on_property_changed(self, name, value):
        if name == "Type":
            self.update_property_visibility()
        # Mark dirty on any property change
        self.changed.emit()

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
        
        generated = np.zeros_like(heightmap)
        
        if gen_type == "Perlin Noise":
            from src.generators.perlin_noise import PerlinNoiseGenerator
            scale = self.get_property("Scale")
            octaves = self.get_property("Octaves")
            pers = self.get_property("Persistence")
            lac = self.get_property("Lacunarity")
            seed = self.get_property("Seed")
            amp = self.get_property("Amplitude")
            offset = self.get_property("Height Offset")
            
            gen = PerlinNoiseGenerator(scale, octaves, pers, lac, seed, amp)
            generated = gen.generate(heightmap.shape[0], terrain_size) + offset
            
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
            generated = gen.generate(heightmap.shape[0], terrain_size) + offset
            
        elif gen_type == "Gabor Noise":
            from src.generators.noise_library import GaborNoiseGenerator
            freq = self.get_property("Gabor Frequency")
            orient = self.get_property("Gabor Orientation")
            bandwidth = self.get_property("Gabor Bandwidth")
            impulses = self.get_property("Gabor Impulses")
            seed = self.get_property("Seed")
            amp = self.get_property("Amplitude")
            
            gen = GaborNoiseGenerator(freq, orient, bandwidth, impulses, seed, amp)
            generated = gen.generate(heightmap.shape[0], terrain_size)
            
        elif gen_type == "Alligator Noise":
            from src.generators.noise_library import AlligatorNoiseGenerator
            scale = self.get_property("Alligator Scale")
            jitter = self.get_property("Alligator Jitter")
            seed = self.get_property("Seed")
            amp = self.get_property("Amplitude")
            
            gen = AlligatorNoiseGenerator(scale, jitter, seed, amp)
            generated = gen.generate(heightmap.shape[0], terrain_size)
            
        elif gen_type == "Voronoi":
            from src.generators.noise_library import VoronoiGenerator
            scale = self.get_property("Voronoi Scale")
            metric = self.get_property("Voronoi Metric")
            dist_type = self.get_property("Distance Type")
            seed = self.get_property("Seed")
            amp = self.get_property("Amplitude")
            invert = self.get_property("Invert Voronoi")
            
            gen = VoronoiGenerator(scale, metric, dist_type, seed, amp, invert)
            generated = gen.generate(heightmap.shape[0], terrain_size)
            
        elif gen_type == "Pattern":
            from src.generators.noise_library import PatternGenerator
            pattern_type = self.get_property("Pattern Type")
            direction = self.get_property("Pattern Direction")
            center_x = self.get_property("Pattern Center X")
            center_y = self.get_property("Pattern Center Y")
            frequency = self.get_property("Pattern Frequency")
            amp = self.get_property("Amplitude")
            
            gen = PatternGenerator(pattern_type, direction, (center_x, center_y), frequency, amp)
            generated = gen.generate(heightmap.shape[0], terrain_size)
            
        elif gen_type == "Constant":
            offset = self.get_property("Height Offset")
            generated[:] = offset

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
            "Distort by Noise", "Terrace", "Clip"
        ])
        
        # Hydraulic Erosion
        self.define_property("H-Iterations", int, 5, 1, 100)
        self.define_property("H-Rain Amount", float, 0.1, 0.0, 1.0)
        
        # Thermal Erosion
        self.define_property("T-Iterations", int, 10, 1, 100)
        self.define_property("T-Strength", float, 0.5, 0.0, 1.0)
        
        # Distort by Noise
        self.define_property("Distort Noise Type", str, "Perlin", options=["Perlin", "Simplex", "Curl"])
        self.define_property("Distort Amplitude", float, 10.0, 0.1, 100.0)
        self.define_property("Distort Element Size", float, 50.0, 10.0, 500.0)
        self.define_property("Distort Substeps", int, 3, 1, 10)
        self.define_property("Distort Seed", int, 42, 0, 99999)
        
        # Terrace
        self.define_property("Terrace Step Count", int, 10, 2, 50)
        self.define_property("Terrace Smoothness", float, 0.1, 0.0, 1.0)
        
        # Clip
        self.define_property("Clip Min Height", float, -100.0, -1000.0, 1000.0)
        self.define_property("Clip Max Height", float, 100.0, -1000.0, 1000.0)
        self.define_property("Clip Soft Strength", float, 0.2, 0.0, 1.0)
        self.define_property("Use Min Clip", bool, False)
        self.define_property("Use Max Clip", bool, False)
        
    def on_process(self, heightmap, mask, terrain_size):
        f_type = self.get_property("Type")
        
        if f_type == "Erosion":
            # Simplified Grid-Based Erosion (Cellular Automata style)
            # Faster than particle drops for python
            rain_amount = self.get_property("H-Rain Amount") * 0.1
            passes = self.get_property("H-Iterations")
            
            for _ in range(passes):
                 padded = np.pad(heightmap, 1, mode='edge')
                 
                 # Neighbors
                 n = padded[:-2, 1:-1]
                 s = padded[2:, 1:-1]
                 e = padded[1:-1, 2:]
                 w = padded[1:-1, :-2]
                 
                 # Diff to neighbors (positive means we are higher)
                 diff_n = heightmap - n
                 diff_s = heightmap - s
                 diff_e = heightmap - e
                 diff_w = heightmap - w
                 
                 # Accumulate flow/erosion (only erode if higher)
                 erode = np.maximum(0, diff_n) + np.maximum(0, diff_s) + \
                         np.maximum(0, diff_e) + np.maximum(0, diff_w)
                 
                 # Apply rain factor
                 delta = erode * rain_amount
                 
                 if mask is not None:
                     heightmap[:] -= delta * mask
                 else:
                     heightmap[:] -= delta
            
        elif f_type == "Thermal":
            # Thermal weathering - Diffusion
            iterations = self.get_property("T-Iterations")
            strength = self.get_property("T-Strength") * 0.5
            
            from scipy.ndimage import uniform_filter
            
            for _ in range(iterations):
                # Box blur creates diffusion
                smoothed = uniform_filter(heightmap, size=3)
                delta = (smoothed - heightmap) * strength
                
                if mask is not None:
                    heightmap[:] += delta * mask
                else:
                    heightmap[:] += delta

        elif f_type == "Smooth":
            from scipy.ndimage import gaussian_filter
            sigma = 2.0
            if mask is not None:
                smoothed = gaussian_filter(heightmap, sigma=sigma)
                heightmap[:] = heightmap * (1.0 - mask) + smoothed * mask
            else:
                heightmap[:] = gaussian_filter(heightmap, sigma=sigma)
        
        elif f_type == "Sharpen":
            from scipy.ndimage import gaussian_filter
            # Unsharp mask
            smoothed = gaussian_filter(heightmap, sigma=2.0)
            detail = heightmap - smoothed
            
            if mask is not None:
                heightmap[:] += detail * mask
            else:
                heightmap[:] += detail
        
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
        self.define_property("Type", str, "Circle", options=["Circle", "Square", "Noise"])
        self.define_property("Invert", bool, False)
        self.define_property("Size", float, 500.0, 10.0, 2048.0)
        self.define_property("Falloff", float, 0.0, 0.0, 500.0) # Unused for binary
        self.define_property("X", float, 0.0, -2048.0, 2048.0)
        self.define_property("Y", float, 0.0, -2048.0, 2048.0)
        
    def process(self, heightmap, parent_mask=None, terrain_size=1000.0):
        if not self.get_property("Enabled"):
            return

        # 1. Generate local mask (Invert is handled inside generate_mask now)
        local_mask = self.generate_mask(heightmap.shape, terrain_size)
        
        # 2. Combine with parent mask
        effective_mask = local_mask
        if parent_mask is not None:
            effective_mask = local_mask * parent_mask
            
        # 3. Process children with this NEW mask
        for child in self._children:
            child.process(heightmap, effective_mask, terrain_size)
            
    def generate_mask(self, shape, terrain_size):
        m_type = self.get_property("Type")
        h, w = shape
        mask = np.zeros(shape, dtype=np.float32)
        
        cx = w//2 + self.get_property("X")
        cy = h//2 + self.get_property("Y") 
        radius = self.get_property("Size") / 2.0
        
        y_idx, x_idx = np.ogrid[:h, :w]
        
        if m_type == "Circle":
            dist_sq = (x_idx - cx)**2 + (y_idx - cy)**2
            # Binary threshold
            mask = np.where(dist_sq <= radius**2, 1.0, 0.0)
            
        elif m_type == "Square":
            mask [ int(cy-radius):int(cy+radius), int(cx-radius):int(cx+radius) ] = 1.0
            
        # Apply Invert
        if self.get_property("Invert"):
            mask = 1.0 - mask
            
        return mask
