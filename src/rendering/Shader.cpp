#include "Shader.h"
#include "../utils/Logger.h"
#include <fstream>
#include <sstream>
#include <QOpenGLFunctions>
#include <glm/gtc/type_ptr.hpp>

namespace terrano {

Shader::Shader()
    : programId(0)
    , vertexShaderId(0)
    , fragmentShaderId(0)
{
}

Shader::~Shader() {
    QOpenGLFunctions gl;
    if (programId) gl.glDeleteProgram(programId);
    if (vertexShaderId) gl.glDeleteShader(vertexShaderId);
    if (fragmentShaderId) gl.glDeleteShader(fragmentShaderId);
}

bool Shader::loadFromFile(const std::string& vertexPath, const std::string& fragmentPath) {
    // Read vertex shader
    std::ifstream vFile(vertexPath);
    if (!vFile.is_open()) {
        Logger::error("Failed to open vertex shader: " + vertexPath);
        return false;
    }
    std::stringstream vStream;
    vStream << vFile.rdbuf();
    std::string vertexSource = vStream.str();
    
    // Read fragment shader
    std::ifstream fFile(fragmentPath);
    if (!fFile.is_open()) {
        Logger::error("Failed to open fragment shader: " + fragmentPath);
        return false;
    }
    std::stringstream fStream;
    fStream << fFile.rdbuf();
    std::string fragmentSource = fStream.str();
    
    return loadFromSource(vertexSource, fragmentSource);
}

bool Shader::loadFromSource(const std::string& vertexSource, const std::string& fragmentSource) {
    QOpenGLFunctions gl;
    gl.initializeOpenGLFunctions();
    
    // Compile shaders
    if (!compileShader(vertexShaderId, vertexSource, GL_VERTEX_SHADER)) {
        return false;
    }
    
    if (!compileShader(fragmentShaderId, fragmentSource, GL_FRAGMENT_SHADER)) {
        return false;
    }
    
    // Link program
    if (!linkProgram()) {
        return false;
    }
    
    Logger::info("Shader loaded successfully");
    return true;
}

void Shader::use() const {
    QOpenGLFunctions gl;
    gl.initializeOpenGLFunctions();
    gl.glUseProgram(programId);
}

void Shader::unuse() const {
    QOpenGLFunctions gl;
    gl.initializeOpenGLFunctions();
    gl.glUseProgram(0);
}

void Shader::setInt(const std::string& name, int value) const {
    QOpenGLFunctions gl;
    gl.initializeOpenGLFunctions();
    gl.glUniform1i(gl.glGetUniformLocation(programId, name.c_str()), value);
}

void Shader::setFloat(const std::string& name, float value) const {
    QOpenGLFunctions gl;
    gl.initializeOpenGLFunctions();
    gl.glUniform1f(gl.glGetUniformLocation(programId, name.c_str()), value);
}

void Shader::setVec3(const std::string& name, const glm::vec3& value) const {
    QOpenGLFunctions gl;
    gl.initializeOpenGLFunctions();
    gl.glUniform3fv(gl.glGetUniformLocation(programId, name.c_str()), 1, glm::value_ptr(value));
}

void Shader::setMat4(const std::string& name, const glm::mat4& value) const {
    QOpenGLFunctions gl;
    gl.initializeOpenGLFunctions();
    gl.glUniformMatrix4fv(gl.glGetUniformLocation(programId, name.c_str()), 1, GL_FALSE, glm::value_ptr(value));
}

bool Shader::compileShader(unsigned int& shader, const std::string& source, int type) {
    QOpenGLFunctions gl;
    gl.initializeOpenGLFunctions();
    
    shader = gl.glCreateShader(type);
    const char* src = source.c_str();
    gl.glShaderSource(shader, 1, &src, nullptr);
    gl.glCompileShader(shader);
    
    // Check compilation
    int success;
    gl.glGetShaderiv(shader, GL_COMPILE_STATUS, &success);
    if (!success) {
        char infoLog[512];
        gl.glGetShaderInfoLog(shader, 512, nullptr, infoLog);
        Logger::error(std::string("Shader compilation failed: ") + infoLog);
        return false;
    }
    
    return true;
}

bool Shader::linkProgram() {
    QOpenGLFunctions gl;
    gl.initializeOpenGLFunctions();
    
    programId = gl.glCreateProgram();
    gl.glAttachShader(programId, vertexShaderId);
    gl.glAttachShader(programId, fragmentShaderId);
    gl.glLinkProgram(programId);
    
    // Check linking
    int success;
    gl.glGetProgramiv(programId, GL_LINK_STATUS, &success);
    if (!success) {
        char infoLog[512];
        gl.glGetProgramInfoLog(programId, 512, nullptr, infoLog);
        Logger::error(std::string("Shader linking failed: ") + infoLog);
        return false;
    }
    
    return true;
}

} // namespace terrano
