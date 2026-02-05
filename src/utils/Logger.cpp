#include "Logger.h"

namespace terrano {

std::ofstream Logger::logFile;
bool Logger::initialized = false;

void Logger::initialize() {
    if (initialized) return;
    
    logFile.open("terrano.log", std::ios::out | std::ios::app);
    initialized = true;
    
    log(LogLevel::INFO, "Logger initialized");
}

void Logger::shutdown() {
    if (!initialized) return;
    
    log(LogLevel::INFO, "Logger shutdown");
    logFile.close();
    initialized = false;
}

void Logger::debug(const std::string& message) {
    log(LogLevel::DEBUG, message);
}

void Logger::info(const std::string& message) {
    log(LogLevel::INFO, message);
}

void Logger::warning(const std::string& message) {
    log(LogLevel::WARNING, message);
}

void Logger::error(const std::string& message) {
    log(LogLevel::ERROR, message);
}

void Logger::log(LogLevel level, const std::string& message) {
    std::string timestamp = getCurrentTimestamp();
    std::string levelStr = levelToString(level);
    
    std::string logMessage = "[" + timestamp + "] [" + levelStr + "] " + message;
    
    // Console output
    std::cout << logMessage << std::endl;
    
    // File output
    if (initialized && logFile.is_open()) {
        logFile << logMessage << std::endl;
        logFile.flush();
    }
}

std::string Logger::getCurrentTimestamp() {
    auto now = std::chrono::system_clock::now();
    auto time = std::chrono::system_clock::to_time_t(now);
    
    std::stringstream ss;
    ss << std::put_time(std::localtime(&time), "%Y-%m-%d %H:%M:%S");
    return ss.str();
}

std::string Logger::levelToString(LogLevel level) {
    switch (level) {
        case LogLevel::DEBUG:   return "DEBUG";
        case LogLevel::INFO:    return "INFO";
        case LogLevel::WARNING: return "WARNING";
        case LogLevel::ERROR:   return "ERROR";
        default:                return "UNKNOWN";
    }
}

} // namespace terrano
