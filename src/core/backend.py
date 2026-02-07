import numpy as np
import sys

import os

# Try to import cupy and perform a smoke test
try:
    # Check for environment variable to force CPU usage
    if os.environ.get("TERRANO_NO_CUDA", "0") == "1":
        raise ImportError("CUDA disabled by user")
    import cupy as cp
    # Smoke test: Verify we can actually use the GPU
    # This catches incorrect installations (e.g. missing CUDA DLLs)
    dev_count = cp.cuda.runtime.getDeviceCount()
    if dev_count > 0:
        # Perform a dummy allocation and operation to ensure memory and libraries (NVRTC) are accessible
        # Note: NVRTC is often lazy loaded, so we force a kernel compile/execution here.
        # Simple array creation
        t = cp.array([1.0])
        # Simple operation to trigger kernel compilation
        res = t + t
        # Synchronize to ensure it actually ran
        cp.cuda.Stream.null.synchronize()
        
        HAS_CUPY = True
        print(f"CuPy available. Found {dev_count} device(s). Using GPU acceleration.")
    else:
        HAS_CUPY = False
        print("CuPy installed but no CUDA devices found. Falling back to CPU.")
except Exception as e:
    # Catch ImportError, RuntimeError (missing DLLs), etc.
    HAS_CUPY = False
    if str(e) == "CUDA disabled by user":
         print("CUDA disabled by user. Using CPU backend.")
    else:
        print(f"CuPy initialization failed: {e}")
        print("Falling back to CPU (NumPy).")

# Select backend
if HAS_CUPY:
    xp = cp
    import cupyx.scipy.ndimage as ndimage
else:
    xp = np
    import scipy.ndimage as ndimage

def get_backend():
    return xp

def to_cpu(array):
    """
    Moves array to CPU (NumPy) if it's on GPU (CuPy).
    If it's already a NumPy array, returns it as is.
    """
    if HAS_CUPY and isinstance(array, cp.ndarray):
        return array.get()
    return array

def to_device(array):
    """
    Moves array to default Device (GPU) if CuPy is available.
    If CuPy is not available or array is already on device/numpy, handles appropriately.
    """
    if HAS_CUPY:
        return cp.asarray(array)
    return np.asarray(array)

def synchronize():
    """Wait for GPU to finish operations."""
    if HAS_CUPY:
        cp.cuda.Stream.null.synchronize()
