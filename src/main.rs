mod app;
mod ui;
mod rendering;
mod terrain;

use app::TerranoApp;
use env_logger;

fn main() -> Result<(), eframe::Error> {
    // Initialize logger
    env_logger::init();
    
    log::info!("Starting Terrano v0.1.0");
    
    // Configure native window options
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_inner_size([1280.0, 720.0])
            .with_title("Terrano - Terrain Generation Software"),
        ..Default::default()
    };
    
    // Run the application
    eframe::run_native(
        "Terrano",
        options,
        Box::new(|cc| Ok(Box::new(TerranoApp::new(cc)))),
    )
}
