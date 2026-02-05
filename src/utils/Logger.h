#pragma once

#include <string>
#include <fstream>
#include <iostream>
#include <chrono>
#include <iomanip>
#include <sstream>

namespace terrano {

enum class LogLevel {
    DEBUG,
    INFO,
    WARNING,
    ERROR
};

class Logger {
public:
    static void initialize();
    static void shutdown();
    
    static void debug(const std::string& message);
    static void info(const std::string& message);
    static void warning(const std::string& message);
    static void error(const std::string& message);
    
private:
    static void log(LogLevel level, const std::string& message);
    static std::string getCurrentTimestamp();
    static std::string levelToString(LogLevel level);
    
    static std::ofstream logFile;
    static bool initialized;
};

} // namespace terrano
