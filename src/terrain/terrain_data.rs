use super::Heightmap;

/// Container for all terrain data
pub struct TerrainData {
    heightmap: Heightmap,
}

impl TerrainData {
    /// Create new terrain data with the given dimensions
    pub fn new(width: usize, height: usize) -> Self {
        log::info!("Creating terrain data");
        Self {
            heightmap: Heightmap::new(width, height),
        }
    }
    
    /// Get a reference to the heightmap
    pub fn heightmap(&self) -> &Heightmap {
        &self.heightmap
    }
    
    /// Get a mutable reference to the heightmap
    pub fn heightmap_mut(&mut self) -> &mut Heightmap {
        &mut self.heightmap
    }
    
    /// Get the width of the terrain
    pub fn width(&self) -> usize {
        self.heightmap.width()
    }
    
    /// Get the height of the terrain
    pub fn height(&self) -> usize {
        self.heightmap.height()
    }
}
