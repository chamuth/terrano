#pragma once

#include <string>
#include <glm/glm.hpp>

namespace terrano {

class Shader {
public:
    Shader();
    ~Shader();
    
    bool loadFromFile(const std::string& vertexPath, const std::string& fragmentPath);
    bool loadFromSource(const std::string& vertexSource, const std::string& fragmentSource);
    
    void use() const;
    void unuse() const;
    
    // Uniform setters
    void setInt(const std::string& name, int value) const;
    void setFloat(const std::string& name, float value) const;
    void setVec3(const std::string& name, const glm::vec3& value) const;
    void setMat4(const std::string& name, const glm::mat4& value) const;
    
    unsigned int getProgramId() const { return programId; }
    
private:
    bool compileShader(unsigned int& shader, const std::string& source, int type);
    bool linkProgram();
    
    unsigned int programId;
    unsigned int vertexShaderId;
    unsigned int fragmentShaderId;
};

} // namespace terrano
