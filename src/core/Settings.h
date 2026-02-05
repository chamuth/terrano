#pragma once

#include <string>

namespace terrano {

class Settings {
public:
    static Settings& instance();
    
    void load();
    void save();
    
    // Getters/Setters
    int getViewportWidth() const { return viewportWidth; }
    int getViewportHeight() const { return viewportHeight; }
    
private:
    Settings();
    ~Settings() = default;
    
    Settings(const Settings&) = delete;
    Settings& operator=(const Settings&) = delete;
    
    int viewportWidth;
    int viewportHeight;
};

} // namespace terrano
