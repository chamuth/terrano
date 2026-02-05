use crate::terrain::TerrainData;

pub struct TerranoApp {
    terrain: TerrainData,
    show_properties: bool,
    show_layers: bool,
}

impl TerranoApp {
    pub fn new(_cc: &eframe::CreationContext<'_>) -> Self {
        log::info!("TerranoApp created");
        
        Self {
            terrain: TerrainData::new(512, 512),
            show_properties: true,
            show_layers: true,
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
                    ui.label("Properties panel (TODO)");
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
        
        // Central panel - Viewport
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("3D Viewport");
            
            // Placeholder for 3D rendering
            let (rect, _response) = ui.allocate_exact_size(
                ui.available_size(),
                egui::Sense::click_and_drag(),
            );
            
            ui.painter().rect_filled(
                rect,
                0.0,
                egui::Color32::from_rgb(50, 50, 50),
            );
            
            ui.painter().text(
                rect.center(),
                egui::Align2::CENTER_CENTER,
                "3D Viewport (wgpu integration coming next)",
                egui::FontId::proportional(16.0),
                egui::Color32::WHITE,
            );
        });
    }
}
