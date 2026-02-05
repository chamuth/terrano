
import numpy as np
from scipy.interpolate import splprep, splev

class RoadNode:
    def __init__(self, x, z, width=10.0):
        self.position = np.array([x, 0, z], dtype=np.float32)
        self.width = width

class RoadSegment:
    def __init__(self, node_a, node_b):
        self.start = node_a
        self.end = node_b
        self.points = [] # Interpolated points

    def interpolate(self, num_points=20):
        # Simple linear for now, or if we have a chain we use splines on the network
        # Let's just do linear for a single segment independent of others for simplicity first
        # But for roads we want curves.
        
        # Actually, interpolation is better handled by the Network class on lists of nodes
        pass

class RoadNetwork:
    def __init__(self):
        self.nodes = []
        self.segments = []
        
    def add_node(self, x, z):
        node = RoadNode(x, z)
        if self.nodes:
            # Auto-connect to last node for this prototype
            prev = self.nodes[-1]
            self.segments.append(RoadSegment(prev, node))
        self.nodes.append(node)
        
    def get_spline_points(self, resolution=500):
        if len(self.nodes) < 2:
            return []
            
        # Extract coordinates
        x = [n.position[0] for n in self.nodes]
        z = [n.position[2] for n in self.nodes]
        
        # Spline interpolation
        # k=3 (cubic) requires > 3 points. k=1 for 2 points.
        k = 3 if len(self.nodes) > 3 else 1
        if len(self.nodes) == 3: k = 2
        
        try:
            tck, u = splprep([x, z], s=0, k=k)
            u_new = np.linspace(0, 1, resolution)
            new_points = splev(u_new, tck)
            
            # Format as Nx2
            return np.stack(new_points, axis=1)
        except Exception as e:
            print(f"Spline error: {e}")
            return []

    def clear(self):
        self.nodes = []
        self.segments = []
