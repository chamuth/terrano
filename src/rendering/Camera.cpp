#include "Camera.h"
#include <glm/gtc/matrix_transform.hpp>
#include <cmath>

namespace terrano {

Camera::Camera()
    : position(0.0f, 5.0f, 10.0f)
    , target(0.0f, 0.0f, 0.0f)
    , distance(10.0f)
    , yaw(0.0f)
    , pitch(30.0f)
    , fov(45.0f)
    , nearPlane(0.1f)
    , farPlane(1000.0f)
{
    updatePosition();
}

Camera::~Camera() {
}

void Camera::setPosition(const glm::vec3& pos) {
    position = pos;
}

void Camera::setTarget(const glm::vec3& t) {
    target = t;
    updatePosition();
}

void Camera::setDistance(float d) {
    distance = d;
    updatePosition();
}

void Camera::setYaw(float y) {
    yaw = y;
    updatePosition();
}

void Camera::setPitch(float p) {
    pitch = p;
    updatePosition();
}

glm::mat4 Camera::getViewMatrix() const {
    return glm::lookAt(position, target, glm::vec3(0.0f, 1.0f, 0.0f));
}

glm::mat4 Camera::getProjectionMatrix(float aspect) const {
    return glm::perspective(glm::radians(fov), aspect, nearPlane, farPlane);
}

void Camera::orbit(float deltaYaw, float deltaPitch) {
    yaw += deltaYaw;
    pitch += deltaPitch;
    
    // Clamp pitch
    if (pitch > 89.0f) pitch = 89.0f;
    if (pitch < -89.0f) pitch = -89.0f;
    
    updatePosition();
}

void Camera::pan(float deltaX, float deltaY) {
    // TODO: Implement panning
    updatePosition();
}

void Camera::zoom(float delta) {
    distance -= delta;
    
    // Clamp distance
    if (distance < 1.0f) distance = 1.0f;
    if (distance > 100.0f) distance = 100.0f;
    
    updatePosition();
}

void Camera::updatePosition() {
    float yawRad = glm::radians(yaw);
    float pitchRad = glm::radians(pitch);
    
    position.x = target.x + distance * cos(pitchRad) * sin(yawRad);
    position.y = target.y + distance * sin(pitchRad);
    position.z = target.z + distance * cos(pitchRad) * cos(yawRad);
}

} // namespace terrano
