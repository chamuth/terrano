#pragma once

#include <string>

namespace terrano {

class Project {
public:
    Project();
    ~Project();
    
    bool createNew();
    bool load(const std::string& filepath);
    bool save();
    bool saveAs(const std::string& filepath);
    
    bool isModified() const { return modified; }
    const std::string& getFilepath() const { return filepath; }
    
private:
    std::string filepath;
    bool modified;
};

} // namespace terrano
