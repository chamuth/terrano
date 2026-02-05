
import numpy as np

class Brush:
    """
    Brush tool for painting on terrain masks.
    """
    def __init__(self, radius=10.0, strength=1.0, falloff='smooth'):
        self.radius = radius
        self.strength = strength
        self.falloff = falloff  # 'smooth', 'linear', 'constant'
        
    def get_influence(self, distance):
        """
        Calculate brush influence at a given distance from center.
        Returns value between 0 and 1.
        """
        if distance > self.radius:
            return 0.0
            
        normalized_dist = distance / self.radius
        
        if self.falloff == 'constant':
            return self.strength
        elif self.falloff == 'linear':
            return self.strength * (1.0 - normalized_dist)
        elif self.falloff == 'smooth':
            # Smooth falloff using cosine
            return self.strength * (np.cos(normalized_dist * np.pi) * 0.5 + 0.5)
        
        return 0.0
    
    def apply_to_mask(self, mask_data, center_x, center_z, size, add_mode=True):
        """
        Apply brush stroke to mask data.
        
        Args:
            mask_data: 2D numpy array (heightmap resolution)
            center_x, center_z: World coordinates
            size: Size of the terrain (to convert world to texture coords)
            add_mode: True to add (paint white), False to subtract (paint black)
        """
        # Convert world coords to texture coords
        # Assuming terrain is centered at 0,0 and spans [-size/2, size/2]
        half_size = size / 2.0
        tex_x = int((center_x + half_size) / size * mask_data.shape[1])
        tex_z = int((center_z + half_size) / size * mask_data.shape[0])
        
        # Clamp to valid range
        tex_x = np.clip(tex_x, 0, mask_data.shape[1] - 1)
        tex_z = np.clip(tex_z, 0, mask_data.shape[0] - 1)
        
        # Calculate pixel radius
        pixel_radius = int(self.radius / size * mask_data.shape[0])
        
        # Apply brush in a square region
        for dy in range(-pixel_radius, pixel_radius + 1):
            for dx in range(-pixel_radius, pixel_radius + 1):
                px = tex_x + dx
                pz = tex_z + dy
                
                if 0 <= px < mask_data.shape[1] and 0 <= pz < mask_data.shape[0]:
                    # Calculate distance
                    dist = np.sqrt(dx*dx + dy*dy) * (size / mask_data.shape[0])
                    influence = self.get_influence(dist)
                    
                    if influence > 0:
                        if add_mode:
                            # Add (paint white)
                            mask_data[pz, px] = np.clip(mask_data[pz, px] + influence, 0.0, 1.0)
                        else:
                            # Subtract (paint black)
                            mask_data[pz, px] = np.clip(mask_data[pz, px] - influence, 0.0, 1.0)
