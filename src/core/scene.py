
import numpy as np
import uuid
from PyQt6.QtCore import QObject, pyqtSignal

class Entity(QObject):
    # Signal when properties change so Inspector/Viewport can update
    changed = pyqtSignal()
    structure_changed = pyqtSignal() # When children are added/removed

    def __init__(self, name="Entity", parent=None):
        super().__init__()
        self.id = str(uuid.uuid4())
        self._name = name
        self._parent = None
        self._children = []
        self._enabled = True
        
        # Generic Properties Dictionary using a custom schema
        # { "prop_name": { "type": float, "value": 1.0, "min": 0, "max": 100 } }
        self.properties = {} 

        if parent:
            self.set_parent(parent)
            
    @property
    def name(self):
        return self._name
        
    @name.setter
    def name(self, value):
        self._name = value
        self.changed.emit()

    def set_parent(self, parent):
        if self._parent:
            self._parent.remove_child(self)
        
        self._parent = parent
        if self._parent:
            self._parent.add_child(self)
    
    def add_child(self, child):
        if child not in self._children:
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

    def process(self, heightmap_data, mask=None):
        """
        Base process method. 
        heightmap_data: The 2D numpy array being modified.
        mask: Optional 2D numpy array (0.0 to 1.0) defining area of effect.
        """
        # Base entity usually does nothing to data, just passes it to children.
        # But specific subclasses will modify it.
        
        # 1. Apply Self Logic
        self.on_process(heightmap_data, mask)
        
        # 2. Process Children
        for child in self._children:
            if child._enabled:
                child.process(heightmap_data, mask)
                
    def on_process(self, heightmap_data, mask):
        pass

    def define_property(self, name, dtype, value, min_val=None, max_val=None, options=None):
        self.properties[name] = {
            "type": dtype,
            "value": value,
            "min": min_val,
            "max": max_val,
            "options": options # For enums
        }

    def set_property(self, name, value):
        if name in self.properties:
            self.properties[name]["value"] = value
            self.changed.emit()
    
    def get_property(self, name):
        return self.properties[name]["value"]


class TerrainEntity(Entity):
    def __init__(self, size=1024):
        super().__init__("Terrain")
        self.define_property("Size", int, size, 32, 4096)
        self.define_property("Base Height", float, 0.0, -100.0, 100.0)
        
        # Perlin Noise Properties
        self.define_property("Noise Scale", float, 100.0, 10.0, 500.0)
        self.define_property("Noise Octaves", int, 6, 1, 10)
        self.define_property("Noise Persistence", float, 0.5, 0.0, 1.0)
        self.define_property("Noise Lacunarity", float, 2.0, 1.0, 4.0)
        self.define_property("Noise Seed", int, 0, 0, 10000)
        self.define_property("Noise Amplitude", float, 50.0, 0.0, 200.0)
        
    def on_process(self, heightmap_data, mask):
        """Generate terrain with Perlin noise"""
        from src.generators.perlin_noise import PerlinNoiseGenerator
        
        size = self.get_property("Size")
        base_height = self.get_property("Base Height")
        
        # Get Perlin noise parameters
        noise_scale = self.get_property("Noise Scale")
        noise_octaves = self.get_property("Noise Octaves")
        noise_persistence = self.get_property("Noise Persistence")
        noise_lacunarity = self.get_property("Noise Lacunarity")
        noise_seed = self.get_property("Noise Seed")
        noise_amplitude = self.get_property("Noise Amplitude")
        
        # Generate Perlin noise
        generator = PerlinNoiseGenerator(
            scale=noise_scale,
            octaves=noise_octaves,
            persistence=noise_persistence,
            lacunarity=noise_lacunarity,
            seed=noise_seed,
            amplitude=noise_amplitude
        )
        
        noise_map = generator.generate(size)
        
        # Apply to heightmap
        heightmap_data[:] = noise_map + base_height

class FilterEntity(Entity):
    def __init__(self, name="Filter", filter_type="Noise"):
        super().__init__(name)
        self.filter_type = filter_type
        
        if filter_type == "Noise":
            self.define_property("Scale", float, 100.0, 10.0, 500.0)
            self.define_property("Strength", float, 20.0, 0.0, 100.0)
            self.define_property("Seed", int, 0, 0, 100)
        elif filter_type == "Erosion":
            self.define_property("Iterations", int, 10, 1, 100)
            self.define_property("Rain Amount", float, 0.1, 0.0, 1.0)

    def on_process(self, heightmap_data, mask):
        import noise
        
        if self.filter_type == "Noise":
            scale = self.get_property("Scale")
            strength = self.get_property("Strength")
            seed = self.get_property("Seed")
            
            rows, cols = heightmap_data.shape
            
            # This is slow per-pixel, usually we vectorise or use C++ modules.
            # For prototype, we generate a block.
            # Using vectorised noise or pre-generated would be better.
            
            # Simple optimization: Use a pre-generated noise generic method?
            # For now, let's just do a simple numpy random loop or library call.
            # Doing per-pixel python loop is deadly slow.
            
            # Fast simple noise for now (Random Uniform interpolated? or just Perlin from library if fast)
            # The 'noise' library is C-extension, so it's "okay" but loop is python.
            
            base = np.zeros_like(heightmap_data)
            # ... implementation of noise ...
            # Let's use a placeholder fast operation for now to prove architecture
            
            rng = np.random.default_rng(seed)
            if mask is not None:
                # Apply only where mask > 0
                delta = rng.uniform(-1, 1, heightmap_data.shape) * strength
                heightmap_data += delta * mask
            else:
                delta = rng.uniform(-1, 1, heightmap_data.shape) * strength
                heightmap_data += delta

class MaskEntity(Entity):
    def __init__(self, name="Mask"):
        super().__init__(name)
        self.define_property("Invert", bool, False)
        # Mask data would be stored here (texture)
        self.mask_data = None
        
    def process(self, heightmap_data, mask=None):
        # Mask overrides the parent mask (intersection) or creates new scope
        
        # 1. Calculate MY mask (e.g. from texture or brush)
        current_scope_mask = self.mask_data if self.mask_data is not None else np.ones_like(heightmap_data)
        
        if self.get_property("Invert"):
            current_scope_mask = 1.0 - current_scope_mask
            
        # 2. Combine with parent mask
        if mask is not None:
             final_mask = mask * current_scope_mask
        else:
            final_mask = current_scope_mask
            
        # 3. Process Children with this NEW mask
        for child in self._children:
            if child._enabled:
                child.process(heightmap_data, final_mask)
