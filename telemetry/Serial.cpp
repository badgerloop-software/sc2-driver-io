#include "DTI.h"
#include "../3rdparty/serial/serialib.h"
#include <thread>
#include <atomic>
#include <chrono>
#include <iostream>
#include <vector>
#include <string>
#include <cstring>

class Serial : public DTI {
public:
    Serial(const std::string& SerialDevice) 
        : device_(SerialDevice), running_(false), needs_reconnect_(false) {
        
        // Open serial port using serialib (115200 baud, 8N1)
        char result = serial_.openDevice(device_.c_str(), 115200);
        if (result != 1) {
            std::cerr << "Failed to open serial port: " << device_ << std::endl;
            needs_reconnect_ = true;
        } else {
            std::cout << "Serial port opened successfully: " << device_ << std::endl;
        }
        
        // Start reconnection monitor thread
        running_ = true;
        monitor_thread_ = std::thread(&Serial::monitorConnection, this);
    }

    ~Serial() {
        running_ = false;
        if (monitor_thread_.joinable()) {
            monitor_thread_.join();
        }
        serial_.closeDevice();
    }

    void sendData(const std::vector<uint8_t>& bytes, long long timestamp) override {
        std::cout << "Sending via Serial" << std::endl;
        
        // Add framing tags
        std::vector<uint8_t> framed;
        framed.reserve(bytes.size() + 11);
        
        const char* start = "<bsr>";
        const char* end = "</bsr>";
        framed.insert(framed.end(), start, start + 5);
        framed.insert(framed.end(), bytes.begin(), bytes.end());
        framed.insert(framed.end(), end, end + 6);
        
        // Write to serial port
        int result = serial_.writeBytes(framed.data(), framed.size());
        if (result < 0) {
            std::cerr << "Error occurred sending data via serial" << std::endl;
            needs_reconnect_ = true;
        }
    }

private:
    void monitorConnection() {
        while (running_) {
            if (needs_reconnect_) {
                std::cout << "Serial port disconnected. Reconnecting..." << std::endl;
                serial_.closeDevice();
                std::this_thread::sleep_for(std::chrono::seconds(1));
                
                char result = serial_.openDevice(device_.c_str(), 115200);
                if (result == 1) {
                    std::cout << "Successfully reconnected to serial port" << std::endl;
                    needs_reconnect_ = false;
                } else {
                    std::cerr << "Failed to reconnect to serial port" << std::endl;
                }
            }
            
            // Check connection every 5 seconds
            std::this_thread::sleep_for(std::chrono::seconds(5));
            
            // Check if device is still responding
            if (serial_.isDeviceOpen() && !needs_reconnect_) {
                // Device appears to be open and working
            } else if (!needs_reconnect_) {
                std::cerr << "Serial device closed unexpectedly" << std::endl;
                needs_reconnect_ = true;
            }
        }
    }

    serialib serial_;
    std::string device_;
    std::atomic<bool> running_;
    std::atomic<bool> needs_reconnect_;
    std::thread monitor_thread_;
};
