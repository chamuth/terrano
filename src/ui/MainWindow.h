#pragma once

#include <QMainWindow>
#include <QMenuBar>
#include <QToolBar>
#include <QStatusBar>
#include <QDockWidget>

namespace terrano {

class ViewportWidget;

class MainWindow : public QMainWindow {
    Q_OBJECT
    
public:
    explicit MainWindow(QWidget* parent = nullptr);
    ~MainWindow();
    
private slots:
    void onNewProject();
    void onOpenProject();
    void onSaveProject();
    void onSaveProjectAs();
    void onExit();
    
    void onAbout();
    
private:
    void createMenus();
    void createToolbars();
    void createDockWidgets();
    void createStatusBar();
    
    // UI components
    ViewportWidget* viewport;
    
    // Menus
    QMenu* fileMenu;
    QMenu* editMenu;
    QMenu* viewMenu;
    QMenu* helpMenu;
    
    // Toolbars
    QToolBar* mainToolbar;
    
    // Dock widgets
    QDockWidget* propertyDock;
    QDockWidget* layersDock;
};

} // namespace terrano
