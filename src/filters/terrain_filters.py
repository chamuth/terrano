"""
Terrain filters for heightfield operations.
Implements Distort by Noise, Terrace, and Clip filters.
"""
import numpy as np
from scipy.ndimage import gaussian_filter


class DistortByNoiseFilter:
    """
    Distort by Noise - Advects terrain through a noise field
    
    Rearranges existing height values by displacing them through
    a noise field, creating natural variation and breaking up patterns.
    """
    
    def __init__(self, noise_type="Perlin", amplitude=10.0, element_size=50.0, 
                 substeps=1, seed=42):
        self.noise_type = noise_type
        self.amplitude = amplitude
        self.element_size = element_size
        self.substeps = max(1, substeps)
        self.seed = seed
    
    def _generate_displacement_field(self, size, terrain_size):
        """Generate 2D displacement vectors using noise."""
        if self.noise_type == "Perlin":
            from src.generators.perlin_noise import PerlinNoiseGenerator
            gen = PerlinNoiseGenerator(self.element_size, 4, 0.5, 2.0, self.seed, 1.0)
            noise_x = gen.generate(size, terrain_size)
            gen_y = PerlinNoiseGenerator(self.element_size, 4, 0.5, 2.0, self.seed + 1, 1.0)
            noise_y = gen_y.generate(size, terrain_size)
            
        elif self.noise_type == "Simplex":
            from src.generators.noise_library import SimplexNoiseGenerator
            gen = SimplexNoiseGenerator(self.element_size, 4, 0.5, 2.0, self.seed, 1.0)
            noise_x = gen.generate(size, terrain_size)
            gen_y = SimplexNoiseGenerator(self.element_size, 4, 0.5, 2.0, self.seed + 1, 1.0)
            noise_y = gen_y.generate(size, terrain_size)
            
        elif self.noise_type == "Curl":
            # Curl noise (perpendicular gradients)
            from src.generators.perlin_noise import PerlinNoiseGenerator
            gen = PerlinNoiseGenerator(self.element_size, 4, 0.5, 2.0, self.seed, 1.0)
            potential = gen.generate(size, terrain_size)
            
            # Compute gradients
            gy, gx = np.gradient(potential)
            # Curl: rotate 90 degrees
            noise_x = -gy
            noise_y = gx
        else:
            noise_x = np.zeros((size, size))
            noise_y = np.zeros((size, size))
        
        return noise_x, noise_y
    
    def apply(self, heightmap, terrain_size=1000.0):
        """Apply distortion filter to heightmap."""
        size = heightmap.shape[0]
        
        # Generate displacement field
        disp_x, disp_y = self._generate_displacement_field(size, terrain_size)
        
        # Scale displacement by amplitude
        pixels_per_unit = size / terrain_size
        disp_x = disp_x * self.amplitude * pixels_per_unit
        disp_y = disp_y * self.amplitude * pixels_per_unit
        
        # Apply displacement in substeps
        result = heightmap.copy()
        step_size = 1.0 / self.substeps
        
        for step in range(self.substeps):
            # Create coordinate grids
            y_coords, x_coords = np.mgrid[0:size, 0:size]
            
            # Apply displacement
            x_new = x_coords + disp_x * step_size
            y_new = y_coords + disp_y * step_size
            
            # Clamp to valid range
            x_new = np.clip(x_new, 0, size - 1)
            y_new = np.clip(y_new, 0, size - 1)
            
            # Bilinear interpolation
            x0 = np.floor(x_new).astype(int)
            x1 = np.clip(x0 + 1, 0, size - 1)
            y0 = np.floor(y_new).astype(int)
            y1 = np.clip(y0 + 1, 0, size - 1)
            
            wx = x_new - x0
            wy = y_new - y0
            
            # Sample and interpolate
            result = (1 - wy) * ((1 - wx) * result[y0, x0] + wx * result[y0, x1]) + \
                     wy * ((1 - wx) * result[y1, x0] + wx * result[y1, x1])
        
        return result


class TerraceFilter:
    """
    Terrace Filter - Creates stepped geological layers
    
    Quantizes height values to create plateau-like formations.
    """
    
    def __init__(self, step_count=10, step_height=None, smoothness=0.1):
        self.step_count = step_count
        self.step_height = step_height  # If None, auto-calculate from range
        self.smoothness = smoothness  # 0-1, blend factor
    
    def apply(self, heightmap, terrain_size=1000.0):
        """Apply terrace filter to heightmap."""
        h_min = heightmap.min()
        h_max = heightmap.max()
        h_range = h_max - h_min
        
        if h_range < 1e-8:
            return heightmap.copy()
        
        # Determine step height
        if self.step_height is not None:
            step_h = self.step_height
        else:
            step_h = h_range / self.step_count
        
        # Normalize to 0-1
        normalized = (heightmap - h_min) / h_range
        
        # Quantize to steps
        step_index = normalized * self.step_count
        terraced = np.floor(step_index) / self.step_count
        
        # Blend with original for smoothness
        if self.smoothness > 0:
            blend_factor = 1.0 - self.smoothness
            terraced = blend_factor * terraced + self.smoothness * normalized
        
        # Scale back to original range
        result = terraced * h_range + h_min
        
        return result


class ClipFilter:
    """
    Clip Filter - Limits height to min/max values
    
    Clamps terrain elevation with optional soft falloff.
    """
    
    def __init__(self, min_height=None, max_height=None, soft_clip_strength=0.0):
        self.min_height = min_height
        self.max_height = max_height
        self.soft_clip_strength = soft_clip_strength  # 0-1, softness
    
    def _soft_clip(self, values, threshold, is_min=True):
        """Apply soft clipping with smooth transition."""
        if self.soft_clip_strength <= 0:
            if is_min:
                return np.maximum(values, threshold)
            else:
                return np.minimum(values, threshold)
        
        # Soft clip range
        soft_range = self.soft_clip_strength * 50.0  # Arbitrary scaling
        
        if is_min:
            # Smooth transition below threshold
            diff = threshold - values
            blend = np.clip(diff / soft_range, 0, 1)
            return values * (1 - blend) + threshold * blend
        else:
            # Smooth transition above threshold
            diff = values - threshold
            blend = np.clip(diff / soft_range, 0, 1)
            return values * (1 - blend) + threshold * blend
    
    def apply(self, heightmap, terrain_size=1000.0):
        """Apply clip filter to heightmap."""
        result = heightmap.copy()
        
        if self.min_height is not None:
            result = self._soft_clip(result, self.min_height, is_min=True)
        
        if self.max_height is not None:
            result = self._soft_clip(result, self.max_height, is_min=False)
        
        return result
