
import numpy as np
from scipy.ndimage import zoom

def generate_perlin_noise_2d_fast(shape, scale=100.0, octaves=6, persistence=0.5, lacunarity=2.0, seed=0, terrain_size=1000.0, style="Standard"):
    """
    Fast Perlin-like noise using scipy interpolation.
    Styles: Standard, Billowy, Ridged, Plateau
    """
    np.random.seed(seed)
    
    height, width = shape
    noise = np.zeros(shape, dtype=np.float32)
    max_amp = 0.0
    
    for octave in range(octaves):
        freq = lacunarity ** octave
        amp = persistence ** octave
        max_amp += amp
        
        # Calculate grid density based on physical unit scaling
        # Avoid division by zero
        wavelength = scale / freq if freq > 0 else scale
        if wavelength < 0.001: wavelength = 0.001
            
        density = max(4, int(terrain_size / wavelength))
        grid = np.random.randn(density, density).astype(np.float32)
        
        # Upsample to full resolution using smooth interpolation
        zoom_factor = (height / density, width / density)
        octave_noise = zoom(grid, zoom_factor, order=3)  # Cubic interpolation
        
        # Ensure exact size
        octave_noise = octave_noise[:height, :width]
        
        # Apply Style
        if style == "Billowy":
            octave_noise = np.abs(octave_noise) * 2.0 - 1.0 
        elif style == "Ridged":
            octave_noise = 1.0 - np.abs(octave_noise)
            octave_noise = octave_noise * 2.0 - 1.0
        elif style == "Plateau":
             octave_noise = np.clip(octave_noise * 2.0, -1.0, 1.0)
             
        noise += octave_noise * amp
        
    # Normalize result roughly to -1..1
    if max_amp > 0:
        noise /= max_amp
    
    return noise


class PerlinNoiseGenerator:
    """Fast Perlin noise generator using scipy zoom interpolation"""
    
    def __init__(self, scale=100.0, octaves=6, persistence=0.5, lacunarity=2.0, seed=0, amplitude=50.0, style="Standard"):
        self.scale = scale
        self.octaves = octaves
        self.persistence = persistence
        self.lacunarity = lacunarity
        self.seed = seed
        self.amplitude = amplitude
        self.style = style
    
    def generate(self, size, terrain_size=1000.0):
        """Generate Perlin noise heightmap"""
        noise = generate_perlin_noise_2d_fast(
            (size, size),
            scale=self.scale,
            octaves=self.octaves,
            persistence=self.persistence,
            lacunarity=self.lacunarity,
            seed=self.seed,
            terrain_size=terrain_size,
            style=self.style
        )
        
        # Scale to desired amplitude
        return noise * self.amplitude
