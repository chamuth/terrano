use crate::rendering::RenderState;
use crate::terrain::{TerrainData, NoiseGenerator};
use std::sync::Arc;

pub struct TerranoApp {
    terrain: TerrainData,
    show_properties: bool,
    show_layers: bool,
    render_state: Option<Arc<parking_lot::Mutex<RenderState>>>,
    
    // Noise generator parameters
    noise_seed: u32,
    noise_scale: f64,
    noise_octaves: usize,
    noise_persistence: f64,
    noise_lacunarity: f64,
}

impl TerranoApp {
    pub fn new(cc: &eframe::CreationContext<'_>) -> Self {
        log::info!("TerranoApp created");
        
        // Initialize wgpu render state
        let render_state = cc.wgpu_render_state.as_ref().map(|rs| {
            let device = rs.device.clone();
            let queue = rs.queue.clone();
            let format = rs.target_format;
            
            Arc::new(parking_lot::Mutex::new(RenderState::new(
                device,
                queue,
                format,
            )))
        });
        
        Self {
            terrain: TerrainData::new(512, 512),
            show_properties: true,
            show_layers: true,
            render_state,
            noise_seed: 42,
            noise_scale: 50.0,
            noise_octaves: 4,
            noise_persistence: 0.5,
            noise_lacunarity: 2.0,
        }
    }
    
    fn generate_terrain(&mut self) {
        log::info!("Generating terrain with seed: {}", self.noise_seed);
        
        let generator = NoiseGenerator::new(self.noise_seed)
            .with_scale(self.noise_scale)
            .with_octaves(self.noise_octaves)
            .with_persistence(self.noise_persistence)
            .with_lacunarity(self.noise_lacunarity);
        
        // Generate heightmap
        let width = self.terrain.width();
        let height = self.terrain.height();
        
        for y in 0..height {
            for x in 0..width {
                let noise_value = generator.generate(x as f64, y as f64);
                // Scale to terrain height range (0 to 100)
                let height_value = (noise_value * 100.0) as f32;
                self.terrain.heightmap_mut().set(x, y, height_value);
            }
        }
        
        log::info!("Terrain generation complete");
    }
}

impl eframe::App for TerranoApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        // Request 60 FPS for smooth rendering
        ctx.request_repaint_after(std::time::Duration::from_millis(16));
        
        // Top menu bar
        egui::TopBottomPanel::top("menu_bar").show(ctx, |ui| {
            egui::menu::bar(ui, |ui| {
                ui.menu_button("File", |ui| {
                    if ui.button("New Project").clicked() {
                        log::info!("New project clicked");
                    }
                    if ui.button("Open Project...").clicked() {
                        log::info!("Open project clicked");
                    }
                    ui.separator();
                    if ui.button("Save Project").clicked() {
                        log::info!("Save project clicked");
                    }
                    if ui.button("Save Project As...").clicked() {
                        log::info!("Save project as clicked");
                    }
                    ui.separator();
                    if ui.button("Exit").clicked() {
                        ctx.send_viewport_cmd(egui::ViewportCommand::Close);
                    }
                });
                
                ui.menu_button("Edit", |ui| {
                    if ui.button("Undo").clicked() {
                        log::info!("Undo clicked");
                    }
                    if ui.button("Redo").clicked() {
                        log::info!("Redo clicked");
                    }
                });
                
                ui.menu_button("View", |ui| {
                    ui.checkbox(&mut self.show_properties, "Properties");
                    ui.checkbox(&mut self.show_layers, "Layers");
                });
                
                ui.menu_button("Help", |ui| {
                    if ui.button("About").clicked() {
                        log::info!("About clicked");
                    }
                });
            });
        });
        
        // Left panel - Layers
        if self.show_layers {
            egui::SidePanel::left("layers_panel")
                .default_width(200.0)
                .show(ctx, |ui| {
                    ui.heading("Layers");
                    ui.separator();
                    ui.label("Layers panel (TODO)");
                });
        }
        
        // Right panel - Properties
        if self.show_properties {
            egui::SidePanel::right("properties_panel")
                .default_width(250.0)
                .show(ctx, |ui| {
                    ui.heading("Properties");
                    ui.separator();
                    
                    ui.label("Terrain Info:");
                    ui.label(format!("Size: {}x{}", 
                        self.terrain.width(), 
                        self.terrain.height()
                    ));
                    
                    ui.separator();
                    ui.heading("Noise Generator");
                    
                    ui.label("Seed:");
                    ui.add(egui::DragValue::new(&mut self.noise_seed).speed(1.0));
                    
                    ui.label("Scale:");
                    ui.add(egui::Slider::new(&mut self.noise_scale, 1.0..=200.0));
                    
                    ui.label("Octaves:");
                    ui.add(egui::Slider::new(&mut self.noise_octaves, 1..=8));
                    
                    ui.label("Persistence:");
                    ui.add(egui::Slider::new(&mut self.noise_persistence, 0.0..=1.0));
                    
                    ui.label("Lacunarity:");
                    ui.add(egui::Slider::new(&mut self.noise_lacunarity, 1.0..=4.0));
                    
                    ui.separator();
                    if ui.button("Generate Terrain").clicked() {
                        self.generate_terrain();
                    }
                    
                    ui.separator();
                    ui.label("Camera Controls:");
                    ui.label("• Middle Mouse: Rotate");
                    ui.label("• Scroll: Zoom");
                });
        }
        
        // Bottom panel - Status bar
        egui::TopBottomPanel::bottom("status_bar").show(ctx, |ui| {
            ui.horizontal(|ui| {
                ui.label("Ready");
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    ui.label(format!("FPS: {:.1}", ctx.input(|i| i.stable_dt.recip())));
                });
            });
        });
        
        // Central panel - 3D Viewport
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("3D Viewport");
            
            // Allocate space for 3D rendering
            let (rect, response) = ui.allocate_exact_size(
                ui.available_size(),
                egui::Sense::click_and_drag(),
            );
            
            // Handle mouse input for camera controls
            if let Some(render_state) = &self.render_state {
                let mut state = render_state.lock();
                
                // Update camera aspect ratio
                let aspect = rect.width() / rect.height();
                state.update_camera(aspect);
                
                // Handle mouse drag for orbit (Unity-style controls)
                if response.dragged_by(egui::PointerButton::Middle) {
                    let delta = response.drag_delta();
                    // Unity-style: negate horizontal, keep vertical as-is
                    state.camera_mut().orbit(
                        -delta.x * 0.01,
                        delta.y * 0.01,
                    );
                }
                
                // Handle scroll for zoom
                let scroll_delta = ui.input(|i| i.smooth_scroll_delta.y);
                if scroll_delta.abs() > 0.0 {
                    state.camera_mut().zoom(scroll_delta * 0.005);
                }
            }
            
            // Render 3D content using wgpu
            if let Some(render_state) = &self.render_state {
                let render_state_clone = render_state.clone();
                
                let callback = egui_wgpu::Callback::new_paint_callback(
                    rect,
                    crate::rendering::Renderer3D::new(render_state_clone),
                );
                
                ui.painter().add(callback);
            } else {
                // Fallback if wgpu is not available
                ui.painter().rect_filled(
                    rect,
                    0.0,
                    egui::Color32::from_rgb(50, 50, 50),
                );
                ui.painter().text(
                    rect.center(),
                    egui::Align2::CENTER_CENTER,
                    "wgpu not available",
                    egui::FontId::proportional(16.0),
                    egui::Color32::WHITE,
                );
            }
        });
    }
}

