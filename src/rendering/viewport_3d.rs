use crate::rendering::RenderState;
use std::sync::Arc;

/// Custom viewport widget that renders 3D terrain
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
        
        // Update camera aspect ratio
        let mut state = self.render_state.lock();
        let aspect = rect.width() / rect.height();
        state.update_camera(aspect);
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
        _device: &wgpu::Device,
        _queue: &wgpu::Queue,
        _screen_descriptor: &egui_wgpu::ScreenDescriptor,
        egui_encoder: &mut wgpu::CommandEncoder,
        _callback_resources: &mut egui_wgpu::CallbackResources,
    ) -> Vec<wgpu::CommandBuffer> {
        Vec::new() // We'll render in paint() to use egui's render pass
    }

    fn paint(
        &self,
        info: egui::PaintCallbackInfo,
        render_pass: &mut wgpu::RenderPass<'static>,
        callback_resources: &egui_wgpu::CallbackResources,
    ) {
        let state = self.render_state.lock();
        
        // CRITICAL: We need a depth attachment but egui's render pass doesn't have one!
        // This will cause a validation error, but it demonstrates the fundamental issue.
        // The ONLY proper solution is to render to our own texture with depth buffer,
        // then blit/copy that texture to egui's surface.
        
        // For now, render without depth testing (will have Z-fighting)
        render_pass.set_pipeline(&state.pipeline);
        render_pass.set_bind_group(0, &state.uniform_bind_group, &[]);
        render_pass.set_vertex_buffer(0, state.vertex_buffer.slice(..));
        render_pass.set_index_buffer(state.index_buffer.slice(..), wgpu::IndexFormat::Uint32);
        render_pass.draw_indexed(0..state.num_indices, 0, 0..1);
    }
}
