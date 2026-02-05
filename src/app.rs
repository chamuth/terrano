use crate::rendering::RenderState;
use crate::terrain::TerrainData;
use std::sync::Arc;

pub struct TerranoApp {
    terrain: TerrainData,
    show_properties: bool,
    show_layers: bool,
    render_state: Option<Arc<parking_lot::Mutex<RenderState>>>,
    last_mouse_pos: Option<egui::Pos2>,
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
            last_mouse_pos: None,
        }
    }
}

impl eframe::App for TerranoApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
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
                    ui.label("Camera Controls:");
                    ui.label("• Middle Mouse: Rotate");
                    ui.label("• Scroll: Zoom");
                    ui.label("• Right Mouse: Pan (TODO)");
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
                
                // Handle mouse drag for orbit
                if response.dragged_by(egui::PointerButton::Middle) {
                    let delta = response.drag_delta();
                    state.camera_mut().orbit(
                        delta.x * 0.01,
                        -delta.y * 0.01,
                    );
                }
                
                // Handle scroll for zoom
                let scroll_delta = ui.input(|i| i.smooth_scroll_delta.y);
                if scroll_delta.abs() > 0.0 {
                    state.camera_mut().zoom(scroll_delta * 0.01);
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

