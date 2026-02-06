"""
Comprehensive noise library for terrain generation.
Includes Simplex, Gabor, Alligator, Voronoi, and Pattern generators.
"""
import numpy as np
from scipy.spatial import cKDTree


class SimplexNoiseGenerator:
    """
    OpenSimplex Noise (patent-free Simplex implementation)
    
    Produces smooth, continuous noise with fewer directional artifacts than Perlin.
    Uses a simplex grid (triangular in 2D) instead of square grid.
    """
    
    def __init__(self, scale=100.0, octaves=6, persistence=0.5, lacunarity=2.0, seed=42, amplitude=50.0):
        self.scale = scale
        self.octaves = octaves
        self.persistence = persistence
        self.lacunarity = lacunarity
        self.seed = seed
        self.amplitude = amplitude
        
    def _grad2(self, hash_val, x, y):
        """Generate 2D gradient from hash."""
        h = hash_val & 7
        u = np.where(h < 4, x, y)
        v = np.where(h < 4, y, x)
        return np.where((h & 1) == 0, u, -u) + np.where((h & 2) == 0, v, -v)
    
    def _noise2d(self, x, y, perm):
        """Core 2D simplex noise function."""
        # Skew input space to determine simplex cell
        F2 = 0.5 * (np.sqrt(3.0) - 1.0)
        s = (x + y) * F2
        i = np.floor(x + s).astype(int)
        j = np.floor(y + s).astype(int)
        
        # Unskew cell origin
        G2 = (3.0 - np.sqrt(3.0)) / 6.0
        t = (i + j) * G2
        X0 = i - t
        Y0 = j - t
        x0 = x - X0
        y0 = y - Y0
        
        # Determine simplex (triangle) we're in
        i1 = (x0 > y0).astype(int)
        j1 = (x0 <= y0).astype(int)
        
        # Offsets for middle and last corners
        x1 = x0 - i1 + G2
        y1 = y0 - j1 + G2
        x2 = x0 - 1.0 + 2.0 * G2
        y2 = y0 - 1.0 + 2.0 * G2
        
        # Hash coordinates
        ii = i & 255
        jj = j & 255
        gi0 = perm[ii + perm[jj]] % 8
        gi1 = perm[ii + i1 + perm[jj + j1]] % 8
        gi2 = perm[ii + 1 + perm[jj + 1]] % 8
        
        # Calculate contributions from three corners
        t0 = 0.5 - x0*x0 - y0*y0
        n0 = np.where(t0 < 0, 0, t0**4 * self._grad2(gi0, x0, y0))
        
        t1 = 0.5 - x1*x1 - y1*y1
        n1 = np.where(t1 < 0, 0, t1**4 * self._grad2(gi1, x1, y1))
        
        t2 = 0.5 - x2*x2 - y2*y2
        n2 = np.where(t2 < 0, 0, t2**4 * self._grad2(gi2, x2, y2))
        
        # Sum and scale
        return 70.0 * (n0 + n1 + n2)
    
    def generate(self, size, terrain_size=1000.0):
        """Generate Simplex noise heightmap."""
        np.random.seed(self.seed)
        
        # Create permutation table
        p = np.arange(256, dtype=int)
        np.random.shuffle(p)
        perm = np.concatenate([p, p])  # Repeat for wrapping
        
        # Generate coordinate grid
        pixels_per_unit = size / terrain_size
        
        heightmap = np.zeros((size, size), dtype=np.float32)
        
        # Layered octaves
        amplitude = self.amplitude
        frequency = 1.0 / (self.scale * pixels_per_unit)
        
        for octave in range(self.octaves):
            # Create coordinate meshgrid
            y_coords, x_coords = np.mgrid[0:size, 0:size]
            x_scaled = x_coords * frequency
            y_scaled = y_coords * frequency
            
            # Generate noise for this octave
            noise = self._noise2d(x_scaled, y_scaled, perm)
            heightmap += noise * amplitude
            
            # Update for next octave
            amplitude *= self.persistence
            frequency *= self.lacunarity
        
        return heightmap


class GaborNoiseGenerator:
    """
    Gabor Noise (Sparse Convolution with spectral control)
    
    Creates oriented, streaky patterns with precise frequency control.
    Good for simulating layered geological features.
    """
    
    def __init__(self, frequency=0.05, orientation=0.0, bandwidth=1.0, 
                 impulses=50, seed=42, amplitude=50.0):
        self.frequency = frequency  # Principal frequency (cycles per pixel)
        self.orientation = orientation  # Orientation in degrees
        self.bandwidth = bandwidth  # Frequency bandwidth
        self.impulses = impulses  # Number of kernels
        self.seed = seed
        self.amplitude = amplitude
    
    def _gabor_kernel(self, size, frequency, theta, bandwidth):
        """Create a Gabor kernel."""
        center = size // 2
        y, x = np.ogrid[-center:center+1, -center:center+1]
        
        # Rotate coordinates
        theta_rad = np.deg2rad(theta)
        x_theta = x * np.cos(theta_rad) + y * np.sin(theta_rad)
        y_theta = -x * np.sin(theta_rad) + y * np.cos(theta_rad)
        
        # Gaussian envelope
        sigma = 1.0 / (bandwidth * frequency * 2 * np.pi)
        gaussian = np.exp(-(x_theta**2 + y_theta**2) / (2 * sigma**2))
        
        # Sinusoidal carrier
        sinusoid = np.cos(2 * np.pi * frequency * x_theta)
        
        return gaussian * sinusoid
    
    def generate(self, size, terrain_size=1000.0):
        """Generate Gabor noise heightmap."""
        np.random.seed(self.seed)
        
        heightmap = np.zeros((size, size), dtype=np.float32)
        
        # Kernel size based on frequency
        kernel_size = max(15, int(5.0 / self.frequency))
        if kernel_size % 2 == 0:
            kernel_size += 1
        
        # Random impulse positions
        positions = np.random.rand(self.impulses, 2) * size
        
        # Random weights (bipolar)
        weights = np.random.uniform(-1.0, 1.0, self.impulses)
        
        # Random orientation variations (around base orientation)
        orientations = self.orientation + np.random.uniform(-30, 30, self.impulses)
        
        # Create and place kernels
        for (px, py), weight, theta in zip(positions, weights, orientations):
            kernel = self._gabor_kernel(kernel_size, self.frequency, theta, self.bandwidth)
            
            x, y = int(px), int(py)
            kr = kernel_size // 2
            
            # Calculate bounds
            x0, y0 = x - kr, y - kr
            x1, y1 = x + kr + 1, y + kr + 1
            
            # Kernel bounds
            kx0, ky0 = 0, 0
            kx1, ky1 = kernel_size, kernel_size
            
            # Clip to image
            if x0 < 0:
                kx0 = -x0
                x0 = 0
            if y0 < 0:
                ky0 = -y0
                y0 = 0
            if x1 > size:
                kx1 -= (x1 - size)
                x1 = size
            if y1 > size:
                ky1 -= (y1 - size)
                y1 = size
            
            # Add weighted kernel
            if x0 < x1 and y0 < y1:
                heightmap[y0:y1, x0:x1] += kernel[ky0:ky1, kx0:kx1] * weight
        
        return heightmap * self.amplitude


class AlligatorNoiseGenerator:
    """
    Alligator Noise (Organic cellular pattern)
    
    Similar to Worley but with distinct organic characteristics.
    Creates scale-like, skin-like patterns.
    """
    
    def __init__(self, scale=100.0, jitter=1.0, seed=42, amplitude=50.0):
        self.scale = scale
        self.jitter = jitter  # 0-1, randomness of cell centers
        self.seed = seed
        self.amplitude = amplitude
    
    def generate(self, size, terrain_size=1000.0):
        """Generate Alligator noise heightmap."""
        np.random.seed(self.seed)
        
        # Calculate grid
        pixels_per_unit = size / terrain_size
        num_cells_1d = max(2, int(terrain_size / self.scale))
        
        # Create regular grid of points
        cell_size = size / num_cells_1d
        points = []
        
        for i in range(num_cells_1d + 2):  # Extra border
            for j in range(num_cells_1d + 2):
                # Base position
                x = (i - 1) * cell_size + cell_size / 2
                y = (j - 1) * cell_size + cell_size / 2
                
                # Add jitter
                jitter_amount = self.jitter * cell_size * 0.5
                x += np.random.uniform(-jitter_amount, jitter_amount)
                y += np.random.uniform(-jitter_amount, jitter_amount)
                
                points.append([x, y])
        
        points = np.array(points)
        
        # Build KD-tree
        tree = cKDTree(points)
        
        # Query all pixels
        y_coords, x_coords = np.mgrid[0:size, 0:size]
        query_points = np.column_stack([x_coords.ravel(), y_coords.ravel()])
        
        # Get distances to nearest 3 points
        distances, indices = tree.query(query_points, k=3)
        
        # Alligator pattern: combination of F1 and edge detection
        # Use a non-linear combination for organic feel
        d1 = distances[:, 0]
        d2 = distances[:, 1]
        d3 = distances[:, 2]
        
        # Create organic pattern with ridges
        pattern = np.sqrt(d1) - 0.3 * np.sqrt(d2 - d1)
        
        heightmap = pattern.reshape((size, size))
        
        # Normalize
        heightmap = (heightmap - heightmap.min()) / (heightmap.max() - heightmap.min() + 1e-8)
        
        return heightmap * self.amplitude


class PatternGenerator:
    """
    Geometric pattern generator
    
    Creates simple gradients and patterns for masks and foundations.
    """
    
    def __init__(self, pattern_type="Linear Ramp", direction=0.0, center=(0.5, 0.5), 
                 frequency=1.0, amplitude=50.0):
        self.pattern_type = pattern_type
        self.direction = direction  # Degrees for linear ramp
        self.center = center  # Normalized (0-1, 0-1)
        self.frequency = frequency
        self.amplitude = amplitude
    
    def generate(self, size, terrain_size=1000.0):
        """Generate pattern."""
        heightmap = np.zeros((size, size), dtype=np.float32)
        
        # Create normalized coordinate grid
        y, x = np.mgrid[0:size, 0:size]
        x_norm = x / size
        y_norm = y / size
        
        if self.pattern_type == "Linear Ramp":
            # Directional ramp
            theta = np.deg2rad(self.direction)
            heightmap = x_norm * np.cos(theta) + y_norm * np.sin(theta)
            
        elif self.pattern_type == "Radial":
            # Radial gradient from center
            cx, cy = self.center
            dx = x_norm - cx
            dy = y_norm - cy
            heightmap = np.sqrt(dx*dx + dy*dy)
            
        elif self.pattern_type == "Grid":
            # Grid pattern
            freq = self.frequency
            heightmap = np.abs(np.sin(x_norm * freq * np.pi * 2)) * \
                       np.abs(np.sin(y_norm * freq * np.pi * 2))
            
        elif self.pattern_type == "Checker":
            # Checkerboard
            freq = int(self.frequency)
            checker_x = ((x // (size // freq)) % 2).astype(float)
            checker_y = ((y // (size // freq)) % 2).astype(float)
            heightmap = (checker_x + checker_y) % 2
        
        # Normalize to 0-1
        if heightmap.max() > heightmap.min():
            heightmap = (heightmap - heightmap.min()) / (heightmap.max() - heightmap.min())
        
        return heightmap * self.amplitude


class VoronoiGenerator:
    """
    Voronoi/Worley Noise Generator
    
    Generates cellular noise based on distances to randomly distributed feature points.
    Supports F1, F2, and F2-F1 distance metrics.
    """
    
    def __init__(self, scale=100.0, metric="F1", distance_type="euclidean", 
                 seed=42, amplitude=50.0, invert=False):
        self.scale = scale
        self.metric = metric
        self.distance_type = distance_type
        self.seed = seed
        self.amplitude = amplitude
        self.invert = invert
    
    def _distance_metric(self, points, query_points):
        """Calculate distances using specified metric."""
        if self.distance_type == "euclidean":
            p = 2
        elif self.distance_type == "manhattan":
            p = 1
        elif self.distance_type == "chebyshev":
            p = np.inf
        else:
            p = 2
        
        tree = cKDTree(points)
        
        if self.metric == "F1":
            distances, _ = tree.query(query_points, k=1, p=p)
            return distances
        elif self.metric == "F2":
            distances, _ = tree.query(query_points, k=2, p=p)
            return distances[:, 1]
        elif self.metric == "F2-F1":
            distances, _ = tree.query(query_points, k=2, p=p)
            return distances[:, 1] - distances[:, 0]
        else:
            distances, _ = tree.query(query_points, k=1, p=p)
            return distances
    
    def generate(self, size, terrain_size=1000.0):
        """Generate Voronoi noise."""
        np.random.seed(self.seed)
        
        # Calculate number of feature points
        num_cells_1d = max(2, int(terrain_size / self.scale))
        num_cells_1d += 2
        num_points = num_cells_1d * num_cells_1d
        
        # Generate random feature points
        points = np.random.rand(num_points, 2) * (size * 1.2) - (size * 0.1)
        
        # Query grid
        y, x = np.mgrid[0:size, 0:size]
        query_points = np.column_stack([x.ravel(), y.ravel()])
        
        # Calculate distances
        distances = self._distance_metric(points, query_points)
        heightmap = distances.reshape((size, size))
        
        # Normalize
        pixels_per_unit = size / terrain_size
        expected_max = self.scale * pixels_per_unit
        
        if self.metric == "F2-F1":
            expected_max *= 0.5
        
        heightmap = heightmap / expected_max
        heightmap = np.clip(heightmap, 0, 1)
        
        if self.invert:
            heightmap = 1.0 - heightmap
        
        return heightmap * self.amplitude
