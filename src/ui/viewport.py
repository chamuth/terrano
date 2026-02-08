from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtCore import pyqtSignal
import vispy.scene
import vispy.scene.cameras
import vispy.scene.visuals as visuals
import vispy.gloo as gloo
import numpy as np
import time
from vispy.visuals.filters import ShadingFilter, TextureFilter

class TerrainViewport(QWidget):
    mesh_stats_changed = pyqtSignal(int, int)
    light_direction_changed = pyqtSignal(float, float, float)

    def __init__(self, terrain_data, road_network, on_click_callback=None, on_paint_callback=None, parent=None):
        super().__init__(parent)
        self.terrain_data = terrain_data
        self.mask_data = None # Store mask for visualization
        self.road_network = road_network
        self.on_click_callback = on_click_callback
        self.on_paint_callback = on_paint_callback
        
        
        # Layout
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self.layout)
        
        self.setMinimumSize(0, 0)
        
        # Vispy Canvas
        # IMPORTANT: Do not set parent=self here immediately if we want to add to layout manually.
        # But SceneCanvas auto-creates a backend widget.
        # Recommended pattern for embedding:
        self.canvas = vispy.scene.SceneCanvas(keys='interactive', show=False, parent=None, bgcolor='#202020')
        
        # Add native widget to layout
        self.layout.addWidget(self.canvas.native)
        self.canvas.native.setParent(self)
        
        self.view = self.canvas.central_widget.add_view()
        
        # Camera Setup (Y-up for XZ terrain, 45-degree top-down view)
        # Distance increased to view 1km terrain
        # Camera Setup (Y-up for XZ terrain, 45-degree top-down view)
        # Default ISO view: 45 deg azimuth, 45 deg elevation
        self.view.camera = vispy.scene.cameras.TurntableCamera(up='+y', elevation=45, azimuth=45, fov=45, distance=1500, center=(0, 0, 0))
        
        # ---------------------------------------------------------
        # Orientation Gizmo (Overlay)
        # ---------------------------------------------------------
        # We create a ViewBox that is NOT in the layout, but child of the canvas scene directly.
        # This allows absolute positioning (Overlay).
        self.gizmo_view = vispy.scene.widgets.ViewBox(parent=self.canvas.scene, bgcolor=None)
        
        # Gizmo camera: Fixed distance, syncs rotation only
        # Distance determines gizmo size relative to view
        # Increased scale to make it "zoomed out"
        # interactive=False prevents user from zooming the gizmo independently
        # center=(0, 1, 0) shifts the look-at point up, moving the gizmo down in view to show Y axis
        self.gizmo_view.camera = vispy.scene.cameras.TurntableCamera(up='+y', elevation=150, azimuth=-45, fov=0, distance=150.0, center=(0, 0.5, 0))
        self.gizmo_view.camera.interactive = False
        
        # Add visual to gizmo view
        # We use separate lines for X, Y, Z to allow picking
        # Length 2.0 covers the view nicely at distance 4.0
        origin = np.array([[0,0,0]])
        self.gizmo_x = visuals.Line(pos=np.vstack([origin, [[1,0,0]]]), color='#ff4444', width=2, parent=self.gizmo_view.scene)
        self.gizmo_y = visuals.Line(pos=np.vstack([origin, [[0,1,0]]]), color='#44ff44', width=2, parent=self.gizmo_view.scene)
        self.gizmo_z = visuals.Line(pos=np.vstack([origin, [[0,0,1]]]), color='#4444ff', width=2, parent=self.gizmo_view.scene)
        
        # Add labels
        self.text_x = visuals.Text("X", pos=[1.2, 0, 0], color='#ff4444', font_size=10, bold=True, parent=self.gizmo_view.scene)
        self.text_y = visuals.Text("Y", pos=[0, 1.2, 0], color='#44ff44', font_size=10, bold=True, parent=self.gizmo_view.scene)
        self.text_z = visuals.Text("Z", pos=[0, 0, 1.2], color='#4444ff', font_size=10, bold=True, parent=self.gizmo_view.scene)

        # We hook into draw to sync camera rotation
        self.canvas.events.draw.connect(self.on_draw)
        
        # Events
        self.canvas.events.mouse_press.connect(self.on_mouse_press)
        
        
        # Layout is already set
        # self.layout = QVBoxLayout()
        # self.layout.addWidget(self.canvas.native)
        # self.setLayout(self.layout)
        
        # Visuals
        # Custom fading grid (1km terrain, 100m spacing, fades at 2km)
        from src.ui.fading_grid import FadingGrid
        self.grid = FadingGrid(size=1000, spacing=100, fade_distance=2000, parent=self.view.scene)
        # Grid is already in XZ plane, no rotation needed 
        
        # Terrain Mesh
        # Setting shading to smooth now that faces are fixed (Nx3)
        # Terrain Mesh
        # Setting shading to smooth now that faces are fixed (Nx3)
        # We use a ShadingFilter to control light direction
        # We use a ShadingFilter to control light direction
        # Default Light: Match Camera (Azimuth 45, Elevation 45)
        # Vector approx (10, 14, 10) -> Normalized roughly (0.5, 0.7, 0.5)
        # User requested opposite direction (keeping Y positive for overhead light)
        self.light_dir = (-8, -15, 10) 
        self.shading_filter = ShadingFilter(shading='smooth', light_dir=self.light_dir)
        self.mesh = visuals.Mesh(color='gray', parent=self.view.scene)
        
        # Mask Texture Filter
        # self.mask_texture = visuals.Texture2D(data=np.ones((1024, 1024, 4), dtype=np.float32), interpolation='linear', wrapping='repeat')
        # Placeholder white texture (no tint)
        self.mask_texture = None 
        self.mask_filter = None
        
        # Road Visuals
        self.road_line = visuals.Line(pos=np.array([[0,0,0], [0,0,0]]), color='red', width=10, parent=self.view.scene, method='gl')
        self.road_nodes = visuals.Markers(parent=self.view.scene)
        
        # Brush Cursor (Circle on terrain)
        self.brush_cursor = None
        self.brush_radius = 10.0
        self.brush_visible_override = False
        self.create_brush_cursor()
        
        # Brush state
        self.is_painting = False
        self.is_panning = False
        
        # Brush state
        self.is_painting = False
        self.is_panning = False
        self.is_rotating_light = False
        self.brush_position = None
        
        # Connect mouse events
        self.canvas.events.mouse_move.connect(self.on_mouse_move)
        self.canvas.events.mouse_release.connect(self.on_mouse_release)
        self.canvas.events.resize.connect(self.on_resize)
        
        # We need to filter camera events for panning
        # By default TurntableCamera handles interaction. We want to override it when Shift is pressed.
        # But Vispy camera interaction is hardcoded in its viewbox event handler usually.
        # So we just modify the camera center in our handler.
        
        self.last_pos = None

        self.update_mesh()
        self.mesh.attach(self.shading_filter)
        self.light_direction_changed.emit(*self.light_dir)
        
    def _ensure_mask_filter(self, texcoords=None):
        if self.mask_filter is None:
             # Define dummy data
             data = np.ones((2, 2, 4), dtype=np.float32)
             
             # Create explicit Texture2D for control
             self.mask_texture = gloo.Texture2D(data, interpolation='linear')
             
             # Initialize Filter with DUMMY data to satisfy constructor
             # It will create an internal texture we will immediately replace
             tc = texcoords if texcoords is not None else 'uv'
             self.mask_filter = TextureFilter(data, texcoords=tc)
             
             # OVERRIDE the filter's internal texture with our controllled object
             self.mask_filter.fshader['u_texture'] = self.mask_texture
             
             self.mesh.attach(self.mask_filter)
        elif texcoords is not None:
             # Update texcoords if provided
             self.mask_filter.texcoords = texcoords
        
    def set_data(self, terrain_data):
        """Update the terrain data reference"""
        self.terrain_data = terrain_data
        self.update_mesh()
        
    def set_brush_visible(self, visible):
        """Enable/Disable brush cursor (called by Editor)"""
        self.brush_visible_override = visible
        if not visible and self.brush_cursor:
            self.brush_cursor.visible = False

    def set_mask(self, mask_data):
        """Set mask data for visualization"""
        self.mask_data = mask_data
        # Optimization: Only update colors, not whole mesh
        self.update_colors()
        
    def force_mask_update(self):
        """Force update mask colors ignoring throttle"""
        self._last_color_update = 0
        self.update_colors()

    def reset_camera(self):
        """Reset camera to default view fitting the terrain"""
        self.view.camera.center = (0, 0, 0)
        self.view.camera.azimuth = 45
        self.view.camera.elevation = 45
        # Distance approx 1.5x physical scale if available, else 1500
        dist = 1500
        if hasattr(self.terrain_data, 'scale'):
            dist = self.terrain_data.scale * 1.5
        self.view.camera.distance = dist
        self.canvas.update()

    def on_resize(self, event):
        """Handle layout and overlay positioning"""
        try:
            w, h = event.size
            if w <= 0 or h <= 0: return
            
            # 1. Update Layout
            # We do NOT set central_widget.max_size as it crashes (widget is frozen)
            # self.canvas.central_widget.max_size = (w, h)
            
            # 2. Position Gizmo Overlay (Top-Right)
            gizmo_size = 150
            padding = 0
            
            # Set pos/size of the ViewBox widget directly
            self.gizmo_view.pos = (w - gizmo_size - padding, h - gizmo_size - padding)
            self.gizmo_view.size = (gizmo_size, gizmo_size)
        except Exception as e:
            # Swallow resize errors during docking transitions
            pass

    def on_draw(self, event):
        """Sync gizmo camera rotation with main camera"""
        try:
            if hasattr(self.view.camera, 'azimuth'):
                # Directly copy rotation parameters
                self.gizmo_view.camera.azimuth = self.view.camera.azimuth
                self.gizmo_view.camera.elevation = self.view.camera.elevation
                self.gizmo_view.camera.roll = self.view.camera.roll
        except:
            pass

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

    def get_world_position(self, canvas_pos):
        """Convert canvas position to Mesh Local position on Y=0 plane"""
        try:
            # 1. Get Transform from Canvas (pixels) DIRECTLY to Mesh Local Space
            # This accounts for camera, scaling, offsets, everything.
            transform = self.mesh.get_transform(map_from='canvas', map_to='visual')
            
            x, y = canvas_pos
            
            # 2. Map screen points to Near/Far in Mesh Space
            # Canvas is 2D, but we map to 3D.
            # Usually input is (x, y, z, w) or (x, y, z).
            # We map specific Z depths in the 'canvas' (screen) space... 
            # Actually, standard way is mapping a Ray.
            
            # Map start (Z=0, Near) and end (Z=1, Far) from Canvas Clip?
            # get_transform('canvas', ...) handles the unprojection if usage is correct.
            # Canvas coordinates [x, y] correspond to a ray.
            # 'canvas' system usually treats Z as depth [0, 1] or [-1, 1].
            
            p1 = transform.map([x, y, 0])
            p2 = transform.map([x, y, 1])
            
            # Convert to numpy and handle homogeneous
            p1 = np.array(p1)
            p2 = np.array(p2)
            
            if p1.shape[0] == 4: p1 = p1[:3] / p1[3]
            if p2.shape[0] == 4: p2 = p2[:3] / p2[3]
            
            # print(f"DEBUG: Canvas=({x}, {y})")
            # print(f"DEBUG: P1 (Mesh Local)={p1}")
            # print(f"DEBUG: P2 (Mesh Local)={p2}")

            # 4. Ray Intersection with Plane Y=0 (Mesh Local)
            vec = p2 - p1
            
            if abs(vec[1]) > 1e-6:
                t = -p1[1] / vec[1]
                intersection = p1 + t * vec
                
                # Verify bounds? (Optional, paint handles it)
                # print(f"DEBUG: Intersection={intersection}")
                return intersection
                 
        except Exception as e:
            # print(f"DEBUG: Raycast Error: {e}")
            pass
        return None

    def on_mouse_move(self, event):
        """Handle panning and brush cursor"""
        
        # 0. Always update brush cursor if not panning/rotating
        if not self.is_rotating_light and not self.is_panning:
             # Only update if visible
             if self.brush_visible_override:
                 world_pos = self.get_world_position(event.pos)
                 if world_pos is not None:
                     self.update_brush_cursor(world_pos[0], world_pos[2])
                 else:
                     if self.brush_cursor: self.brush_cursor.visible = False
             else:
                 # Ensure hidden if override is False
                 if self.brush_cursor and self.brush_cursor.visible:
                     self.brush_cursor.visible = False
        
        # 1. Painting (Drag)
        if self.is_painting:
             world_pos = self.get_world_position(event.pos)
             if world_pos is not None:
                 if hasattr(self, 'on_paint_callback') and self.on_paint_callback:
                     if self.on_paint_callback(world_pos[0], world_pos[2], self.brush_radius):
                         event.handled = True
                         self.last_pos = event.pos
                         return
             
             # If painting but off-terrain, still consume event to prevent camera spin
             event.handled = True
             return

        # Light Rotation (Alt + Left Drag)
        if self.is_rotating_light:
            if self.last_pos is not None:
                p1 = event.pos
                p2 = self.last_pos
                
                dx = p2[0] - p1[0]
                dy = p2[1] - p1[1] 
                
                # Sensitivity
                angle_speed = 0.01
                
                # Current light dir
                lx, ly, lz = self.light_dir
                
                # Convert to spherical coordinates
                # Radius
                r = np.sqrt(lx**2 + ly**2 + lz**2)
                if r < 1e-6: r = 1.0
                
                # Azimuth (Angle in XZ plane) -> atan2(x, z)
                azimuth = np.arctan2(lx, lz)
                
                # Elevation (Angle from XZ plane) -> asin(y / r)
                # Clip to safe range
                elevation = np.arcsin(np.clip(ly / r, -1.0, 1.0))
                
                # Update angles based on mouse delta
                # Drag Right (dx > 0) -> Increase Azimuth (Rotate Right)
                azimuth += dx * angle_speed
                
                # Drag Down (dy > 0) -> Decrease Elevation (Sun goes down)
                # Drag Up (dy < 0) -> Increase Elevation (Sun goes up)
                elevation -= dy * angle_speed
                
                # Clamp elevation to prevent flipping (keep between -85 and 85 degrees)
                limit = np.radians(85)
                elevation = np.clip(elevation, -limit, limit)
                
                # Convert back to Cartesian
                # y = r * sin(elev)
                # h = r * cos(elev)
                # x = h * sin(azi)
                # z = h * cos(azi)
                
                new_ly = r * np.sin(elevation)
                h = r * np.cos(elevation)
                new_lx = h * np.sin(azimuth)
                new_lz = h * np.cos(azimuth)
                
                self.light_dir = (new_lx, new_ly, new_lz)
                self.shading_filter.light_dir = self.light_dir[:3] 
                self.light_direction_changed.emit(*self.light_dir)
                self.canvas.update()

            self.last_pos = event.pos
            event.handled = True
            return
        
        # Panning Logic (Shift + Left Drag OR Middle Mouse Drag)
        if self.is_panning:
            if self.last_pos is not None:
                # Calculate delta
                p1 = event.pos
                p2 = self.last_pos
                
                # Get viewport size
                w, h = self.canvas.size
                
                # Invert logic: Dragging Left means Pulling world Left -> Camera moves Right
                # p1(curr) < p2(last) -> dx < 0. We want Camera X > 0.
                # So we use (p2 - p1)
                
                dx_pixels = p2[0] - p1[0]
                dy_pixels = p2[1] - p1[1]
                
                # Scale
                scale = self.view.camera.distance * 2.0 / min(w, h)
                
                dx = dx_pixels * scale
                dy = dy_pixels * scale
                
                # We need to move relative to camera azimuth
                azimuth_rad = np.radians(self.view.camera.azimuth)
                
                # Move 'center'
                center = list(self.view.camera.center)
                
                # Right vector
                cx = np.sin(azimuth_rad)
                cz = np.cos(azimuth_rad)
                
                # Forward vector
                fx = -np.cos(azimuth_rad)
                fz = np.sin(azimuth_rad)
                
                center[0] += dx * cx + dy * fx
                center[2] += dx * cz + dy * fz
                
                self.view.camera.center = tuple(center)
                self.canvas.update()
                
            # Update last_pos for next frame
            self.last_pos = event.pos
            event.handled = True
            return

    def on_mouse_release(self, event):
        self.is_painting = False
        self.is_panning = False
        self.is_rotating_light = False
        self.last_pos = None
        
        # Re-enable camera interaction
        self.view.camera.interactive = True

    def on_mouse_press(self, event):
        # Middle mouse button = panning
        if event.button == 3:
            self.is_panning = True
            self.last_pos = None  # Reset to avoid initial jump
            event.handled = True
            return
        
        if event.button == 1:

            # Block Shift+LMB (prevents default Vispy camera interaction moving the view)
            if 'Shift' in event.modifiers:
                event.handled = True
                return

            # Light Rotation (Alt + LMB)
            if 'Alt' in event.modifiers:
                self.is_rotating_light = True
                self.last_pos = event.pos
                event.handled = True
                return

            # Start painting
            self.is_painting = True
            self.last_pos = event.pos
            
            # Get world position
            world_pos = self.get_world_position(event.pos)
            print(f"DEBUG: Mouse Press at {event.pos}, World Pos: {world_pos}")
            
            # Update Brush Cursor (always if not panning/rotating)
            # Update Brush Cursor (always if not panning/rotating)
            if self.brush_visible_override:
                if world_pos is not None:
                    self.brush_position = world_pos
                    self.update_brush_cursor(world_pos[0], world_pos[2])
                else:
                    if self.brush_cursor: self.brush_cursor.visible = False
            
            if self.is_painting:
                if world_pos is not None and hasattr(self, 'on_paint_callback') and self.on_paint_callback:
                    # Check if paint was handled (active drawing mode)
                    handled = self.on_paint_callback(world_pos[0], world_pos[2], self.brush_radius)
                    print(f"DEBUG: on_paint_callback returned {handled}")
                    if handled:
                         self.view.camera.interactive = False # Force disable camera
                         event.handled = True
                         return # Added return here
                    else:
                         # Not in drawing mode, allow camera
                         self.is_painting = False
                else:
                     print("DEBUG: Painting conditions failed")
                     self.is_painting = False
        
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
        """Rebuild the mesh geometry and mask texture"""
        if not self.terrain_data:
            return

        # 1. Update Geometry
        vertices, normals, faces = self.terrain_data.get_vertex_data()
        
        # Cache for geometry
        self._cached_vertices = vertices.astype(np.float32)
        self._cached_faces = faces.astype(np.uint32)
        
        # Generate UV coordinates for TextureFilter
        # Map X/Z from range [-scale/2, scale/2] to [0, 1]
        scale = self.terrain_data.scale if hasattr(self.terrain_data, 'scale') else 1000.0
        
        # x is vertices[:, 0], z is vertices[:, 2] (y is up)
        u = (vertices[:, 0] + scale/2) / scale
        v = (vertices[:, 2] + scale/2) / scale
        # VisPy TextureFilter uses 'texcoords' buffer
        # Shape (N, 2)
        texcoords = np.column_stack([u, v]).astype(np.float32)
        
        # 3. Upload Geometry + UVs. 
        # We assume base color is gray.
        gray = np.array([0.5, 0.5, 0.5, 1.0])
        colors = np.tile(gray, (len(vertices), 1))
        
        # We MUST upload everything once
        self.mesh.set_data(vertices=self._cached_vertices, faces=self._cached_faces, vertex_colors=colors, color=None)
        
        # Attach texcoords separately? set_data doesn't have explicit texcoords arg usually,
        # but Mesh visual might. 
        # Vispy Mesh set_data: vertices, faces, vertex_colors, meshdata...
        # TextureFilter expects 'texcoords' varying. Mesh needs to provide it.
        # mesh_data.get_vertex_data returns it if present.
        # We can pass it to Mesh constructor, but here we update.
        # We need to manually set the texcoords in the underlying mesh data or visual.
        # mesh.mesh_data.set_texcoords(texcoords)? No.
        # mesh._meshdata usually.
        # Best way for visual:
        # visual.shared_program['texcoord'] = texcoords (Attribute)
        # But 'texcoords' name depends on filter. TextureFilter uses 'texcoords'.
        # Let's try explicit attribute setting if set_data fails.
        # Actually set_data(..., texcoords=texcoords) is supported if Visual allows?
        # Standard Mesh visual args: vertices, faces, vertex_colors, vertex_values, color.
        # It does NOT accept texcoords in set_data directly in some versions.
        # We might need to set it via mesh_data.
        
        # Correct way for VisPy Mesh:
        from vispy.geometry import MeshData
        # MeshData doesn't store texcoords unless we subclass or it's a newer version?
        # Standard VisPy MeshData uses vertex_values for attributes?
        # But we are using a Filter which adds a Varying.
        # We need to set the varying on the visual or filter.
        
        # NOTE: set_vertex_texcoords is NOT standard MeshData method.
        # We just set data on mesh.
        self.mesh.set_data(vertices=self._cached_vertices, faces=self._cached_faces, vertex_colors=colors)
        
        self._ensure_mask_filter(texcoords=texcoords)
        self.update_colors() # Updates the Texture
        self.mesh.update()
        
        self.mesh_stats_changed.emit(len(vertices), len(faces))

    def update_colors(self):
        """Update only mask texture"""
        if not hasattr(self, '_last_color_update'):
             self._last_color_update = 0
             
        now = time.time()
        if now - self._last_color_update < 0.05:
             return
        self._last_color_update = now

        self._ensure_mask_filter()

        if self.mask_data is not None:
             t_start = time.time()
             from src.core.backend import to_cpu
             mask_cpu = to_cpu(self.mask_data)
             
             # Convert to Texture (RGBA)
             # Red Overlay:
             # Mask=0 -> White (1,1,1,1) (Multiplies to Gray)
             # Mask=1 -> Red (1,0,0,1) (Multiplies to Dark Red)
             
             # Optimized CPU conversion
             # texture = White
             # G, B = 1.0 - mask
             
             # (H, W) -> (H, W, 4)
             h, w = mask_cpu.shape
             
             # Use float32 texture for simplicity? Or Uint8?
             # Uint8 is 4x smaller bandwidth.
             # R=255, A=255.
             # G, B = (1-mask)*255.
             
             mask_u8 = (mask_cpu * 255).astype(np.uint8)
             inv_mask_u8 = 255 - mask_u8
             
             texture_data = np.full((h, w, 4), 255, dtype=np.uint8)
             texture_data[:, :, 1] = inv_mask_u8 # G
             texture_data[:, :, 2] = inv_mask_u8 # B
             
             # Upload Texture
             # set_data is fast for textures
             # self.mask_texture.set_data(texture_data)
             
             # Upload Texture
             # set_data is fast for textures
             if self.mask_texture is not None:
                 self.mask_texture.set_data(texture_data)
                 
             # Access internal texture from filter
             # VisPy TextureFilter uses 'u_texture' uniform
             # if self.mask_filter and hasattr(self.mask_filter, 'texture'):
             #    self.mask_filter.texture.set_data(texture_data)
             
             t_end = time.time()
             print(f"DEBUG: update_mask_texture took {(t_end-t_start)*1000:.2f}ms")
             
             self.mesh.update()
        else:
             # Reset to white if no mask
             # 1x1 white texture (255, 255, 255, 255)
             # We check if it's already 2x2 to avoid redundant updates
             # But self.mask_texture might be large from previous mask.
             # So we always reset if it's not the default size, or just force it.
             # Creating a small buffer is cheap.
             if self.mask_texture is not None:
                 # Check if we need to resize/reset
                 # We can just set a small 2x2 white texture.
                 # Note: gloo.Texture2D.set_data might error if size changes?
                 # No, set_data updates subregion if args provided, or whole if not.
                 # But if shape changes, we might need to resize.
                 # resize() exists on Texture2D.
                 
                 # Simplest: Update with 1x1 white pixel if we can't resize easily?
                 # Shaders use UVs. 1x1 white texture covers everything if UVs are 0..1.
                 
                 # Let's try resizing to 2x2 and setting white.
                 data = np.full((2, 2, 4), 255, dtype=np.uint8)
                 try:
                     self.mask_texture.set_data(data) # This might fail if size mismatch
                 except:
                     # If set_data fails due to size, we might need to resize first or Create new?
                     # Re-creating might break the filter binding?
                     # Wrapper 'Texture2D' might handle it?
                     # Native gloo texture: .resize(shape)
                     self.mask_texture.resize((2, 2, 4))
                     self.mask_texture.set_data(data)
                 
                 self.mesh.update()
        
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
