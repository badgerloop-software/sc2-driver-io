//
// Created by Mingcan Li on 2/3/23.
// STUB: Temporarily disabled - needs libcurl implementation for HTTP POST
//

#include "DTI.h"
#include "Config.h"
#include <iostream>
#include <string>
#include <thread>
#include <atomic>
#include <chrono>

// TODO: Implement with libcurl for HTTP POST to LTE server
// For now, this is a stub that compiles but doesn't send data

class SQL : public DTI {
public:
    SQL(const std::string& tableToCreate) 
        : tableToCreate_(tableToCreate), finish_(false) {
        
        std::cout << "SQL/LTE transmission initialized (STUB - not functional)" << std::endl;
        std::cout << "  Requested table: " << tableToCreate << std::endl;
        std::cout << "  TODO: Implement libcurl HTTP POST" << std::endl;
        
        lastRetry_ = std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count();
    }

    ~SQL() {
        finish_ = true;
    }

    void sendData(const std::vector<uint8_t>& bytes, long long timestamp) override {
        // STUB: Just log that we would send data
        std::cout << "SQL: Would send " << bytes.size() << " bytes at timestamp " 
                  << timestamp << " (not implemented)" << std::endl;
        
        // TODO: Implement HTTP POST with libcurl
        // 1. Check if table exists (tableName_ not empty)
        // 2. If not, retry table creation
        // 3. POST data to server with framing tags
    }

private:
    std::string serverUrl_;
    long long lastRetry_;
    std::string tableName_;
    std::string tableToCreate_;
    std::atomic<bool> finish_;
    
    // TODO: Add libcurl handle and request implementation
};
