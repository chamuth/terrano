#pragma once

#include <vector>
#include <glm/glm.hpp>

namespace terrano {

class Camera {
public:
    Camera();
    ~Camera();
    
    void setPosition(const glm::vec3& pos);
    void setTarget(const glm::vec3& target);
    void setDistance(float distance);
    void setYaw(float yaw);
    void setPitch(float pitch);
    
    glm::vec3 getPosition() const { return position; }
    glm::mat4 getViewMatrix() const;
    glm::mat4 getProjectionMatrix(float aspect) const;
    
    void orbit(float deltaYaw, float deltaPitch);
    void pan(float deltaX, float deltaY);
    void zoom(float delta);
    
private:
    void updatePosition();
    
    glm::vec3 position;
    glm::vec3 target;
    float distance;
    float yaw;
    float pitch;
    float fov;
    float nearPlane;
    float farPlane;
};

} // namespace terrano
