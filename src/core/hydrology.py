
import numpy as np
import heapq
from src.core.backend import to_cpu, to_device, xp, ndimage

def fill_sinks(dem):
    """
    Fills depressions in a DEM using the Priority-Flood algorithm (Barnes et al., 2014).
    This ensures water can always flow to the edge of the terrain.
    
    Args:
        dem: Input Digital Elevation Model.
        
    Returns:
        Filled DEM.
    """
    dem_cpu = to_cpu(dem).astype(np.float32)
    rows, cols = dem_cpu.shape
    
    # "Spill" elevation array, init with infinity
    spill = np.full_like(dem_cpu, np.inf)
    
    # Closed set (visited)
    closed = np.zeros_like(dem_cpu, dtype=bool)
    
    # Priority Queue: (elevation, r, c)
    open_list = []
    
    # 1. Initialize with edge cells
    # Top and Bottom rows
    for c in range(cols):
        heapq.heappush(open_list, (dem_cpu[0, c], 0, c))
        heapq.heappush(open_list, (dem_cpu[rows-1, c], rows-1, c))
        closed[0, c] = True
        closed[rows-1, c] = True
        spill[0, c] = dem_cpu[0, c]
        spill[rows-1, c] = dem_cpu[rows-1, c]

    # Left and Right cols (excluding corners already added)
    for r in range(1, rows-1):
        heapq.heappush(open_list, (dem_cpu[r, 0], r, 0))
        heapq.heappush(open_list, (dem_cpu[r, cols-1], r, cols-1))
        closed[r, 0] = True
        closed[r, cols-1] = True
        spill[r, 0] = dem_cpu[r, 0]
        spill[r, cols-1] = dem_cpu[r, cols-1]
        
    # Directions (D8)
    d_r = [-1, -1, -1, 0, 0, 1, 1, 1]
    d_c = [-1, 0, 1, -1, 1, -1, 0, 1]
    
    # 2. Process Queue
    while open_list:
        e, r, c = heapq.heappop(open_list)
        
        for i in range(8):
            nr, nc = r + d_r[i], c + d_c[i]
            
            if 0 <= nr < rows and 0 <= nc < cols:
                if not closed[nr, nc]:
                    closed[nr, nc] = True
                    
                    neighbor_elev = dem_cpu[nr, nc]
                    # The spill elevation is max(current_spill_source, neighbor_original_elev)
                    next_spill = max(neighbor_elev, e)
                    
                    spill[nr, nc] = next_spill
                    heapq.heappush(open_list, (next_spill, nr, nc))
                    
    # Return to original device
    # If input was GPU/CuPy array, return as such
    if hasattr(dem, 'device'): 
        return to_device(spill)
    return spill

def compute_flow_accumulation(dem):
    """
    Computes D8 Flow Accumulation.
    
    Args:
        dem: Filled DEM.
        
    Returns:
        Accumulation array (number of upstream cells).
    """
    dem_cpu = to_cpu(dem).astype(np.float32)
    rows, cols = dem_cpu.shape
    
    # 1. Flatten and Sort indices by elevation (descending)
    # We process high cells first, pushing their flow to lower neighbors.
    flat_indices = np.argsort(dem_cpu.ravel())[::-1] 
    
    # Accumulation array (init with 1 for rainfall on self)
    acc = np.ones((rows, cols), dtype=np.float32)
    
    # Pre-compute strides for fast neighbor access in 1D
    # But neighbor access in 2D is clearer for edge checking.
    
    # D8 Offsets
    d_r = np.array([-1, -1, -1, 0, 0, 1, 1, 1])
    d_c = np.array([-1, 0, 1, -1, 1, -1, 0, 1])
    
    # Optimization: Numba would be ideal. Pure Python loop is slow for 1k^2 (1M iters).
    # Since we don't have Numba, we rely on the fact that this is "Offline" processing (Filter step)
    # and 1M iterations in basic Python takes ~0.5-1.0s, which is acceptable for a "Filter apply".
    
    for idx_flat in flat_indices:
        r, c = divmod(idx_flat, cols)
        
        my_elev = dem_cpu[r, c]
        min_elev = my_elev
        receiver_r, receiver_c = -1, -1
        
        # Check 8 neighbors
        # We look for the steepest descent neighbor
        for i in range(8):
            nr, nc = r + d_r[i], c + d_c[i]
            
            # Boundary check
            if 0 <= nr < rows and 0 <= nc < cols:
                neighbor_elev = dem_cpu[nr, nc]
                if neighbor_elev < min_elev:
                    min_elev = neighbor_elev
                    receiver_r, receiver_c = nr, nc
        
        # If we found a lower neighbor, pass our flow to it
        if receiver_r != -1:
            acc[receiver_r, receiver_c] += acc[r, c]
            
    if hasattr(dem, 'device'):
        return to_device(acc)
    return acc

def carve_rivers(heightmap, accumulation, threshold=100.0, strength=1.0, width=1.0):
    """
    Carves rivers into heightmap based on accumulation.
    """
    hm = xp.asarray(heightmap) # Ensure on device/numpy
    acc = xp.asarray(accumulation)
    
    # 1. River Mask
    # Log-scale accumulation is often used for visualization, but for carving depth:
    # Large rivers (high acc) should be deeper.
    # New Height = Old Height - (sqrt(acc) * strength)
    
    # Only apply where acc > threshold
    
    # Calculate carving map
    # We use sqrt(acc) to dampen the extreme values (e.g. 1M vs 100)
    # subtract threshold first?
    
    # Let's say: 
    # if acc < threshold: carve = 0
    # else: carve = (log(acc) - log(threshold)) * strength
    
    # Using xp (numpy/cupy)
    river_mask = (acc > threshold).astype(xp.float32)
    
    # Safe log: log(max(acc, 1e-6))
    log_acc = xp.log1p(acc)
    log_threshold = xp.log1p(threshold)
    
    intensity = xp.maximum(0.0, log_acc - log_threshold)
    
    # Carve Amount
    carve_map = intensity * strength
    
    # Smooth the carve map to create "width"
    if width > 0.1:
        # Use simple gaussian blur
        carve_map = ndimage.gaussian_filter(carve_map, sigma=width)
        
    return hm - carve_map
