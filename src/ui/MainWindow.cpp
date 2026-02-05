#include "MainWindow.h"
#include "ViewportWidget.h"
#include "../utils/Logger.h"
#include <QMessageBox>
#include <QFileDialog>
#include <QLabel>

namespace terrano {

MainWindow::MainWindow(QWidget* parent)
    : QMainWindow(parent)
{
    setWindowTitle("Terrano - Terrain Generation Software");
    resize(1280, 720);
    
    // Create central viewport
    viewport = new ViewportWidget(this);
    setCentralWidget(viewport);
    
    // Create UI components
    createMenus();
    createToolbars();
    createDockWidgets();
    createStatusBar();
    
    Logger::info("Main window created");
}

MainWindow::~MainWindow() {
    Logger::info("Main window destroyed");
}

void MainWindow::createMenus() {
    // File menu
    fileMenu = menuBar()->addMenu("&File");
    
    QAction* newAction = fileMenu->addAction("&New Project");
    newAction->setShortcut(QKeySequence::New);
    connect(newAction, &QAction::triggered, this, &MainWindow::onNewProject);
    
    QAction* openAction = fileMenu->addAction("&Open Project...");
    openAction->setShortcut(QKeySequence::Open);
    connect(openAction, &QAction::triggered, this, &MainWindow::onOpenProject);
    
    fileMenu->addSeparator();
    
    QAction* saveAction = fileMenu->addAction("&Save Project");
    saveAction->setShortcut(QKeySequence::Save);
    connect(saveAction, &QAction::triggered, this, &MainWindow::onSaveProject);
    
    QAction* saveAsAction = fileMenu->addAction("Save Project &As...");
    saveAsAction->setShortcut(QKeySequence::SaveAs);
    connect(saveAsAction, &QAction::triggered, this, &MainWindow::onSaveProjectAs);
    
    fileMenu->addSeparator();
    
    QAction* exitAction = fileMenu->addAction("E&xit");
    exitAction->setShortcut(QKeySequence::Quit);
    connect(exitAction, &QAction::triggered, this, &MainWindow::onExit);
    
    // Edit menu
    editMenu = menuBar()->addMenu("&Edit");
    
    QAction* undoAction = editMenu->addAction("&Undo");
    undoAction->setShortcut(QKeySequence::Undo);
    undoAction->setEnabled(false);
    
    QAction* redoAction = editMenu->addAction("&Redo");
    redoAction->setShortcut(QKeySequence::Redo);
    redoAction->setEnabled(false);
    
    // View menu
    viewMenu = menuBar()->addMenu("&View");
    
    // Help menu
    helpMenu = menuBar()->addMenu("&Help");
    
    QAction* aboutAction = helpMenu->addAction("&About Terrano");
    connect(aboutAction, &QAction::triggered, this, &MainWindow::onAbout);
}

void MainWindow::createToolbars() {
    mainToolbar = addToolBar("Main Toolbar");
    mainToolbar->setMovable(false);
    
    // Add toolbar actions here
    QAction* newAction = mainToolbar->addAction("New");
    connect(newAction, &QAction::triggered, this, &MainWindow::onNewProject);
    
    QAction* openAction = mainToolbar->addAction("Open");
    connect(openAction, &QAction::triggered, this, &MainWindow::onOpenProject);
    
    QAction* saveAction = mainToolbar->addAction("Save");
    connect(saveAction, &QAction::triggered, this, &MainWindow::onSaveProject);
}

void MainWindow::createDockWidgets() {
    // Properties dock
    propertyDock = new QDockWidget("Properties", this);
    propertyDock->setAllowedAreas(Qt::LeftDockWidgetArea | Qt::RightDockWidgetArea);
    QLabel* propLabel = new QLabel("Properties panel (TODO)", propertyDock);
    propertyDock->setWidget(propLabel);
    addDockWidget(Qt::RightDockWidgetArea, propertyDock);
    
    // Layers dock
    layersDock = new QDockWidget("Layers", this);
    layersDock->setAllowedAreas(Qt::LeftDockWidgetArea | Qt::RightDockWidgetArea);
    QLabel* layersLabel = new QLabel("Layers panel (TODO)", layersDock);
    layersDock->setWidget(layersLabel);
    addDockWidget(Qt::RightDockWidgetArea, layersDock);
    
    // Add dock widget toggles to View menu
    viewMenu->addAction(propertyDock->toggleViewAction());
    viewMenu->addAction(layersDock->toggleViewAction());
}

void MainWindow::createStatusBar() {
    statusBar()->showMessage("Ready");
}

// Slots
void MainWindow::onNewProject() {
    Logger::info("New project requested");
    statusBar()->showMessage("Creating new project...", 2000);
    // TODO: Implement new project logic
}

void MainWindow::onOpenProject() {
    Logger::info("Open project requested");
    QString fileName = QFileDialog::getOpenFileName(
        this,
        "Open Project",
        "",
        "Terrano Projects (*.terrano);;All Files (*)"
    );
    
    if (!fileName.isEmpty()) {
        Logger::info("Opening project: " + fileName.toStdString());
        statusBar()->showMessage("Opening project: " + fileName, 2000);
        // TODO: Implement open project logic
    }
}

void MainWindow::onSaveProject() {
    Logger::info("Save project requested");
    statusBar()->showMessage("Saving project...", 2000);
    // TODO: Implement save project logic
}

void MainWindow::onSaveProjectAs() {
    Logger::info("Save project as requested");
    QString fileName = QFileDialog::getSaveFileName(
        this,
        "Save Project As",
        "",
        "Terrano Projects (*.terrano);;All Files (*)"
    );
    
    if (!fileName.isEmpty()) {
        Logger::info("Saving project as: " + fileName.toStdString());
        statusBar()->showMessage("Saving project as: " + fileName, 2000);
        // TODO: Implement save as logic
    }
}

void MainWindow::onExit() {
    Logger::info("Exit requested");
    close();
}

void MainWindow::onAbout() {
    QMessageBox::about(
        this,
        "About Terrano",
        "<h2>Terrano v0.1.0</h2>"
        "<p>Terrain Generation and Procedural Asset Development Software</p>"
        "<p>Built for BeamNG.drive game mods</p>"
        "<p>Copyright © 2026</p>"
    );
}

} // namespace terrano
