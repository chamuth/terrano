#include <QApplication>
#include "core/Application.h"
#include "ui/MainWindow.h"
#include "utils/Logger.h"

int main(int argc, char *argv[])
{
    // Initialize Qt application
    QApplication app(argc, argv);
    app.setApplicationName("Terrano");
    app.setApplicationVersion("0.1.0");
    app.setOrganizationName("Terrano");
    
    // Initialize logger
    terrano::Logger::initialize();
    terrano::Logger::info("Starting Terrano v0.1.0");
    
    // Create and show main window
    terrano::MainWindow mainWindow;
    mainWindow.show();
    
    terrano::Logger::info("Application initialized successfully");
    
    // Run application event loop
    return app.exec();
}
