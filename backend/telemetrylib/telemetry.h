#ifndef TELEMETRYLIB_LIBRARY_H
#define TELEMETRYLIB_LIBRARY_H

#include <iostream>
#include <vector>
#include <atomic>
#include <functional>
#include "DTI.h"

/**
 * A library built for handling data telemetry that allows automatic switching
 * between communication methods with modular design for future extension
 */
class Telemetry {
public:
    // Callback type for engineering dashboard connection status
    using EngDashConnectionCallback = std::function<void(bool state)>;
    
    Telemetry();
    /**
     * @param comm Data telemetry objects ranked by priority
     */
    Telemetry(std::vector<DTI*> comm);
    
    /**
     * to send data, as simple as it gets
     * @param data telemetry data buffer
     * @param timestamp the time which the byte array is created
     */
    void sendData(const std::vector<uint8_t>& data, long long timestamp);
    
    /**
     * Set callback for engineering dashboard connection status changes
     */
    void setEngDashConnectionCallback(EngDashConnectionCallback callback) {
        engDashConnectionCallback = callback;
    }
    
protected:
    // Helper method to notify engineering dashboard connection changes
    void notifyEngDashConnection(bool state) {
        if (engDashConnectionCallback) {
            engDashConnectionCallback(state);
        }
    }

private:
    int originalSize = 0;
    int compressedSize = 0;
    std::vector<std::vector<uint8_t>> dataCache;
    std::atomic<int> commChannel = -1;
    std::vector<DTI*> comm;
    EngDashConnectionCallback engDashConnectionCallback;
};
#endif //TELEMETRYLIB_LIBRARY_H
