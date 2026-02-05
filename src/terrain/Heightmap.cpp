#include "Heightmap.h"
#include "../utils/Logger.h"
#include <algorithm>

namespace terrano {

Heightmap::Heightmap(int width, int height)
    : width(width)
    , height(height)
{
    data.resize(width * height, 0.0f);
    Logger::info("Heightmap created: " + std::to_string(width) + "x" + std::to_string(height));
}

Heightmap::~Heightmap() {
}

void Heightmap::resize(int w, int h) {
    width = w;
    height = h;
    data.resize(width * height, 0.0f);
    Logger::info("Heightmap resized: " + std::to_string(width) + "x" + std::to_string(height));
}

void Heightmap::clear(float value) {
    std::fill(data.begin(), data.end(), value);
}

float Heightmap::get(int x, int y) const {
    if (x < 0 || x >= width || y < 0 || y >= height) {
        return 0.0f;
    }
    return data[y * width + x];
}

void Heightmap::set(int x, int y, float value) {
    if (x < 0 || x >= width || y < 0 || y >= height) {
        return;
    }
    data[y * width + x] = value;
}

} // namespace terrano
