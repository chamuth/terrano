
import numpy as np

class TerrainData:
    def __init__(self, size=1024, scale=1000.0):
        """
        Args:
            size: Resolution of heightmap (1024x1024 grid)
            scale: Physical size in world units (1000 = 1km)
        """
        self.size = size
        self.scale = scale
        self.heightmap = np.zeros((size, size), dtype=np.float32)
        self.roads = None # RoadNetwork reference
        
    @property
    def shape(self):
        return self.heightmap.shape
        
    def reset(self):
        self.heightmap.fill(0.0)

    def get_vertex_data(self):
        rows, cols = self.heightmap.shape
        # X: -size/2 to size/2
        # Z: -size/2 to size/2
        
        x = np.linspace(-self.size/2, self.size/2, cols)
        z = np.linspace(-self.size/2, self.size/2, rows)
        xv, zv = np.meshgrid(x, z)
        
        # Stack vertices [xv, height, zv]
        vertices = np.stack([xv, self.heightmap, zv], axis=2).reshape(-1, 3)
        
        # Calculate normals efficiently
        dy, dx = np.gradient(self.heightmap)
        spacing = self.size / (rows - 1)
        dx = dx / spacing
        dy = dy / spacing
        
        # Normal vector (-dx, 1, -dy)
        normals = np.stack([-dx, np.ones_like(dy), -dy], axis=2).reshape(-1, 3)
        # Normalize
        norm_lens = np.linalg.norm(normals, axis=1, keepdims=True)
        normals = (normals / norm_lens).astype(np.float32)
        
        # Indices
        # Cache this if size is constant for performance
        c_idx = np.arange(cols * rows).reshape(rows, cols)
        
        # Quads: 
        # TL(r,c) -- TR(r,c+1)
        # |             |
        # BL(r+1,c) -- BR(r+1,c+1)
        
        # Top-left of triangle 1
        tl = c_idx[:-1, :-1].flatten()
        tr = c_idx[:-1, 1:].flatten()
        bl = c_idx[1:, :-1].flatten()
        br = c_idx[1:, 1:].flatten()
        
        # Tri 1: TL, BL, BR
        # Tri 2: TL, BR, TR
        
        # We need (N, 3) for Vispy faces usually
        # Stack columns, then reshape
        indices = np.column_stack([tl, bl, br, tl, br, tr]).reshape(-1, 3)
        
        return vertices.astype(np.float32), normals, indices.astype(np.uint32)

    def carve_road(self, road_points, width=10.0, falloff=5.0):
        """
        Simple road carving. 
        Projects road spline onto 2D grid and adjusts height.
        """
        if road_points is None or len(road_points) == 0:
            return

        rows, cols = self.heightmap.shape
        
        # Convert world road points to grid coordinates
        # World: -size/2 to size/2
        # Grid: 0 to size-1
        
        def world_to_grid(wx, wz):
            gx = (wx + self.size/2) / self.size * (cols - 1)
            gz = (wz + self.size/2) / self.size * (rows - 1)
            return gx, gz

        # This is a very robust "brute force" approach for the prototype.
        # For every point in the road spline, we flatten the terrain around it.
        # A shader-based approach or rasterization would be faster for real-time.
        
        # Let's do a mask-based approach. Create a mask of distance to road.
        
        grid_x = np.linspace(-self.size/2, self.size/2, cols)
        grid_z = np.linspace(-self.size/2, self.size/2, rows)
        gv_x, gv_z = np.meshgrid(grid_x, grid_z)
        
        # KDTree or Distance Transform is better, 
        # but for prototype let's just iterate spline segments (subsampled) 
        # and splat height.
        
        # Subsample road points for speed if needed
        # Assuming road_points is dense enough
        
        import scipy.spatial
        
        # Flatten grid for KD-tree query
        grid_points = np.stack([gv_x.ravel(), gv_z.ravel()], axis=1)
        road_tree = scipy.spatial.KDTree(road_points)
        
        # Query distance to nearest road point for every grid point
        # This is slow for 512x512. 
        # Optimization: Only calculate bounding box of road.
        
        dists, idxs = road_tree.query(grid_points, distance_upper_bound=width + falloff)
        
        # Mask where distance < width + falloff
        mask = dists < (width + falloff)
        
        # Mask is 1D, reshape
        mask_2d = mask.reshape(rows, cols)
        
        if not np.any(mask_2d):
            return
            
        # Get target heights from the nearest road calculation
        # idxs has the index of the nearest road point
        valid_indices = idxs[mask]
        # Some indices might be len(road_points) if out of bounds (KDTree feature)
        # Filter them
        valid = valid_indices < len(road_points)
        final_mask_indices = np.where(mask)[0][valid]
        road_indices = valid_indices[valid]
        
        # Height of the road at those nearest points
        # Wait, RoadNode currently has y=0?
        # We need road to follow terrain OR terrain to follow road.
        # Usually road has its own height. For now let's assume road is at terrain height 
        # OR road sets the height.
        # Let's say road is at flat 0 for test, or we sample terrain height at road nodes first?
        
        # For "Carving", usually the road defines the grade.
        # Let's assume road is at constant height 10 for testing
        target_heights = 0.0 # simple test
        
        # Apply
        # Linear falloff
        # dists[final_mask_indices] is distance to centerline
        d = dists[final_mask_indices]
        
        # Alpha: 1.0 at center, 0.0 at edge
        # actually, 1.0 inside width, fading out in falloff
        alpha = np.zeros_like(d)
        
        # Inner part (road surface)
        alpha[d <= width] = 1.0
        
        # Falloff part
        falloff_mask = (d > width)
        alpha[falloff_mask] = 1.0 - (d[falloff_mask] - width) / falloff
        
        # Blend
        current_h = self.heightmap.flatten()[final_mask_indices]
        new_h = current_h * (1 - alpha) + target_heights * alpha
        
        # Write back (need coordinate conversion or direct flat index usage)
        flat_hm = self.heightmap.flatten()
        flat_hm[final_mask_indices] = new_h
        self.heightmap = flat_hm.reshape(rows, cols)

