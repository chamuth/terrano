#pragma once

#include <QOpenGLWidget>
#include <QOpenGLFunctions>
#include <QMouseEvent>
#include <QWheelEvent>

namespace terrano {

class ViewportWidget : public QOpenGLWidget, protected QOpenGLFunctions {
    Q_OBJECT
    
public:
    explicit ViewportWidget(QWidget* parent = nullptr);
    ~ViewportWidget();
    
protected:
    // OpenGL functions
    void initializeGL() override;
    void resizeGL(int w, int h) override;
    void paintGL() override;
    
    // Input handling
    void mousePressEvent(QMouseEvent* event) override;
    void mouseMoveEvent(QMouseEvent* event) override;
    void mouseReleaseEvent(QMouseEvent* event) override;
    void wheelEvent(QWheelEvent* event) override;
    
private:
    // Camera state
    float cameraDistance;
    float cameraYaw;
    float cameraPitch;
    
    // Mouse state
    QPoint lastMousePos;
    bool isRotating;
    bool isPanning;
};

} // namespace terrano
