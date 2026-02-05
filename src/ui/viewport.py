
from PyQt6.QtWidgets import QWidget, QVBoxLayout
import vispy.scene
import vispy.scene.cameras
from vispy.scene import visuals
import vispy.visuals.transforms 
import numpy as np

class TerrainViewport(QWidget):
    def __init__(self, terrain_data, road_network, on_click_callback=None, on_paint_callback=None, parent=None):
        super().__init__(parent)
        self.terrain_data = terrain_data
        self.road_network = road_network
        self.on_click_callback = on_click_callback
        self.on_paint_callback = on_paint_callback
        
        # Vispy Canvas
        self.canvas = vispy.scene.SceneCanvas(keys='interactive', show=True, parent=self)
        self.view = self.canvas.central_widget.add_view()
        
        # Camera Setup (Y-up for XZ terrain, 45-degree top-down view)
        # Distance increased to view 1km terrain
        self.view.camera = vispy.scene.cameras.TurntableCamera(up='+y', elevation=45, azimuth=-45, fov=45, distance=1500)
        
        # Events
        self.canvas.events.mouse_press.connect(self.on_mouse_press)
        
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.canvas.native)
        self.setLayout(self.layout)
        
        # Visuals
        # Custom fading grid (1km terrain, 100m spacing, fades at 2km)
        from src.ui.fading_grid import FadingGrid
        self.grid = FadingGrid(size=1000, spacing=100, fade_distance=2000, parent=self.view.scene)
        # Grid is already in XZ plane, no rotation needed 
        
        # Terrain Mesh
        # Setting shading to smooth now that faces are fixed (Nx3)
        self.mesh = visuals.Mesh(shading='smooth', color='gray', parent=self.view.scene)
        
        # Pathfinder Widget (Axis)
        self.axis = visuals.XYZAxis(parent=self.view.scene, width=5)
        # We can position it or make a separate ViewBox for it to stay in corner.
        # For now, just placing it at origin for reference.
        
        # Road Visuals
        self.road_line = visuals.Line(pos=np.array([[0,0,0], [0,0,0]]), color='red', width=10, parent=self.view.scene, method='gl')
        self.road_nodes = visuals.Markers(parent=self.view.scene)
        
        # Brush Cursor (Circle on terrain)
        self.brush_cursor = None
        self.brush_radius = 10.0
        self.create_brush_cursor()
        
        # Brush state
        self.is_painting = False
        self.brush_position = None
        
        # Connect mouse events
        self.canvas.events.mouse_move.connect(self.on_mouse_move)
        self.canvas.events.mouse_release.connect(self.on_mouse_release)

        self.update_mesh()
    
    def create_brush_cursor(self):
        """Create a circular cursor for the brush"""
        # Create circle vertices
        num_points = 32
        angles = np.linspace(0, 2*np.pi, num_points)
        x = np.cos(angles) * self.brush_radius
        z = np.sin(angles) * self.brush_radius
        y = np.ones(num_points) * 0.5  # Slightly above terrain
        
        pos = np.column_stack([x, y, z]).astype(np.float32)
        self.brush_cursor = visuals.Line(pos=pos, color='yellow', width=3, parent=self.view.scene, method='gl', connect='strip')
        self.brush_cursor.visible = False
    
    def update_brush_cursor(self, world_x, world_z):
        """Update brush cursor position"""
        if self.brush_cursor is None:
            return
            
        num_points = 32
        angles = np.linspace(0, 2*np.pi, num_points)
        x = world_x + np.cos(angles) * self.brush_radius
        z = world_z + np.sin(angles) * self.brush_radius
        y = np.ones(num_points) * 0.5
        
        pos = np.column_stack([x, y, z]).astype(np.float32)
        self.brush_cursor.set_data(pos=pos, connect='strip')
        self.brush_cursor.visible = True
        self.canvas.update()
    
    def on_mouse_move(self, event):
        """Handle mouse movement for brush cursor"""
        # Get world position
        world_pos = self.get_world_position(event.pos)
        if world_pos is not None:
            self.brush_position = world_pos
            self.update_brush_cursor(world_pos[0], world_pos[2])
            
            # If painting (mouse held down), apply brush
            if self.is_painting and hasattr(self, 'on_paint_callback') and self.on_paint_callback:
                self.on_paint_callback(world_pos[0], world_pos[2], self.brush_radius)
    
    def on_mouse_release(self, event):
        """Handle mouse release"""
        self.is_painting = False
    
    def get_world_position(self, canvas_pos):
        """Convert canvas position to world position on Y=0 plane"""
        try:
            transform = self.view.get_transform('canvas', 'visual')
            x, y = canvas_pos
            
            p1 = transform.map([x, y, 0])  # Near
            p2 = transform.map([x, y, 1])  # Far
            
            # Ray: P = p1 + t * (p2 - p1)
            # Intersect with Y=0 plane
            vec = p2 - p1
            if abs(vec[1]) > 1e-6:
                t = -p1[1] / vec[1]
                if t >= 0:
                    intersection = p1 + t * vec
                    return intersection
        except Exception as e:
            pass
        return None

    def on_mouse_press(self, event):
        if event.button == 1:  # Left click
            # Start painting
            self.is_painting = True
            
            # Get world position and trigger paint
            world_pos = self.get_world_position(event.pos)
            if world_pos is not None and hasattr(self, 'on_paint_callback') and self.on_paint_callback:
                self.on_paint_callback(world_pos[0], world_pos[2], self.brush_radius)
            
            # Also call the old click callback if it exists
            if self.on_click_callback and world_pos is not None:
                self.on_click_callback(world_pos[0], world_pos[2])
            # Get ray from camera
            # Transform mouse coords to normalized device coords (-1 to 1)
            # Then unproject? Vispy makes this hard.
            # Easier: View.scene.transform...
            pass
            
            # Simple approach: Vispy Scene has a method to picking or mapping
            # transform = self.view.scene.transform
            # map_to_visual(visual, [x,y])
            
            # Let's try visual.transform.map(pos) inverse?
            # Actually, standard way is:
            tr = self.canvas.scene.node_transform(self.view.scene)
            # This gives transform from canvas to scene (world)
            
            # Vispy's event.pos is (x, y) in canvas pixels
            # We need to raycast.
            
            # Simplified: Use the Camera's transform
            # Ray direction
            # For now, let's implement a simplified planar intersection assuming Y=0 (or somewhat close)
            # This is complex in pure Vispy without helper functions.
            
            # Workaround:
            # We can use the camera internals.
            # But wait, if we are in "Road Mode", we want to pick.
            # Let's assume the user CLICKS on the grid.
            
            # Using the `scene.visuals.Plane` approach or `transform`.
            
            # Let's try to pass the event to a helper or just print for now?
            # No, user wants it to work.
            
            # Implementation of ray-plane intersection:
            # 1. NDC coordinates
            w, h = self.canvas.size
            x, y = event.pos
            ndc_x = 2.0 * x / w - 1.0
            ndc_y = 1.0 - 2.0 * y / h # Flip Y
            
            # 2. Inverse ViewProjection Matrix
            # self.view.camera.transform gives World -> Cam
            # We need the full projection.
            
            # Can we use `view.get_transform('canvas', 'scene')`?
            try:
                transform = self.view.get_transform('canvas', 'visual')
                # this maps generic canvas to visual local.
                # Let's map to the Grid (which is at 0,0,0 world)
                
                # Intersect ray with plane Y=0? 
                # transform.map([x, y]) often returns a point on the near plane or projected.
                
                p1 = transform.map([x, y, 0]) # Near
                p2 = transform.map([x, y, 1]) # Far
                
                # Ray: P = p1 + t * (p2 - p1)
                # We want P.y = 0
                # 0 = p1.y + t * (p2.y - p1.y)
                # t = -p1.y / (p2.y - p1.y)
                
                vec = p2 - p1
                if abs(vec[1]) > 1e-6:
                    t = -p1[1] / vec[1]
                    intersection = p1 + t * vec
                    
                    # Valid intersection?
                    if t >= 0:
                        self.on_click_callback(intersection[0], intersection[2])
            except Exception as e:
                print(f"Picking error: {e}")


    def update_mesh(self):
        # Update Terrain
        vertices, normals, faces = self.terrain_data.get_vertex_data()
        
        # Ensure types for Vispy (Critical)
        vertices = vertices.astype(np.float32)
        normals = normals.astype(np.float32)
        faces = faces.astype(np.uint32)
        
        # Coloring based on height
        y = vertices[:, 1]
        colors = np.ones((len(vertices), 4), dtype=np.float32)
        # Gradient
        mn, mx = -50, 50 # expected range
        # Avoid divide by zero
        if mx - mn < 1e-6:
            div = 1.0
        else:
            div = mx - mn
            
        norm = np.clip((y - mn) / div, 0, 1)
        colors[:, 0] = norm # R
        colors[:, 1] = 0.5 + 0.2*norm # G
        colors[:, 2] = 0.2 # B
        
        if np.isnan(vertices).any() or np.isinf(vertices).any():
            print("ERROR: Vertices contain NaN or Inf!")
            return

        # Debug stats
        print(f"Mesh Update: V={vertices.shape}, F={faces.shape}")
        
        # Pass normals expressly to avoid recalc issues
        # Vispy set_data doesn't take normals directly, removing it. 
        # The float32 cast above should fix the original warning.
        # SIMPLIFICATION: Removing colors for debug
        self.mesh.set_data(vertices=vertices, faces=faces) #, vertex_colors=colors)
        
        # Update Road
        spline = self.road_network.get_spline_points()
        if len(spline) > 0:
            # Spline is Nx2 (x,z), need y
            # For visualization, let's just put it slightly above 0 or at terrain height
            # For now, y=10 to be visible over 0-flat terrain
            y_road = np.ones(len(spline)) * 2.0 
            pos = np.stack([spline[:,0], y_road, spline[:,1]], axis=1).astype(np.float32)
            self.road_line.set_data(pos=pos, connect='strip')
        else:
            self.road_line.set_data(pos=np.array([[0,0,0]], dtype=np.float32))
            
        # Update Nodes
        if len(self.road_network.nodes) > 0:
            nx = [n.position[0] for n in self.road_network.nodes]
            nz = [n.position[2] for n in self.road_network.nodes]
            ny = [2.0] * len(nx)
            npos = np.stack([nx, ny, nz], axis=1).astype(np.float32)
            self.road_nodes.set_data(pos=npos, face_color='blue', size=10)
        else:
            self.road_nodes.set_data(pos=None)

        self.canvas.update()
