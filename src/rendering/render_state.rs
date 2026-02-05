use crate::rendering::Camera;
use std::sync::Arc;
use wgpu::util::DeviceExt;

#[repr(C)]
#[derive(Copy, Clone, Debug, bytemuck::Pod, bytemuck::Zeroable)]
struct Vertex {
    position: [f32; 3],
    color: [f32; 3],
}

impl Vertex {
    fn desc() -> wgpu::VertexBufferLayout<'static> {
        wgpu::VertexBufferLayout {
            array_stride: std::mem::size_of::<Vertex>() as wgpu::BufferAddress,
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

#[repr(C)]
#[derive(Copy, Clone, Debug, bytemuck::Pod, bytemuck::Zeroable)]
struct Uniforms {
    view_proj: [[f32; 4]; 4],
}

pub struct RenderState {
    pub(crate) device: Arc<wgpu::Device>,
    pub(crate) queue: Arc<wgpu::Queue>,
    pub(crate) pipeline: wgpu::RenderPipeline,
    pub(crate) vertex_buffer: wgpu::Buffer,
    pub(crate) index_buffer: wgpu::Buffer,
    pub(crate) num_indices: u32,
    pub(crate) uniform_buffer: wgpu::Buffer,
    pub(crate) uniform_bind_group: wgpu::BindGroup,
    camera: Camera,
}

impl RenderState {
    pub fn new(device: Arc<wgpu::Device>, queue: Arc<wgpu::Queue>, format: wgpu::TextureFormat) -> Self {
        // Create shader module
        let shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("Shader"),
            source: wgpu::ShaderSource::Wgsl(include_str!("shader.wgsl").into()),
        });
        
        // Create uniform buffer
        let camera = Camera::new(1.0);
        let uniforms = Uniforms {
            view_proj: camera.view_projection_matrix().to_cols_array_2d(),
        };
        
        let uniform_buffer = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("Uniform Buffer"),
            contents: bytemuck::cast_slice(&[uniforms]),
            usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
        });
        
        // Create bind group layout
        let bind_group_layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: Some("Bind Group Layout"),
            entries: &[wgpu::BindGroupLayoutEntry {
                binding: 0,
                visibility: wgpu::ShaderStages::VERTEX,
                ty: wgpu::BindingType::Buffer {
                    ty: wgpu::BufferBindingType::Uniform,
                    has_dynamic_offset: false,
                    min_binding_size: None,
                },
                count: None,
            }],
        });
        
        // Create bind group
        let uniform_bind_group = device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("Bind Group"),
            layout: &bind_group_layout,
            entries: &[wgpu::BindGroupEntry {
                binding: 0,
                resource: uniform_buffer.as_entire_binding(),
            }],
        });
        
        // Create pipeline layout
        let pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
            label: Some("Pipeline Layout"),
            bind_group_layouts: &[&bind_group_layout],
            push_constant_ranges: &[],
        });
        
        // Create render pipeline
        let pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("Render Pipeline"),
            layout: Some(&pipeline_layout),
            vertex: wgpu::VertexState {
                module: &shader,
                entry_point: Some("vs_main"),
                buffers: &[Vertex::desc()],
                compilation_options: Default::default(),
            },
            fragment: Some(wgpu::FragmentState {
                module: &shader,
                entry_point: Some("fs_main"),
                targets: &[Some(wgpu::ColorTargetState {
                    format,
                    blend: Some(wgpu::BlendState::REPLACE),
                    write_mask: wgpu::ColorWrites::ALL,
                })],
                compilation_options: Default::default(),
            }),
            primitive: wgpu::PrimitiveState {
                topology: wgpu::PrimitiveTopology::TriangleList,
                strip_index_format: None,
                front_face: wgpu::FrontFace::Ccw,
                cull_mode: Some(wgpu::Face::Back),
                polygon_mode: wgpu::PolygonMode::Fill,
                unclipped_depth: false,
                conservative: false,
            },
            depth_stencil: None,
            multisample: wgpu::MultisampleState {
                count: 1,
                mask: !0,
                alpha_to_coverage_enabled: false,
            },
            multiview: None,
            cache: None,
        });
        
        // Create grid mesh
        let (vertices, indices) = Self::create_grid(10, 10, 1.0);
        
        let vertex_buffer = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("Vertex Buffer"),
            contents: bytemuck::cast_slice(&vertices),
            usage: wgpu::BufferUsages::VERTEX,
        });
        
        let index_buffer = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("Index Buffer"),
            contents: bytemuck::cast_slice(&indices),
            usage: wgpu::BufferUsages::INDEX,
        });
        
        Self {
            device,
            queue,
            pipeline,
            vertex_buffer,
            index_buffer,
            num_indices: indices.len() as u32,
            uniform_buffer,
            uniform_bind_group,
            camera,
        }
    }
    
    fn create_grid(width: u32, height: u32, spacing: f32) -> (Vec<Vertex>, Vec<u16>) {
        let mut vertices = Vec::new();
        let mut indices = Vec::new();
        
        let half_width = (width as f32 * spacing) / 2.0;
        let half_height = (height as f32 * spacing) / 2.0;
        
        // Create grid lines parallel to X axis
        for z in 0..=height {
            let z_pos = z as f32 * spacing - half_height;
            vertices.push(Vertex {
                position: [-half_width, 0.0, z_pos],
                color: [0.3, 0.3, 0.3],
            });
            vertices.push(Vertex {
                position: [half_width, 0.0, z_pos],
                color: [0.3, 0.3, 0.3],
            });
            
            let base = vertices.len() as u16 - 2;
            indices.push(base);
            indices.push(base + 1);
        }
        
        // Create grid lines parallel to Z axis
        for x in 0..=width {
            let x_pos = x as f32 * spacing - half_width;
            vertices.push(Vertex {
                position: [x_pos, 0.0, -half_height],
                color: [0.3, 0.3, 0.3],
            });
            vertices.push(Vertex {
                position: [x_pos, 0.0, half_height],
                color: [0.3, 0.3, 0.3],
            });
            
            let base = vertices.len() as u16 - 2;
            indices.push(base);
            indices.push(base + 1);
        }
        
        (vertices, indices)
    }
    
    pub fn camera_mut(&mut self) -> &mut Camera {
        &mut self.camera
    }
    
    pub fn update_terrain_mesh(&mut self, heightmap: &crate::terrain::Heightmap) {
        use crate::rendering::terrain_mesh::TerrainMesh;
        
        log::info!("Updating terrain mesh");
        
        // Generate mesh from heightmap
        let mesh = TerrainMesh::from_heightmap(heightmap, 0.1);
        
        // Update vertex buffer
        self.vertex_buffer = self.device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("Terrain Vertex Buffer"),
            contents: bytemuck::cast_slice(&mesh.vertices),
            usage: wgpu::BufferUsages::VERTEX,
        });
        
        // Update index buffer
        self.index_buffer = self.device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("Terrain Index Buffer"),
            contents: bytemuck::cast_slice(&mesh.indices),
            usage: wgpu::BufferUsages::INDEX,
        });
        
        self.num_indices = mesh.indices.len() as u32;
        
        log::info!("Terrain mesh updated: {} vertices, {} indices", mesh.vertices.len(), mesh.indices.len());
    }
    
    pub fn update_camera(&mut self, aspect: f32) {
        self.camera.set_aspect(aspect);
        
        let uniforms = Uniforms {
            view_proj: self.camera.view_projection_matrix().to_cols_array_2d(),
        };
        
        self.queue.write_buffer(
            &self.uniform_buffer,
            0,
            bytemuck::cast_slice(&[uniforms]),
        );
    }
    
    pub fn render(&self, encoder: &mut wgpu::CommandEncoder, view: &wgpu::TextureView) {
        let mut render_pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
            label: Some("Render Pass"),
            color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                view,
                resolve_target: None,
                ops: wgpu::Operations {
                    load: wgpu::LoadOp::Clear(wgpu::Color {
                        r: 0.1,
                        g: 0.1,
                        b: 0.1,
                        a: 1.0,
                    }),
                    store: wgpu::StoreOp::Store,
                },
            })],
            depth_stencil_attachment: None,
            timestamp_writes: None,
            occlusion_query_set: None,
        });
        
        render_pass.set_pipeline(&self.pipeline);
        render_pass.set_bind_group(0, &self.uniform_bind_group, &[]);
        render_pass.set_vertex_buffer(0, self.vertex_buffer.slice(..));
        render_pass.set_index_buffer(self.index_buffer.slice(..), wgpu::IndexFormat::Uint16);
        render_pass.draw_indexed(0..self.num_indices, 0, 0..1);
    }
    
    /// Render directly to an existing render pass (for egui callback)
    pub fn render_to_pass<'a>(&'a self, render_pass: &mut wgpu::RenderPass<'a>) {
        render_pass.set_pipeline(&self.pipeline);
        render_pass.set_bind_group(0, &self.uniform_bind_group, &[]);
        render_pass.set_vertex_buffer(0, self.vertex_buffer.slice(..));
        render_pass.set_index_buffer(self.index_buffer.slice(..), wgpu::IndexFormat::Uint16);
        render_pass.draw_indexed(0..self.num_indices, 0, 0..1);
    }
}
