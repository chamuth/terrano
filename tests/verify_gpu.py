
import sys
import os
import numpy as np

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Force reload of backend to pick up changes if run multiple times
if "src.core.backend" in sys.modules:
    import importlib
    importlib.reload(sys.modules["src.core.backend"])

from src.core.backend import HAS_CUPY, xp, to_cpu, get_backend
from src.core.scene import TerrainEntity, GeneratorEntity, FilterEntity, MaskEntity

def verify_gpu():
    print("--- GPU Verification ---")
    print(f"CuPy Available: {HAS_CUPY}")
    print(f"Backend XP: {xp.__name__}")
    
    if HAS_CUPY:
        import cupy as cp
        print(f"Current Device: {cp.cuda.Device(0).compute_capability}")
    else:
        print("Note: CuPy failed to initialize or valid device not found. Using CPU fallback.")
    
    # 1. Setup Scene
    print("\n--- Setting up Scene ---")
    size = 512
    phys_size = 1000.0
    
    root = TerrainEntity()
    root.set_property("Size", phys_size)
    root.set_property("Resolution", str(size))
    
    # Generator
    gen = GeneratorEntity("Perlin Gen")
    gen.set_parent(root)
    gen.set_property("Type", "Perlin Noise")
    gen.set_property("Scale", 100.0)
    gen.set_property("Amplitude", 50.0)
    
    # Hydraulic Erosion
    erosion = FilterEntity("Hydro")
    erosion.set_parent(root)
    erosion.set_property("Type", "Erosion")
    erosion.set_property("H-Iterations", 5) # Small number for quick test
    
    # Mask
    mask = MaskEntity("Circle Mask")
    mask.set_parent(erosion)
    mask.set_property("Type", "Primitive")
    mask.set_property("Primitive Shape", "Circle")
    mask.set_property("Size", 200.0)
    
    # 2. Process
    print("\n--- Processing ---")
    import time
    start_time = time.time()
    
    # Create initial
    initial = xp.zeros((size, size), dtype=xp.float32)
    
    result, ver = root.process(initial, terrain_size=phys_size)
    
    end_time = time.time()
    print(f"Processing finished in {end_time - start_time:.4f}s")
    
    # 3. Validation
    print("\n--- Validation ---")
    print(f"Result Type: {type(result)}")
    print(f"Result Shape: {result.shape}")
    
    # Check for NaNs
    if xp.any(xp.isnan(result)):
        print("FAILURE: NaNs detected in output!")
    else:
        print("SUCCESS: No NaNs detected.")
        
    center = result[size//2, size//2]
    corner = result[0, 0]
    print(f"Center Height: {center:.2f}")
    print(f"Corner Height: {corner:.2f}")
    
    print("\n--- Verification Complete ---")

if __name__ == "__main__":
    verify_gpu()
