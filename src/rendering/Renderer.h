#pragma once

namespace terrano {

class Renderer {
public:
    Renderer();
    ~Renderer();
    
    void initialize();
    void shutdown();
    void render();
    
private:
    bool initialized;
};

} // namespace terrano
