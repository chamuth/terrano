# Terrano - Terrain Generation Software

A professional terrain generation and procedural asset development tool for BeamNG.drive game mods.

## Features

- **2D Heightmap Workflow**: Procedural noise generation, advanced erosion simulation, biome painting
- **3D Terrain Editing**: Full 3D mesh manipulation without heightmap limitations
- **Real-time Preview**: Interactive 3D viewport with playable walk mode
- **BeamNG.drive Export**: Direct export to BeamNG.drive compatible formats

## Development Environment Setup

### Prerequisites

1. **Visual Studio 2022** (Community Edition or higher)
   - Download from: https://visualstudio.microsoft.com/downloads/
   - During installation, select:
     - "Desktop development with C++"
     - Windows 10/11 SDK
     - CMake tools for Windows

2. **CMake** (3.20 or higher)
   - Download from: https://cmake.org/download/
   - Add to PATH during installation
   - Or install via Visual Studio (included in C++ tools)

3. **Qt 6** (6.5 or higher)
   - Download from: https://www.qt.io/download-qt-installer
   - Install Qt 6.5+ with MSVC 2022 64-bit component
   - Add Qt to PATH: `C:\Qt\6.x.x\msvc2022_64\bin`

4. **Git** (already installed ✓)
   - Version: 2.49.0.windows.1

5. **vcpkg** (for dependency management)
   ```powershell
   cd C:\
   git clone https://github.com/Microsoft/vcpkg.git
   cd vcpkg
   .\bootstrap-vcpkg.bat
   .\vcpkg integrate install
   ```

### Installing Dependencies via vcpkg

```powershell
# Navigate to vcpkg directory
cd C:\vcpkg

# Install required libraries
.\vcpkg install glm:x64-windows
.\vcpkg install glfw3:x64-windows
.\vcpkg install stb:x64-windows
.\vcpkg install nlohmann-json:x64-windows
.\vcpkg install eigen3:x64-windows
.\vcpkg install assimp:x64-windows
```

## Building the Project

### Using Visual Studio 2022

1. Open Visual Studio 2022
2. File → Open → CMake → Select `CMakeLists.txt`
3. Visual Studio will automatically configure CMake
4. Build → Build All (Ctrl+Shift+B)
5. Run → Start Debugging (F5)

### Using Command Line

```powershell
# Create build directory
mkdir build
cd build

# Configure CMake (with vcpkg toolchain)
cmake .. -DCMAKE_TOOLCHAIN_FILE=C:/vcpkg/scripts/buildsystems/vcpkg.cmake

# Build
cmake --build . --config Release

# Run
.\Release\Terrano.exe
```

## Project Structure

```
terrano/
├── src/                    # Source code
│   ├── core/              # Core application logic
│   ├── terrain/           # Terrain data structures
│   ├── generators/        # Procedural generators
│   ├── filters/           # Terrain filters
│   ├── tools/             # Editing tools
│   ├── rendering/         # OpenGL rendering
│   ├── ui/                # Qt UI components
│   ├── export/            # Export functionality
│   └── utils/             # Utilities
├── shaders/               # GLSL shaders
├── resources/             # Icons, presets, templates
├── docs/                  # Documentation
├── CMakeLists.txt         # Root CMake configuration
└── README.md              # This file
```

## Development Roadmap

See [implementation_plan.md](docs/implementation_plan.md) for detailed development phases.

## License

TBD

## Contributing

TBD
