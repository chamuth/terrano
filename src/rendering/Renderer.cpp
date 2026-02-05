#include "Renderer.h"
#include "../utils/Logger.h"

namespace terrano {

Renderer::Renderer()
    : initialized(false)
{
}

Renderer::~Renderer() {
    shutdown();
}

void Renderer::initialize() {
    if (initialized) return;
    
    Logger::info("Renderer initialized");
    initialized = true;
}

void Renderer::shutdown() {
    if (!initialized) return;
    
    Logger::info("Renderer shutdown");
    initialized = false;
}

void Renderer::render() {
    // TODO: Implement rendering
}

} // namespace terrano
