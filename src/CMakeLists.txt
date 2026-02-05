# Source files
set(SOURCES
    main.cpp
    core/Application.cpp
    core/Project.cpp
    core/Settings.cpp
    ui/MainWindow.cpp
    ui/ViewportWidget.cpp
    rendering/Renderer.cpp
    rendering/Camera.cpp
    rendering/Shader.cpp
    terrain/TerrainData.cpp
    terrain/Heightmap.cpp
    utils/Logger.cpp
)

# Header files
set(HEADERS
    core/Application.h
    core/Project.h
    core/Settings.h
    ui/MainWindow.h
    ui/ViewportWidget.h
    rendering/Renderer.h
    rendering/Camera.h
    rendering/Shader.h
    terrain/TerrainData.h
    terrain/Heightmap.h
    utils/Logger.h
)

# Create executable
add_executable(Terrano ${SOURCES} ${HEADERS})

# Link libraries
target_link_libraries(Terrano
    Qt6::Core
    Qt6::Widgets
    Qt6::OpenGLWidgets
    OpenGL::GL
    glm::glm
    glfw
    nlohmann_json::nlohmann_json
    Eigen3::Eigen
    assimp::assimp
)

# Set output directory
set_target_properties(Terrano PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin
)

# Copy Qt DLLs on Windows
if(WIN32)
    add_custom_command(TARGET Terrano POST_BUILD
        COMMAND ${CMAKE_COMMAND} -E copy_if_different
        $<TARGET_FILE:Qt6::Core>
        $<TARGET_FILE:Qt6::Widgets>
        $<TARGET_FILE:Qt6::OpenGLWidgets>
        $<TARGET_FILE_DIR:Terrano>
    )
endif()
