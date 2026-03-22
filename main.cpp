#include <iostream>
#include <thread>
#include <chrono>
#include <filesystem>
#include <cstdlib>
#include <signal.h>
#include <DataProcessor/dataUnpacker.h>
#include "InfluxWriter.h"

// Global flag for clean shutdown
volatile bool g_running = true;

// Signal handler for graceful shutdown
void signalHandler(int signal) {
    std::cout << "\nReceived signal " << signal << ". Shutting down gracefully..." << std::endl;
    g_running = false;
}

// Function to start file sync process
void startFileSync() {
    // Check for file_sync/file_sync_up/main.py in different locations
    std::filesystem::path sync_paths[] = {
        "../backend/file_sync/file_sync_up/main.py",
        "./backend/file_sync/file_sync_up/main.py"
    };
    
    for (const auto& path : sync_paths) {
        if (std::filesystem::exists(path) && std::filesystem::is_regular_file(path)) {
            std::cout << "Starting file sync from: " << path << std::endl;
            std::string command = "python3 " + path.string() + " &";
            int result = std::system(command.c_str());
            if (result == 0) {
                std::cout << "File sync started successfully" << std::endl;
                return;
            } else {
                std::cout << "Failed to start file sync process" << std::endl;
            }
        }
    }
    
    std::cout << "\nWARNING: running without file sync" << std::endl;
    std::cout << "   * Check whether you've cloned all the submodules" << std::endl;
    std::cout << "   * If that didn't work, your build output is probably in a nonstandard directory" << std::endl;
}

int main(int argc, char *argv[]) {
    std::cout << "SC2 Driver IO - Headless Telemetry System" << std::endl;
    std::cout << "===========================================" << std::endl;
    
    // Set up signal handlers for graceful shutdown
    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);
    
    // Initialize the data unpacker (telemetry processor)
    DataUnpacker unpacker;
    
    // Initialize InfluxDB writer (reads INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET from env)
    std::unique_ptr<InfluxWriter> influxWriter;
    try {
        influxWriter = std::make_unique<InfluxWriter>();
        std::cout << "InfluxDB writer initialized successfully." << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "WARNING: InfluxDB not configured: " << e.what() << std::endl;
        std::cerr << "         Set INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET to enable." << std::endl;
    }
    
    // Start file sync process in background
    startFileSync();
    
    // Start the telemetry processing
    std::cout << "Starting telemetry data processing..." << std::endl;
    unpacker.start();
    
    // Main application loop
    std::cout << "System running. Press Ctrl+C to shutdown gracefully." << std::endl;
    auto lastInfluxWrite = std::chrono::steady_clock::now();
    while (g_running) {
        // Sleep for a short period to avoid busy waiting
        std::this_thread::sleep_for(std::chrono::milliseconds(100));

        // Publish telemetry to InfluxDB every 2 seconds
        if (influxWriter) {
            auto now = std::chrono::steady_clock::now();
            if (std::chrono::duration_cast<std::chrono::seconds>(now - lastInfluxWrite).count() >= 2) {
                try {
                    TelemetryRecord rec = unpacker.buildTelemetryRecord();
                    influxWriter->write(influxWriter->toLineProtocol(rec));
                } catch (const std::exception& e) {
                    std::cerr << "InfluxDB write error: " << e.what() << std::endl;
                }
                lastInfluxWrite = now;
            }
        }
    }
    
    // Graceful shutdown
    std::cout << "Shutting down telemetry system..." << std::endl;
    unpacker.stop();
    
    std::cout << "SC2 Driver IO shutdown complete." << std::endl;
    return 0;
}
