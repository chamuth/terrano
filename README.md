# Terrano - Terrain Generation Software (Rust)

A professional terrain generation and procedural asset development tool for BeamNG.drive game mods, built with Rust.

## Features

- **2D Heightmap Workflow**: Procedural noise generation, advanced erosion simulation, biome painting
- **3D Terrain Editing**: Full 3D mesh manipulation without heightmap limitations
- **Real-time Preview**: Interactive 3D viewport with playable walk mode
- **BeamNG.drive Export**: Direct export to BeamNG.drive compatible formats

## Why Rust?

- **Memory Safety**: No null pointer crashes or memory leaks
- **Performance**: Equal to C++ performance
- **Modern**: Great tooling, package manager (Cargo), and ecosystem
- **Concurrency**: Safe multi-threading with fearless concurrency

## Technology Stack

- **Language**: Rust 2021 edition
- **UI**: egui (immediate mode GUI)
- **Graphics**: wgpu (modern, cross-platform GPU API)
- **Math**: glam + nalgebra
- **Noise**: noise-rs
- **Build**: Cargo

## Quick Start

### Prerequisites

1. **Rust** (1.70+)
   ```powershell
   # Install rustup (Rust installer)
   # Download from: https://rustup.rs/
   # Or use:
   winget install Rustlang.Rustup
   ```

2. **Visual Studio C++ Build Tools** (for Windows)
   - Download from: https://visualstudio.microsoft.com/downloads/
   - Select "Desktop development with C++"
   - Or minimal: `winget install Microsoft.VisualStudio.2022.BuildTools`

### Build and Run

```powershell
# Clone or navigate to project
cd C:\Users\chamu\Projects\terrano

# Build (first time will download dependencies)
cargo build

# Run in debug mode
cargo run

# Run in release mode (optimized)
cargo run --release

# Run tests
cargo test

# Check code without building
cargo check
```

## Project Structure

```
terrano/
├── Cargo.toml              # Rust dependencies and config
├── Cargo.lock              # Dependency lock file
├── src/
│   ├── main.rs             # Application entry point
│   ├── app.rs              # Main application struct
│   ├── ui/
│   │   ├── mod.rs          # UI module
│   │   ├── main_window.rs  # Main window layout
│   │   └── viewport.rs     # 3D viewport panel
│   ├── rendering/
│   │   ├── mod.rs          # Rendering module
│   │   ├── camera.rs       # Camera controller
│   │   ├── renderer.rs     # wgpu renderer
│   │   └── shaders.wgsl    # WGSL shaders
│   ├── terrain/
│   │   ├── mod.rs          # Terrain module
│   │   ├── heightmap.rs    # 2D heightmap
│   │   └── terrain_data.rs # Terrain container
│   ├── generators/
│   │   ├── mod.rs          # Generators module
│   │   └── perlin.rs       # Perlin noise generator
│   ├── filters/
│   │   ├── mod.rs          # Filters module
│   │   └── erosion.rs      # Erosion simulation
│   └── export/
│       ├── mod.rs          # Export module
│       └── beamng.rs       # BeamNG.drive exporter
├── assets/                 # Shaders, icons, presets
├── benches/                # Performance benchmarks
└── tests/                  # Integration tests
```

## Development

```powershell
# Format code
cargo fmt

# Lint code
cargo clippy

# Run with logging
$env:RUST_LOG="debug"; cargo run

# Build documentation
cargo doc --open

# Run benchmarks
cargo bench
```

## Rust Learning Resources

- [The Rust Book](https://doc.rust-lang.org/book/)
- [Rust by Example](https://doc.rust-lang.org/rust-by-example/)
- [egui Documentation](https://docs.rs/egui/)
- [wgpu Tutorial](https://sotrh.github.io/learn-wgpu/)

## Advantages Over C++

✅ **No manual memory management** - Ownership system prevents leaks  
✅ **No null pointer crashes** - Option<T> instead of null  
✅ **No data races** - Compiler prevents concurrent access bugs  
✅ **Better error handling** - Result<T, E> for explicit error handling  
✅ **Modern tooling** - Cargo handles dependencies, building, testing  
✅ **Fast compilation** - Incremental compilation with cargo  

## License

TBD

## Contributing

TBD
