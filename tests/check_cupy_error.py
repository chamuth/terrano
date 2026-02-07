import sys
print(f"Python: {sys.version}")

try:
    import cupy
    print("CuPy is installed and imported successfully.")
    print(f"CuPy Version: {cupy.__version__}")
except ImportError as e:
    print("--- Import Error Details ---")
    print(e)
    print("----------------------------")
    print("Recommendation: Please install cupy-cudaXX where XX is your CUDA version.")
    print("Example: pip install cupy-cuda12x")
except Exception as e:
    print(f"Unexpected error: {e}")
