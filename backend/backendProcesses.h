#ifndef BACKENDPROCESSES_H
#define BACKENDPROCESSES_H
#ifdef unix
#undef unix
#endif

#include <vector>
#include <mutex>
#include <atomic>
#include <thread>
#include <functional>
#include <fstream>
#include <string>
#include <cstdint>

#include "backend/telemetrylib/telemetry.h"
#include "backend/telemetrylib/DTI.h"

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
    // Callback types
    using EngDashConnectionCallback = std::function<void(bool state)>;
    using DataReadyCallback = std::function<void()>;

    explicit BackendProcesses(std::vector<uint8_t> &bytes, std::vector<std::string> &names, std::vector<std::string> &types, timestampOffsets timeDataOffsets, std::mutex &mutex, int byteSize);
    ~BackendProcesses();

    // Start and stop the backend processing
    void start();
    void stop();
    
    // Set callbacks for events
    void setEngDashConnectionCallback(EngDashConnectionCallback callback) {
        engDashConnectionCallback = callback;
    }
    void setDataReadyCallback(DataReadyCallback callback) {
        dataReadyCallback = callback;
    }
    
    // Interface methods (replacements for Qt slots)
    void threadProcedure();
    void startThread();
    void comm_status(bool s);

private:
    // Helper methods to notify callbacks
    void notifyEngDashConnection(bool state) {
        if (engDashConnectionCallback) {
            engDashConnectionCallback(state);
        }
    }
    void notifyDataReady() {
        if (dataReadyCallback) {
            dataReadyCallback();
        }
    }

    timestampOffsets tstampOffsets;
    std::vector<uint8_t> &bytes;
    std::atomic<bool> stop_flag = false;
    std::vector<std::string> &names;
    std::vector<std::string> &types;
    std::mutex &mutex;
    int byteSize;
    Telemetry* tel;

    // Threading
    std::thread processingThread;
    
    // Callback functions
    EngDashConnectionCallback engDashConnectionCallback;
    DataReadyCallback dataReadyCallback;

    // path of output directory used for file sync
    std::string basePath;

    // timestamp when the last file sync output was written to disk
    uint8_t last_minute = 0;

    // queued data for file sync
    std::vector<uint8_t> all_bytes_in_minute;
};

#endif // BACKENDPROCESSES_H
