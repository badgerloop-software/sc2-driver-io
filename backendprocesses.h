#ifndef BACKENDPROCESSES_H
#define BACKENDPROCESSES_H
#ifdef unix
#undef unix
#endif

#include <vector>
#include <string>
#include <mutex>
#include <fstream>
#include <atomic>
#include <functional>
#include <cstdint>

#include "telemetry/telemetry.h"
#include "telemetry/DTI.h"
#include "telemetry/tcp.cpp"
#include "telemetry/sql.cpp"
#include "telemetry/udp.cpp"
#include "telemetry/Serial.cpp"

struct timestampOffsets {
    int hr;
    int mn;
    int sc;
    int ms;
    int unix;
};

class BackendProcesses
{
public:
    // Callback types for event notifications
    using ConnectionCallback = std::function<void(bool state)>;
    using DataReadyCallback = std::function<void()>;
    
    explicit BackendProcesses(
        std::vector<uint8_t> &bytes, 
        std::vector<std::string> &names, 
        std::vector<std::string> &types, 
        timestampOffsets timeDataOffsets, 
        std::mutex &mutex, 
        int byteSize);
    
    ~BackendProcesses();
    
    // Public methods (formerly slots)
    void threadProcedure();
    void startThread();
    void comm_status(bool s);
    
    // Set callbacks for events (replacement for signals)
    void setEngDashConnectionCallback(ConnectionCallback callback) {
        engDashConnectionCallback_ = callback;
    }
    
    void setDataReadyCallback(DataReadyCallback callback) {
        dataReadyCallback_ = callback;
    }

private:
    timestampOffsets tstampOffsets;

    std::vector<uint8_t> &bytes;

    std::atomic<bool> stop = false;
    std::vector<std::string> &names;
    std::vector<std::string> &types;

    std::mutex &mutex;

    int byteSize;

    Telemetry* tel;

    // path of output directory used for file sync
    std::string basePath;

    // timestamp when the last file sync output was written to disk
    uint8_t last_minute = 0;

    // queued data for file sync
    std::vector<uint8_t> all_bytes_in_minute;
    
    // Callbacks (replacement for Qt signals)
    ConnectionCallback engDashConnectionCallback_;
    DataReadyCallback dataReadyCallback_;
    
protected:
    // Helper to emit callbacks
    void emitEngDashConnection(bool state) {
        if (engDashConnectionCallback_) {
            engDashConnectionCallback_(state);
        }
    }
    
    void emitDataReady() {
        if (dataReadyCallback_) {
            dataReadyCallback_();
        }
    }
};

#endif // BACKENDPROCESSES_H
