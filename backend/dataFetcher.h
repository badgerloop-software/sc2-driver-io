#ifndef DATAFETCHER_H
#define DATAFETCHER_H

#include <vector>
#include <mutex>
#include <thread>
#include <atomic>
#include <functional>
#include <cstdint>
#include "gps/gps.h"

class DataFetcher
{
public:
    // Callback type for data fetched events
    using DataFetchedCallback = std::function<void()>;

    explicit DataFetcher(std::vector<uint8_t> &bytes, int byteSize, std::mutex &mutex, GPSData gpsOffset);
    ~DataFetcher();

    // Start and stop data fetching
    void start();
    void stop();
    
    // Set callback for data fetched events
    void setDataFetchedCallback(DataFetchedCallback callback) {
        dataFetchedCallback = callback;
    }
    
    // Interface methods (replacements for Qt slots)
    void threadProcedure();
    void startThread();
    void onNewConnection();
    void onReadyRead();
    void onDisconnected();
    void sendData(const std::vector<uint8_t>& data);

private:
    // Helper method to notify data fetched
    void notifyDataFetched() {
        if (dataFetchedCallback) {
            dataFetchedCallback();
        }
    }

    std::vector<uint8_t> &bytes;
    int byteSize;
    std::mutex &mutex;
    std::atomic<bool> connected = false;
    std::atomic<bool> running = false;
    std::thread* thread;

    GPS* gps;
    GPSData gpsOffset;
    std::thread gpsThread;
    
    // Network communication (will need to be replaced with standard socket implementation)
    // QTcpServer* ethServer;  // TODO: Replace with standard socket server
    // QTcpSocket* clientSocket;  // TODO: Replace with standard socket client
    
    // Callback function
    DataFetchedCallback dataFetchedCallback;
};

#endif // DATAFETCHER_H
