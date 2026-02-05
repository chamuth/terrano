#include "TerrainData.h"
#include "../utils/Logger.h"

namespace terrano {

TerrainData::TerrainData() {
    Logger::info("TerrainData created");
}

TerrainData::~TerrainData() {
    Logger::info("TerrainData destroyed");
}

void TerrainData::createHeightmap(int width, int height) {
    heightmap = std::make_unique<Heightmap>(width, height);
}

} // namespace terrano
