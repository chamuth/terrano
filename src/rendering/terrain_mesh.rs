use crate::terrain::Heightmap;
use wgpu::util::DeviceExt;

#[repr(C)]
#[derive(Copy, Clone, Debug, bytemuck::Pod, bytemuck::Zeroable)]
pub struct TerrainVertex {
    pub position: [f32; 3],
    pub color: [f32; 3],
}

impl TerrainVertex {
    pub fn desc() -> wgpu::VertexBufferLayout<'static> {
        wgpu::VertexBufferLayout {
            array_stride: std::mem::size_of::<TerrainVertex>() as wgpu::BufferAddress,
            step_mode: wgpu::VertexStepMode::Vertex,
            attributes: &[
                wgpu::VertexAttribute {
                    offset: 0,
                    shader_location: 0,
                    format: wgpu::VertexFormat::Float32x3,
                },
                wgpu::VertexAttribute {
                    offset: std::mem::size_of::<[f32; 3]>() as wgpu::BufferAddress,
                    shader_location: 1,
                    format: wgpu::VertexFormat::Float32x3,
                },
            ],
        }
    }
}

pub struct TerrainMesh {
    pub vertices: Vec<TerrainVertex>,
    pub indices: Vec<u32>,
}

impl TerrainMesh {
    /// Generate a mesh from a heightmap
    pub fn from_heightmap(heightmap: &Heightmap, scale: f32) -> Self {
        let width = heightmap.width();
        let height = heightmap.height();
        
        let mut vertices = Vec::new();
        let mut indices = Vec::new();
        
        // Generate vertices
        for y in 0..height {
            for x in 0..width {
                let h = heightmap.get(x, y).unwrap_or(0.0);
                
                // Center the terrain
                let pos_x = (x as f32 - width as f32 / 2.0) * scale;
                let pos_y = h * 0.1; // Scale height
                let pos_z = (y as f32 - height as f32 / 2.0) * scale;
                
                // Rainbow color based on height
                let t = (h / 100.0).clamp(0.0, 1.0);
                let color = if t < 0.2 {
                    // Blue to Cyan
                    let local_t = t / 0.2;
                    [0.0, local_t, 1.0]
                } else if t < 0.4 {
                    // Cyan to Green
                    let local_t = (t - 0.2) / 0.2;
                    [0.0, 1.0, 1.0 - local_t]
                } else if t < 0.6 {
                    // Green to Yellow
                    let local_t = (t - 0.4) / 0.2;
                    [local_t, 1.0, 0.0]
                } else if t < 0.8 {
                    // Yellow to Red
                    let local_t = (t - 0.6) / 0.2;
                    [1.0, 1.0 - local_t, 0.0]
                } else {
                    // Red to Magenta
                    let local_t = (t - 0.8) / 0.2;
                    [1.0, 0.0, local_t]
                };
                
                vertices.push(TerrainVertex {
                    position: [pos_x, pos_y, pos_z],
                    color,
                });
            }
        }
        
        // Generate indices for triangles
        for y in 0..(height - 1) {
            for x in 0..(width - 1) {
                let top_left = (y * width + x) as u32;
                let top_right = (y * width + x + 1) as u32;
                let bottom_left = ((y + 1) * width + x) as u32;
                let bottom_right = ((y + 1) * width + x + 1) as u32;
                
                // First triangle
                indices.push(top_left);
                indices.push(bottom_left);
                indices.push(top_right);
                
                // Second triangle
                indices.push(top_right);
                indices.push(bottom_left);
                indices.push(bottom_right);
            }
        }
        
        Self { vertices, indices }
    }
}
