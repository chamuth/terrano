#include "ViewportWidget.h"
#include "../utils/Logger.h"
#include <cmath>

namespace terrano {

ViewportWidget::ViewportWidget(QWidget* parent)
    : QOpenGLWidget(parent)
    , cameraDistance(10.0f)
    , cameraYaw(45.0f)
    , cameraPitch(30.0f)
    , isRotating(false)
    , isPanning(false)
{
    setFocusPolicy(Qt::StrongFocus);
    Logger::info("Viewport widget created");
}

ViewportWidget::~ViewportWidget() {
    Logger::info("Viewport widget destroyed");
}

void ViewportWidget::initializeGL() {
    initializeOpenGLFunctions();
    
    Logger::info("OpenGL initialized");
    Logger::info(std::string("OpenGL Version: ") + 
                 reinterpret_cast<const char*>(glGetString(GL_VERSION)));
    Logger::info(std::string("GLSL Version: ") + 
                 reinterpret_cast<const char*>(glGetString(GL_SHADING_LANGUAGE_VERSION)));
    
    // Set clear color (dark gray)
    glClearColor(0.2f, 0.2f, 0.2f, 1.0f);
    
    // Enable depth testing
    glEnable(GL_DEPTH_TEST);
    glDepthFunc(GL_LESS);
    
    // Enable backface culling
    glEnable(GL_CULL_FACE);
    glCullFace(GL_BACK);
}

void ViewportWidget::resizeGL(int w, int h) {
    glViewport(0, 0, w, h);
}

void ViewportWidget::paintGL() {
    // Clear buffers
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);
    
    // TODO: Render terrain here
    // For now, just clear to background color
}

void ViewportWidget::mousePressEvent(QMouseEvent* event) {
    lastMousePos = event->pos();
    
    if (event->button() == Qt::MiddleButton) {
        isRotating = true;
    } else if (event->button() == Qt::RightButton) {
        isPanning = true;
    }
}

void ViewportWidget::mouseMoveEvent(QMouseEvent* event) {
    QPoint delta = event->pos() - lastMousePos;
    lastMousePos = event->pos();
    
    if (isRotating) {
        // Rotate camera
        cameraYaw += delta.x() * 0.5f;
        cameraPitch += delta.y() * 0.5f;
        
        // Clamp pitch
        if (cameraPitch > 89.0f) cameraPitch = 89.0f;
        if (cameraPitch < -89.0f) cameraPitch = -89.0f;
        
        update();
    } else if (isPanning) {
        // Pan camera (TODO: implement proper panning)
        update();
    }
}

void ViewportWidget::mouseReleaseEvent(QMouseEvent* event) {
    if (event->button() == Qt::MiddleButton) {
        isRotating = false;
    } else if (event->button() == Qt::RightButton) {
        isPanning = false;
    }
}

void ViewportWidget::wheelEvent(QWheelEvent* event) {
    // Zoom camera
    float delta = event->angleDelta().y() / 120.0f;
    cameraDistance -= delta * 0.5f;
    
    // Clamp distance
    if (cameraDistance < 1.0f) cameraDistance = 1.0f;
    if (cameraDistance > 100.0f) cameraDistance = 100.0f;
    
    update();
}

} // namespace terrano
