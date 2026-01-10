#include "Config.h"
#include "3rdparty/rapidjson/filereadstream.h"
#include "3rdparty/rapidjson/error/en.h"
#include <iostream>
#include <cstdio>

using namespace rapidjson;

// Singleton: Return the single instance of the Config class
Config& Config::getInstance() {
    static Config instance;
    return instance;
}

Config::Config() {
    // Try different possible locations for config.json
    const char* paths[] = {
        "config.json",
        "../config.json",
        "./config.json"
    };
    
    for (const char* path : paths) {
        FILE* fp = fopen(path, "r");
        if (fp) {
            readConfigFile(path);
            fclose(fp);
            return;
        }
    }
    
    std::cerr << "WARNING: Could not find config.json in any standard location" << std::endl;
}

void Config::readConfigFile(const std::string& filePath) {
    FILE* fp = fopen(filePath.c_str(), "r");
    if (!fp) {
        std::cerr << "Could not open config file: " << filePath << std::endl;
        return;
    }
    
    char readBuffer[65536];
    FileReadStream is(fp, readBuffer, sizeof(readBuffer));
    
    configDoc.ParseStream(is);
    fclose(fp);
    
    if (configDoc.HasParseError()) {
        std::cerr << "JSON parse error in config file: " 
                  << GetParseError_En(configDoc.GetParseError())
                  << " at offset " << configDoc.GetErrorOffset() << std::endl;
    } else {
        std::cout << "Configuration loaded successfully from: " << filePath << std::endl;
    }
}

std::string Config::getString(const std::string& key, const std::string& defaultValue) const {
    if (configDoc.HasMember(key.c_str()) && configDoc[key.c_str()].IsString()) {
        return configDoc[key.c_str()].GetString();
    }
    return defaultValue;
}

int Config::getInt(const std::string& key, int defaultValue) const {
    if (configDoc.HasMember(key.c_str()) && configDoc[key.c_str()].IsInt()) {
        return configDoc[key.c_str()].GetInt();
    }
    return defaultValue;
}

double Config::getDouble(const std::string& key, double defaultValue) const {
    if (configDoc.HasMember(key.c_str())) {
        if (configDoc[key.c_str()].IsDouble()) {
            return configDoc[key.c_str()].GetDouble();
        } else if (configDoc[key.c_str()].IsInt()) {
            return static_cast<double>(configDoc[key.c_str()].GetInt());
        }
    }
    return defaultValue;
}

bool Config::getBool(const std::string& key, bool defaultValue) const {
    if (configDoc.HasMember(key.c_str()) && configDoc[key.c_str()].IsBool()) {
        return configDoc[key.c_str()].GetBool();
    }
    return defaultValue;
}
