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

    void threadProcedure();
    void startThread();
    void comm_status(bool s);

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

    std::string basePath;

    uint8_t last_minute = 0;

    std::vector<uint8_t> all_bytes_in_minute;

    ConnectionCallback engDashConnectionCallback_;
    DataReadyCallback dataReadyCallback_;

protected:
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
