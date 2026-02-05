#pragma once

namespace terrano {

class Application {
public:
    static Application& instance();
    
    void initialize();
    void shutdown();
    
private:
    Application() = default;
    ~Application() = default;
    
    Application(const Application&) = delete;
    Application& operator=(const Application&) = delete;
};

} // namespace terrano
