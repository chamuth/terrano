#include "Project.h"
#include "../utils/Logger.h"

namespace terrano {

Project::Project()
    : modified(false)
{
}

Project::~Project() {
}

bool Project::createNew() {
    filepath.clear();
    modified = false;
    Logger::info("New project created");
    return true;
}

bool Project::load(const std::string& filepath) {
    this->filepath = filepath;
    modified = false;
    Logger::info("Project loaded: " + filepath);
    // TODO: Implement actual loading
    return true;
}

bool Project::save() {
    if (filepath.empty()) {
        Logger::error("Cannot save: no filepath specified");
        return false;
    }
    
    Logger::info("Project saved: " + filepath);
    modified = false;
    // TODO: Implement actual saving
    return true;
}

bool Project::saveAs(const std::string& filepath) {
    this->filepath = filepath;
    return save();
}

} // namespace terrano
