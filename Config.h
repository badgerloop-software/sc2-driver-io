#ifndef CONFIG_H
#define CONFIG_H

#include <string>
#include <map>
#include "3rdparty/rapidjson/document.h"

class Config {
public:
    static Config& getInstance();
    
    // Get configuration value by key
    std::string getString(const std::string& key, const std::string& defaultValue = "") const;
    int getInt(const std::string& key, int defaultValue = 0) const;
    double getDouble(const std::string& key, double defaultValue = 0.0) const;
    bool getBool(const std::string& key, bool defaultValue = false) const;
    
    // Get raw JSON document for complex queries
    const rapidjson::Document& getDocument() const { return configDoc; }

private:
    rapidjson::Document configDoc;
    
    Config();
    
    void readConfigFile(const std::string& filePath);
    
    // Singleton pattern - delete copy/assignment
    Config(const Config&) = delete;
    void operator=(const Config&) = delete;
};

#endif // CONFIG_H
