#pragma once

#include <vector>

namespace terrano {

class Heightmap {
public:
    Heightmap(int width = 512, int height = 512);
    ~Heightmap();
    
    void resize(int width, int height);
    void clear(float value = 0.0f);
    
    float get(int x, int y) const;
    void set(int x, int y, float value);
    
    int getWidth() const { return width; }
    int getHeight() const { return height; }
    
    const std::vector<float>& getData() const { return data; }
    std::vector<float>& getData() { return data; }
    
private:
    int width;
    int height;
    std::vector<float> data;
};

} // namespace terrano
