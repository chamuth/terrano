
import numpy as np
from vispy.scene import visuals

class FadingGrid(visuals.Line):
    """
    Custom grid that fades out with distance, similar to Blender.
    """
    def __init__(self, size=1000, spacing=100, fade_distance=2000, **kwargs):
        """
        Args:
            size: Size of the terrain (1km = 1000m)
            spacing: Grid cell size (100m for 10x10 grid)
            fade_distance: Distance at which grid fully fades out
        """
        self.size = size
        self.spacing = spacing
        self.fade_distance = fade_distance
        
        # Generate grid lines
        positions, colors = self._generate_grid()
        
        super().__init__(pos=positions, color=colors, connect='segments', method='gl', **kwargs)
    
    def _generate_grid(self):
        """Generate grid line positions and colors with fade-out"""
        half_size = self.size / 2.0
        fade_start = self.size  # Start fading after terrain size
        
        positions = []
        colors = []
        
        # Calculate number of lines needed to reach fade_distance
        num_lines = int(self.fade_distance / self.spacing)
        
        # Generate lines along X axis (parallel to Z)
        for i in range(-num_lines, num_lines + 1):
            x = i * self.spacing
            
            # Calculate alpha based on distance from center
            dist = abs(x)
            if dist <= fade_start:
                alpha = 0.3  # Full opacity within terrain bounds
            elif dist >= self.fade_distance:
                alpha = 0.0  # Fully transparent at fade distance
            else:
                # Linear fade between fade_start and fade_distance
                alpha = 0.3 * (1.0 - (dist - fade_start) / (self.fade_distance - fade_start))
            
            # Thicker line at center
            if i == 0:
                color = [0.5, 0.5, 0.5, 0.6]  # Brighter center line
            else:
                color = [0.3, 0.3, 0.3, alpha]
            
            # Line from -fade_distance to +fade_distance along Z
            positions.append([x, 0, -self.fade_distance])
            colors.append(color)
            positions.append([x, 0, self.fade_distance])
            colors.append(color)
        
        # Generate lines along Z axis (parallel to X)
        for i in range(-num_lines, num_lines + 1):
            z = i * self.spacing
            
            dist = abs(z)
            if dist <= fade_start:
                alpha = 0.3
            elif dist >= self.fade_distance:
                alpha = 0.0
            else:
                alpha = 0.3 * (1.0 - (dist - fade_start) / (self.fade_distance - fade_start))
            
            if i == 0:
                color = [0.5, 0.5, 0.5, 0.6]
            else:
                color = [0.3, 0.3, 0.3, alpha]
            
            positions.append([-self.fade_distance, 0, z])
            colors.append(color)
            positions.append([self.fade_distance, 0, z])
            colors.append(color)
        
        return np.array(positions, dtype=np.float32), np.array(colors, dtype=np.float32)
