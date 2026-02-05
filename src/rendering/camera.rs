use glam::{Mat4, Vec3};

/// 3D camera with orbit controls
pub struct Camera {
    /// Camera position in world space
    position: Vec3,
    /// Target point the camera looks at
    target: Vec3,
    /// Up vector
    up: Vec3,
    /// Distance from target
    distance: f32,
    /// Horizontal rotation (yaw) in radians
    yaw: f32,
    /// Vertical rotation (pitch) in radians
    pitch: f32,
    /// Field of view in degrees
    fov: f32,
    /// Aspect ratio (width / height)
    aspect: f32,
    /// Near clipping plane
    near: f32,
    /// Far clipping plane
    far: f32,
}

impl Camera {
    /// Create a new camera with default settings
    pub fn new(aspect: f32) -> Self {
        let mut camera = Self {
            position: Vec3::new(0.0, 5.0, 10.0),
            target: Vec3::ZERO,
            up: Vec3::Y,
            distance: 10.0,
            yaw: 0.0,
            pitch: 30.0_f32.to_radians(),
            fov: 45.0,
            aspect,
            near: 1.0,  // Increased from 0.1 for better depth precision
            far: 100.0, // Reduced from 1000.0 to improve near/far ratio
        };
        camera.update_position();
        camera
    }
    
    /// Update camera position based on yaw, pitch, and distance
    fn update_position(&mut self) {
        let x = self.distance * self.pitch.cos() * self.yaw.sin();
        let y = self.distance * self.pitch.sin();
        let z = self.distance * self.pitch.cos() * self.yaw.cos();
        
        self.position = self.target + Vec3::new(x, y, z);
    }
    
    /// Orbit the camera (rotate around target)
    pub fn orbit(&mut self, delta_yaw: f32, delta_pitch: f32) {
        self.yaw += delta_yaw;
        self.pitch += delta_pitch;
        
        // Clamp pitch to prevent gimbal lock
        self.pitch = self.pitch.clamp(-89.0_f32.to_radians(), 89.0_f32.to_radians());
        
        self.update_position();
    }
    
    /// Zoom the camera (change distance from target)
    pub fn zoom(&mut self, delta: f32) {
        self.distance -= delta;
        self.distance = self.distance.clamp(1.0, 100.0);
        self.update_position();
    }
    
    /// Pan the camera (move target point)
    pub fn pan(&mut self, delta_x: f32, delta_y: f32) {
        let right = (self.position - self.target).cross(self.up).normalize();
        let up = right.cross(self.position - self.target).normalize();
        
        self.target += right * delta_x + up * delta_y;
        self.update_position();
    }
    
    /// Set aspect ratio (call when window is resized)
    pub fn set_aspect(&mut self, aspect: f32) {
        self.aspect = aspect;
    }
    
    /// Get the view matrix
    pub fn view_matrix(&self) -> Mat4 {
        Mat4::look_at_rh(self.position, self.target, self.up)
    }
    
    /// Get the projection matrix
    pub fn projection_matrix(&self) -> Mat4 {
        Mat4::perspective_rh(
            self.fov.to_radians(),
            self.aspect,
            self.near,
            self.far,
        )
    }
    
    /// Get the combined view-projection matrix
    pub fn view_projection_matrix(&self) -> Mat4 {
        self.projection_matrix() * self.view_matrix()
    }
    
    /// Get camera position
    pub fn position(&self) -> Vec3 {
        self.position
    }
    
    /// Get camera target
    pub fn target(&self) -> Vec3 {
        self.target
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_camera_creation() {
        let camera = Camera::new(16.0 / 9.0);
        assert_eq!(camera.aspect, 16.0 / 9.0);
        assert!(camera.position.length() > 0.0);
    }
    
    #[test]
    fn test_camera_orbit() {
        let mut camera = Camera::new(1.0);
        let initial_pos = camera.position();
        
        camera.orbit(0.1, 0.1);
        
        assert_ne!(camera.position(), initial_pos);
    }
    
    #[test]
    fn test_camera_zoom() {
        let mut camera = Camera::new(1.0);
        let initial_distance = camera.distance;
        
        camera.zoom(1.0);
        
        assert_ne!(camera.distance, initial_distance);
    }
}
