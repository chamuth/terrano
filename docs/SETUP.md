# Development Environment Setup Guide

## Step 1: Install Visual Studio 2022

1. Download Visual Studio 2022 Community Edition from: https://visualstudio.microsoft.com/downloads/
2. Run the installer
3. Select **"Desktop development with C++"** workload
4. In the installation details, ensure these are checked:
   - MSVC v143 - VS 2022 C++ x64/x86 build tools
   - Windows 10/11 SDK
   - C++ CMake tools for Windows
   - C++ ATL for latest build tools
5. Click Install (this may take 30-60 minutes)

## Step 2: Install CMake (if not included with VS)

CMake should be included with Visual Studio's C++ tools. To verify:

```powershell
cmake --version
```

If not found, download from: https://cmake.org/download/
- Choose "Windows x64 Installer"
- During installation, select "Add CMake to system PATH"

## Step 3: Install Qt 6

1. Download Qt Online Installer from: https://www.qt.io/download-qt-installer
2. Create a Qt account (free)
3. Run the installer
4. Select Qt 6.5 or later
5. Under Qt 6.x.x, select:
   - **MSVC 2022 64-bit**
   - Qt 5 Compatibility Module (optional)
   - Additional Libraries (optional)
6. Complete installation

7. Add Qt to your system PATH:
   - Open System Environment Variables
   - Add to PATH: `C:\Qt\6.x.x\msvc2022_64\bin`
   - Replace `6.x.x` with your installed version

## Step 4: Install vcpkg (Dependency Manager)

Open PowerShell as Administrator:

```powershell
# Navigate to C drive
cd C:\

# Clone vcpkg
git clone https://github.com/Microsoft/vcpkg.git

# Navigate to vcpkg directory
cd vcpkg

# Bootstrap vcpkg
.\bootstrap-vcpkg.bat

# Integrate with Visual Studio
.\vcpkg integrate install
```

## Step 5: Install Dependencies via vcpkg

```powershell
# Make sure you're in C:\vcpkg directory
cd C:\vcpkg

# Install required libraries (this may take 20-30 minutes)
.\vcpkg install glm:x64-windows
.\vcpkg install glfw3:x64-windows
.\vcpkg install stb:x64-windows
.\vcpkg install nlohmann-json:x64-windows
.\vcpkg install eigen3:x64-windows
.\vcpkg install assimp:x64-windows
```

## Step 6: Configure Environment Variables

Add these to your system PATH:
1. Qt bin directory: `C:\Qt\6.x.x\msvc2022_64\bin`
2. vcpkg directory: `C:\vcpkg`

## Step 7: Initialize Git Repository

```powershell
cd C:\Users\chamu\Projects\terrano
git init
git add .
git commit -m "Initial project structure"
```

## Step 8: Build the Project

### Option A: Using Visual Studio 2022 (Recommended)

1. Open Visual Studio 2022
2. Click "Open a local folder"
3. Navigate to `C:\Users\chamu\Projects\terrano`
4. Visual Studio will automatically detect CMakeLists.txt
5. Wait for CMake configuration to complete (check Output window)
6. Select "Terrano.exe" as startup item
7. Press F5 to build and run

### Option B: Using Command Line

```powershell
cd C:\Users\chamu\Projects\terrano

# Create build directory
mkdir build
cd build

# Configure CMake with vcpkg toolchain
cmake .. -DCMAKE_TOOLCHAIN_FILE=C:/vcpkg/scripts/buildsystems/vcpkg.cmake -DCMAKE_PREFIX_PATH=C:/Qt/6.x.x/msvc2022_64

# Build (Release mode)
cmake --build . --config Release

# Run
.\bin\Release\Terrano.exe
```

## Troubleshooting

### CMake can't find Qt

Add this to your CMake command:
```powershell
-DCMAKE_PREFIX_PATH=C:/Qt/6.x.x/msvc2022_64
```

### vcpkg packages not found

Make sure you're using the vcpkg toolchain:
```powershell
-DCMAKE_TOOLCHAIN_FILE=C:/vcpkg/scripts/buildsystems/vcpkg.cmake
```

### Missing DLLs when running

Qt DLLs should be copied automatically. If not, manually copy from:
`C:\Qt\6.x.x\msvc2022_64\bin\` to your build output directory.

### OpenGL errors

Make sure your graphics drivers are up to date.

## Next Steps

Once the project builds successfully:
1. Verify the application window opens
2. Check the console for log messages
3. Verify OpenGL context is created
4. Start implementing Phase 1 features from the implementation plan

## Useful Commands

```powershell
# Clean build
cmake --build . --target clean

# Rebuild
cmake --build . --config Release --clean-first

# View CMake cache
cmake -L

# Generate Visual Studio solution (optional)
cmake .. -G "Visual Studio 17 2022" -A x64
```
