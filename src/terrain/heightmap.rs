/// 2D heightmap data structure
pub struct Heightmap {
    width: usize,
    height: usize,
    data: Vec<f32>,
}

impl Heightmap {
    /// Create a new heightmap with the given dimensions
    pub fn new(width: usize, height: usize) -> Self {
        log::info!("Creating heightmap: {}x{}", width, height);
        Self {
            width,
            height,
            data: vec![0.0; width * height],
        }
    }
    
    /// Get the width of the heightmap
    pub fn width(&self) -> usize {
        self.width
    }
    
    /// Get the height of the heightmap
    pub fn height(&self) -> usize {
        self.height
    }
    
    /// Get a height value at the given coordinates
    pub fn get(&self, x: usize, y: usize) -> Option<f32> {
        if x >= self.width || y >= self.height {
            return None;
        }
        Some(self.data[y * self.width + x])
    }
    
    /// Set a height value at the given coordinates
    pub fn set(&mut self, x: usize, y: usize, value: f32) -> bool {
        if x >= self.width || y >= self.height {
            return false;
        }
        self.data[y * self.width + x] = value;
        true
    }
    
    /// Get a reference to the raw data
    pub fn data(&self) -> &[f32] {
        &self.data
    }
    
    /// Get a mutable reference to the raw data
    pub fn data_mut(&mut self) -> &mut [f32] {
        &mut self.data
    }
    
    /// Clear the heightmap to a specific value
    pub fn clear(&mut self, value: f32) {
        self.data.fill(value);
    }
    
    /// Resize the heightmap (clears existing data)
    pub fn resize(&mut self, width: usize, height: usize) {
        log::info!("Resizing heightmap: {}x{}", width, height);
        self.width = width;
        self.height = height;
        self.data = vec![0.0; width * height];
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_heightmap_creation() {
        let hm = Heightmap::new(10, 10);
        assert_eq!(hm.width(), 10);
        assert_eq!(hm.height(), 10);
        assert_eq!(hm.data().len(), 100);
    }
    
    #[test]
    fn test_heightmap_get_set() {
        let mut hm = Heightmap::new(10, 10);
        assert!(hm.set(5, 5, 42.0));
        assert_eq!(hm.get(5, 5), Some(42.0));
        assert_eq!(hm.get(100, 100), None);
    }
}
