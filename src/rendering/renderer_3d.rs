use crate::rendering::RenderState;
use std::sync::Arc;

pub struct Renderer3D {
    render_state: Arc<parking_lot::Mutex<RenderState>>,
}

impl Renderer3D {
    pub fn new(render_state: Arc<parking_lot::Mutex<RenderState>>) -> Self {
        Self { render_state }
    }
}

impl egui_wgpu::CallbackTrait for Renderer3D {
    fn prepare(
        &self,
        _device: &wgpu::Device,
        _queue: &wgpu::Queue,
        _screen_descriptor: &egui_wgpu::ScreenDescriptor,
        _egui_encoder: &mut wgpu::CommandEncoder,
        _callback_resources: &mut egui_wgpu::CallbackResources,
    ) -> Vec<wgpu::CommandBuffer> {
        // No preparation needed
        Vec::new()
    }

    fn paint(
        &self,
        _info: egui::PaintCallbackInfo,
        render_pass: &mut wgpu::RenderPass<'static>,
        _callback_resources: &egui_wgpu::CallbackResources,
    ) {
        // Lock the render state and render
        // The lock guard must live for the entire paint call
        let state = self.render_state.lock();
        
        // Set pipeline and render
        render_pass.set_pipeline(&state.pipeline);
        render_pass.set_bind_group(0, &state.uniform_bind_group, &[]);
        render_pass.set_vertex_buffer(0, state.vertex_buffer.slice(..));
        render_pass.set_index_buffer(state.index_buffer.slice(..), wgpu::IndexFormat::Uint32);
        render_pass.draw_indexed(0..state.num_indices, 0, 0..1);
    }
}

