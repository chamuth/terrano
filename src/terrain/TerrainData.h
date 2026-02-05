#pragma once

#include "Heightmap.h"
#include <memory>

namespace terrano {

class TerrainData {
public:
    TerrainData();
    ~TerrainData();
    
    Heightmap* getHeightmap() { return heightmap.get(); }
    const Heightmap* getHeightmap() const { return heightmap.get(); }
    
    void createHeightmap(int width, int height);
    
private:
    std::unique_ptr<Heightmap> heightmap;
};

} // namespace terrano
