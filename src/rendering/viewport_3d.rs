use crate::rendering::RenderState;
use std::sync::Arc;

/// Custom viewport widget that renders 3D terrain with depth buffer
pub struct Viewport3D {
    render_state: Arc<parking_lot::Mutex<RenderState>>,
}

impl Viewport3D {
    pub fn new(render_state: Arc<parking_lot::Mutex<RenderState>>) -> Self {
        Self { render_state }
    }
    
    pub fn ui(&mut self, ui: &mut egui::Ui) -> egui::Response {
        // Allocate space for the viewport
        let (rect, response) = ui.allocate_exact_size(
            ui.available_size(),
            egui::Sense::click_and_drag(),
        );
        
        // Update camera aspect ratio and resize depth texture
        let mut state = self.render_state.lock();
        let aspect = rect.width() / rect.height();
        state.update_camera(aspect);
        
        let width = rect.width() as u32;
        let height = rect.height() as u32;
        if width > 0 && height > 0 {
            state.resize_depth_texture(width, height);
        }
        drop(state);
        
        // Use egui's wgpu callback for rendering
        let render_state_clone = self.render_state.clone();
        let callback = egui_wgpu::Callback::new_paint_callback(
            rect,
            ViewportCallback { render_state: render_state_clone },
        );
        
        ui.painter().add(callback);
        
        response
    }
}

struct ViewportCallback {
    render_state: Arc<parking_lot::Mutex<RenderState>>,
}

impl egui_wgpu::CallbackTrait for ViewportCallback {
    fn prepare(
        &self,
        device: &wgpu::Device,
        queue: &wgpu::Queue,
        _screen_descriptor: &egui_wgpu::ScreenDescriptor,
        _egui_encoder: &mut wgpu::CommandEncoder,
        _callback_resources: &mut egui_wgpu::CallbackResources,
    ) -> Vec<wgpu::CommandBuffer> {
        // Create our own command encoder for custom rendering
        let mut encoder = device.create_command_encoder(&wgpu::CommandEncoderDescriptor {
            label: Some("Viewport Encoder"),
        });
        
        let state = self.render_state.lock();
        
        // Create a temporary texture for rendering
        let texture = device.create_texture(&wgpu::TextureDescriptor {
            label: Some("Viewport Texture"),
            size: wgpu::Extent3d {
                width: state.depth_texture.width(),
                height: state.depth_texture.height(),
                depth_or_array_layers: 1,
            },
            mip_level_count: 1,
            sample_count: 1,
            dimension: wgpu::TextureDimension::D2,
            format: state.target_format, // Use the same format as the pipeline
            usage: wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::TEXTURE_BINDING,
            view_formats: &[],
        });
        
        let view = texture.create_view(&wgpu::TextureViewDescriptor::default());
        
        // Render with depth buffer
        {
            let mut render_pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: Some("Viewport Render Pass"),
                color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                    view: &view,
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
                depth_stencil_attachment: Some(wgpu::RenderPassDepthStencilAttachment {
                    view: &state.depth_view,
                    depth_ops: Some(wgpu::Operations {
                        load: wgpu::LoadOp::Clear(1.0),
                        store: wgpu::StoreOp::Store,
                    }),
                    stencil_ops: None,
                }),
                timestamp_writes: None,
                occlusion_query_set: None,
            });
            
            render_pass.set_pipeline(&state.pipeline);
            render_pass.set_bind_group(0, &state.uniform_bind_group, &[]);
            render_pass.set_vertex_buffer(0, state.vertex_buffer.slice(..));
            render_pass.set_index_buffer(state.index_buffer.slice(..), wgpu::IndexFormat::Uint32);
            render_pass.draw_indexed(0..state.num_indices, 0, 0..1);
        }
        
        vec![encoder.finish()]
    }

    fn paint(
        &self,
        _info: egui::PaintCallbackInfo,
        _render_pass: &mut wgpu::RenderPass<'static>,
        _callback_resources: &egui_wgpu::CallbackResources,
    ) {
        // Rendering is done in prepare()
    }
}
