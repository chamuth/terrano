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

    def process(self, heightmap, mask=None):
        """
        Recursive processing pipeline.
        heightmap: The shared heightmap array (modified in-place).
        mask: The current scoped mask (0.0 - 1.0). None implies 1.0 everywhere.
        """
        # Check property instead of private flag
        if not self.get_property("Enabled"):
            return

        # 1. Apply Self Logic
        self.on_process(heightmap, mask)
        
        # 2. Process Children
        # If we are a Mask, we handle children differently (scoped)
        if self.entity_type != EntityType.MASK:
            for child in self._children:
                child.process(heightmap, mask)
                
    def on_process(self, heightmap, mask):
        pass

    def define_property(self, name, dtype, value, min_val=None, max_val=None, options=None):
        self.properties[name] = {
            "type": dtype,
            "value": value,
            "min": min_val,
            "max": max_val,
            "options": options # For Dropdowns (list of strings)
        }

    def set_property(self, name, value):
        if name in self.properties:
            # Type safety check could go here
            self.properties[name]["value"] = value
            self.on_property_changed(name, value)
            self.changed.emit()
    
    def get_property(self, name):
        return self.properties[name]["value"]
        
    def on_property_changed(self, name, value):
        pass


class TerrainEntity(Entity):
    def __init__(self):
        super().__init__("Terrain", entity_type=EntityType.ROOT)
        # Resolution as options
        self.define_property("Resolution", str, "1024", options=["512", "1024", "2048", "4096"])
        self.define_property("Base Height", float, 0.0, -1000.0, 1000.0)
        
    def on_process(self, heightmap, mask):
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
        self.define_property("Type", str, "Perlin Noise", options=["Perlin Noise", "Simplex Noise", "Constant"])
        self.define_property("Strength", float, 1.0, 0.0, 1.0) # Blend strength
        self.define_property("Operation", str, "Add", options=["Add", "Subtract", "Replace", "Multiply"])
        
        # Perlin Defaults
        self.define_property("Scale", float, 100.0, 10.0, 1000.0)
        self.define_property("Octaves", int, 6, 1, 12)
        self.define_property("Persistence", float, 0.5, 0.0, 1.0)
        self.define_property("Lacunarity", float, 2.0, 1.0, 4.0)
        self.define_property("Height Offset", float, 0.0, -500.0, 500.0)
        self.define_property("Amplitude", float, 50.0, 0.0, 1000.0)
        self.define_property("Seed", int, 42, 0, 99999)

    def on_property_changed(self, name, value):
        if name == "Type":
            # We could dynamically hide/show props here if Inspector supports it
            pass

    def on_process(self, heightmap, mask):
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
            generated = gen.generate(heightmap.shape[0]) + offset
            
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
        self.define_property("Type", str, "Erosion", options=["Erosion", "Thermal", "Smooth", "Sharpen"])
        
        # Hydraulic
        self.define_property("H-Iterations", int, 5, 1, 100) # Passes
        self.define_property("H-Rain Amount", float, 0.1, 0.0, 1.0)
        
        # Thermal
        self.define_property("T-Iterations", int, 10, 1, 100)
        self.define_property("T-Strength", float, 0.5, 0.0, 1.0)
        
    def on_process(self, heightmap, mask):
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


class MaskEntity(Entity):
    def __init__(self, name="Mask"):
        super().__init__(name, entity_type=EntityType.MASK)
        self.define_property("Type", str, "Circle", options=["Circle", "Square", "Noise"])
        self.define_property("Invert", bool, False)
        self.define_property("Size", float, 500.0, 10.0, 2048.0)
        self.define_property("Falloff", float, 0.0, 0.0, 500.0) # Unused for binary
        self.define_property("X", float, 0.0, -2048.0, 2048.0)
        self.define_property("Y", float, 0.0, -2048.0, 2048.0)
        
    def process(self, heightmap, parent_mask=None):
        if not self.get_property("Enabled"):
            return

        # 1. Generate local mask
        local_mask = self.generate_mask(heightmap.shape)
        
        if self.get_property("Invert"):
            local_mask = 1.0 - local_mask

        # 2. Combine with parent mask
        effective_mask = local_mask
        if parent_mask is not None:
            effective_mask = local_mask * parent_mask
            
        # 3. Process children with this NEW mask
        for child in self._children:
            child.process(heightmap, effective_mask)
            
    def generate_mask(self, shape):
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
            
        return mask
