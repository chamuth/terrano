#include "Settings.h"
#include "../utils/Logger.h"

namespace terrano {

Settings::Settings()
    : viewportWidth(1280)
    , viewportHeight(720)
{
}

Settings& Settings::instance() {
    static Settings instance;
    return instance;
}

void Settings::load() {
    Logger::info("Settings loaded");
    // TODO: Load from file
}

void Settings::save() {
    Logger::info("Settings saved");
    // TODO: Save to file
}

} // namespace terrano
