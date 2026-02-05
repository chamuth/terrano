#include "Application.h"
#include "../utils/Logger.h"

namespace terrano {

Application& Application::instance() {
    static Application instance;
    return instance;
}

void Application::initialize() {
    Logger::info("Application core initialized");
}

void Application::shutdown() {
    Logger::info("Application core shutdown");
}

} // namespace terrano
