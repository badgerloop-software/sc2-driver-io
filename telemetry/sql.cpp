//
// Created by Mingcan Li on 2/3/23.
// Convex Cloud Database Integration via HTTP API
// Sends parsed telemetry data as JSON key-value pairs
//

#include "DTI.h"
#include "Config.h"
#include <iostream>
#include <string>
#include <thread>
#include <atomic>
#include <chrono>
#include <curl/curl.h>
#include <sstream>
#include <iomanip>
#include <mutex>
#include <queue>
#include "3rdparty/rapidjson/document.h"
#include "3rdparty/rapidjson/filereadstream.h"
#include "3rdparty/rapidjson/stringbuffer.h"
#include "3rdparty/rapidjson/writer.h"

using namespace rapidjson;

namespace {  // Anonymous namespace for internal helpers

// Helper function to read float from bytes (little-endian)
float sqlBytesToFloat(const std::vector<uint8_t>& data, int offset) {
    float value;
    memcpy(&value, &data[offset], sizeof(float));
    return value;
}

// Helper function to read uint8 from bytes
uint8_t sqlBytesToUint8(const std::vector<uint8_t>& data, int offset) {
    return data[offset];
}

// Helper function to read uint16 from bytes (little-endian)
uint16_t sqlBytesToUint16(const std::vector<uint8_t>& data, int offset) {
    return data[offset] | (data[offset + 1] << 8);
}

// Helper function to read bool from bytes
bool sqlBytesToBool(const std::vector<uint8_t>& data, int offset) {
    return data[offset] != 0;
}

// Callback for libcurl to capture response
size_t WriteCallback(void* contents, size_t size, size_t nmemb, std::string* userp) {
    size_t totalSize = size * nmemb;
    userp->append(static_cast<char*>(contents), totalSize);
    return totalSize;
}

}  // namespace


class SQL : public DTI {
public:
    SQL(const std::string& identifier = "telemetry") 
        : identifier_(identifier), running_(true), requestsPending_(0) {
        
        // Load Convex configuration
        Config& config = Config::getInstance();
        convexUrl_ = config.getString("convex_deployment_url", "");
        mutationEndpoint_ = config.getString("convex_mutation_endpoint", "/api/mutation");
        mutationName_ = config.getString("convex_mutation_name", "telemetry:storeTelemetry");
        timeout_ = config.getInt("convex_timeout_ms", 5000);
        retryInterval_ = config.getInt("convex_retry_interval_ms", 3000);
        
        if (convexUrl_.empty()) {
            std::cerr << "ERROR: Convex URL not configured in config.json" << std::endl;
            std::cerr << "Please set 'convex_deployment_url' to your Convex deployment URL" << std::endl;
            return;
        }
        
        // Load format.json to parse the byte array
        if (!loadFormatDefinitions()) {
            std::cerr << "ERROR: Failed to load sc1-data-format/format.json" << std::endl;
            return;
        }
        
        // Initialize libcurl
        curl_global_init(CURL_GLOBAL_DEFAULT);
        
        std::cout << "Convex LTE transmission initialized" << std::endl;
        std::cout << "  Convex URL: " << convexUrl_ << std::endl;
        std::cout << "  Mutation: " << mutationName_ << std::endl;
        std::cout << "  Format fields: " << formatFields_.size() << std::endl;
        
        // Start background worker thread for async sending
        workerThread_ = std::thread(&SQL::workerLoop, this);
    }

    ~SQL() {
        running_ = false;
        if (workerThread_.joinable()) {
            workerThread_.join();
        }
        curl_global_cleanup();
    }

    void sendData(const std::vector<uint8_t>& bytes, long long timestamp) override {
        if (convexUrl_.empty() || formatFields_.empty()) {
            return;  // Not configured
        }
        
        // Queue the data for async sending
        {
            std::lock_guard<std::mutex> lock(queueMutex_);
            dataQueue_.push({bytes, timestamp});
            requestsPending_++;
        }
    }

private:
    struct TelemetryData {
        std::vector<uint8_t> bytes;
        long long timestamp;
    };
    
    struct FormatField {
        std::string name;
        int numBytes;
        std::string dataType;
        int offset;
    };
    
    std::string convexUrl_;
    std::string mutationEndpoint_;
    std::string mutationName_;
    std::string identifier_;
    int timeout_;
    int retryInterval_;
    
    std::atomic<bool> running_;
    std::atomic<int> requestsPending_;
    std::queue<TelemetryData> dataQueue_;
    std::mutex queueMutex_;
    std::thread workerThread_;
    
    std::vector<FormatField> formatFields_;
    
    bool loadFormatDefinitions() {
        FILE* fp = fopen("./sc1-data-format/format.json", "r");
        if (fp == nullptr) {
            fp = fopen("../sc1-data-format/format.json", "r");
        }
        if (fp == nullptr) {
            return false;
        }
        
        char readBuffer[65536];
        FileReadStream is(fp, readBuffer, sizeof(readBuffer));
        
        Document d;
        d.ParseStream(is);
        fclose(fp);
        
        if (d.HasParseError()) {
            return false;
        }
        
        int offset = 0;
        for (Value::ConstMemberIterator itr = d.MemberBegin(); itr != d.MemberEnd(); ++itr) {
            FormatField field;
            field.name = itr->name.GetString();
            
            const Value& arr = itr->value.GetArray();
            field.numBytes = arr[0].GetInt();
            field.dataType = arr[1].GetString();
            field.offset = offset;
            
            formatFields_.push_back(field);
            offset += field.numBytes;
        }
        
        return true;
    }
    
    void workerLoop() {
        while (running_) {
            TelemetryData data;
            bool hasData = false;
            
            // Get next item from queue
            {
                std::lock_guard<std::mutex> lock(queueMutex_);
                if (!dataQueue_.empty()) {
                    data = dataQueue_.front();
                    dataQueue_.pop();
                    hasData = true;
                }
            }
            
            if (hasData) {
                sendToConvex(data.bytes, data.timestamp);
                requestsPending_--;
            } else {
                // Sleep briefly if queue is empty
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
            }
        }
    }
    
    bool sendToConvex(const std::vector<uint8_t>& bytes, long long timestamp) {
        CURL* curl = curl_easy_init();
        if (!curl) {
            std::cerr << "Failed to initialize CURL" << std::endl;
            return false;
        }
        
        // Parse byte array into JSON object
        Document parsedData;
        parsedData.SetObject();
        Document::AllocatorType& allocator = parsedData.GetAllocator();
        
        // Add metadata
        parsedData.AddMember("timestamp", timestamp, allocator);
        parsedData.AddMember("source", Value(identifier_.c_str(), allocator), allocator);
        parsedData.AddMember("receivedAt", 
            std::chrono::duration_cast<std::chrono::milliseconds>(
                std::chrono::system_clock::now().time_since_epoch()).count(), 
            allocator);
        
        // Parse each field according to format
        for (const auto& field : formatFields_) {
            if (field.offset + field.numBytes > bytes.size()) {
                continue; // Skip if out of bounds
            }
            
            Value key(field.name.c_str(), allocator);
            
            if (field.dataType == "float") {
                float value = sqlBytesToFloat(bytes, field.offset);
                parsedData.AddMember(key, value, allocator);
            } else if (field.dataType == "uint8") {
                uint8_t value = sqlBytesToUint8(bytes, field.offset);
                parsedData.AddMember(key, static_cast<unsigned int>(value), allocator);
            } else if (field.dataType == "uint16") {
                uint16_t value = sqlBytesToUint16(bytes, field.offset);
                parsedData.AddMember(key, static_cast<unsigned int>(value), allocator);
            } else if (field.dataType == "bool") {
                bool value = sqlBytesToBool(bytes, field.offset);
                parsedData.AddMember(key, value, allocator);
            }
        }
        
        // Convert to JSON string
        StringBuffer buffer;
        Writer<StringBuffer> writer(buffer);
        parsedData.Accept(writer);
        
        // Build Convex mutation payload
        std::stringstream jsonPayload;
        jsonPayload << "{"
                    << "\"path\":\"" << mutationName_ << "\","
                    << "\"args\":[" << buffer.GetString() << "]"
                    << "}";
        
        std::string payload = jsonPayload.str();
        std::string response;
        
        // Build full URL
        std::string fullUrl = convexUrl_ + mutationEndpoint_;
        
        // Set CURL options
        curl_easy_setopt(curl, CURLOPT_URL, fullUrl.c_str());
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, payload.c_str());
        curl_easy_setopt(curl, CURLOPT_TIMEOUT_MS, timeout_);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
        
        // Set headers
        struct curl_slist* headers = nullptr;
        headers = curl_slist_append(headers, "Content-Type: application/json");
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
        
        // Perform request
        CURLcode res = curl_easy_perform(curl);
        long httpCode = 0;
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &httpCode);
        
        bool success = (res == CURLE_OK && httpCode >= 200 && httpCode < 300);
        
        if (success) {
            std::cout << "Convex: Sent telemetry data (timestamp: " 
                      << timestamp << ") - HTTP " << httpCode << std::endl;
        } else {
            std::cerr << "Convex: Failed to send data - ";
            if (res != CURLE_OK) {
                std::cerr << "CURL error: " << curl_easy_strerror(res) << std::endl;
            } else {
                std::cerr << "HTTP " << httpCode << " - " << response << std::endl;
            }
        }
        
        // Cleanup
        curl_slist_free_all(headers);
        curl_easy_cleanup(curl);
        
        return success;
    }
};
