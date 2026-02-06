
import numpy as np
from scipy.ndimage import zoom

def generate_perlin_noise_2d_fast(shape, scale=100.0, octaves=6, persistence=0.5, lacunarity=2.0, seed=0, terrain_size=1000.0):
    """
    Fast Perlin-like noise using scipy interpolation.
    Much faster than pixel-by-pixel approach.
    """
    np.random.seed(seed)
    
    height, width = shape
    noise = np.zeros(shape, dtype=np.float32)
    
    for octave in range(octaves):
        freq = lacunarity ** octave
        amp = persistence ** octave
        
        # Generate small random grid for this octave
        # Generate small random grid for this octave
        # Grid density depends on physical size, not pixel resolution
        # density = terrain_size / (scale / freq)
        
        density = max(4, int(terrain_size / (scale / freq)))
        grid = np.random.randn(density, density).astype(np.float32)
        
        # Upsample to full resolution using smooth interpolation
        zoom_factor = (height / density, width / density)
        octave_noise = zoom(grid, zoom_factor, order=3)  # Cubic interpolation
        
        # Ensure exact size
        octave_noise = octave_noise[:height, :width]
        
        noise += octave_noise * amp
    
    return noise


class PerlinNoiseGenerator:
    """Fast Perlin noise generator using scipy zoom interpolation"""
    
    def __init__(self, scale=100.0, octaves=6, persistence=0.5, lacunarity=2.0, seed=0, amplitude=50.0):
        self.scale = scale
        self.octaves = octaves
        self.persistence = persistence
        self.lacunarity = lacunarity
        self.seed = seed
        self.amplitude = amplitude
    
    def generate(self, size, terrain_size=1000.0):
        """Generate Perlin noise heightmap"""
        noise = generate_perlin_noise_2d_fast(
            (size, size),
            scale=self.scale,
            octaves=self.octaves,
            persistence=self.persistence,
            lacunarity=self.lacunarity,
            seed=self.seed,
            terrain_size=terrain_size
        )
        
        # Scale to desired amplitude
        return noise * self.amplitude
