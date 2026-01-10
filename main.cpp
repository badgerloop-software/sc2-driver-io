#include <iostream>
#include <thread>
#include <chrono>
#include <filesystem>
#include <cstdlib>
#include <signal.h>
#include "data_processor/dataUnpacker.h"
#include "telemetry/can_bridge.h"

// Global objects for clean shutdown
volatile bool g_running = true;
CANBridge* g_can_bridge = nullptr;

// Signal handler for graceful shutdown
void signalHandler(int signal) {
    std::cout << "\nReceived signal " << signal << ". Shutting down gracefully..." << std::endl;
    g_running = false;
    
    // Stop CAN bridge if running
    if (g_can_bridge) {
        g_can_bridge->stop();
    }
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
    
    // Initialize CAN Bridge (receives CAN data from Python)
    std::cout << "Initializing CAN Bridge..." << std::endl;
    CANBridge can_bridge;
    g_can_bridge = &can_bridge;
    
    // Set callback for received CAN messages
    can_bridge.setMessageCallback([](const CANBridgeMessage& msg) {
        // TODO: Process CAN message and feed to telemetry system
        // For now, just log periodically
        static uint64_t msg_count = 0;
        msg_count++;
        
        if (msg_count % 100 == 0) {
            std::cout << "CAN Bridge: Received message " << msg_count 
                      << " - ID: 0x" << std::hex << msg.can_id << std::dec
                      << ", len: " << (int)msg.data_len << std::endl;
        }
    });
    
    if (!can_bridge.start()) {
        std::cerr << "Failed to start CAN Bridge!" << std::endl;
        return 1;
    }
    
    std::cout << "CAN Bridge started successfully" << std::endl;
    
    // Initialize the data unpacker (telemetry processor)
    DataUnpacker unpacker;
    
    // Start file sync process in background
    startFileSync();
    
    // Start the telemetry processing
    std::cout << "Starting telemetry data processing..." << std::endl;
    unpacker.start();
    
    // Main application loop
    std::cout << "System running. Press Ctrl+C to shutdown gracefully." << std::endl;
    std::cout << "Waiting for CAN data from Python coordinator..." << std::endl;
    while (g_running) {
        // Sleep for a short period to avoid busy waiting
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        
        // Periodic status check every 10 seconds
        static auto last_status = std::chrono::steady_clock::now();
        auto now = std::chrono::steady_clock::now();
        if (std::chrono::duration_cast<std::chrono::seconds>(now - last_status).count() >= 10) {
            std::cout << "Status: CAN messages received: " << can_bridge.getMessagesReceived() << std::endl;
            last_status = now;
        }
    }
    
    // Graceful shutdown
    std::cout << "Shutting down telemetry system..." << std::endl;
    can_bridge.stop();
    unpacker.stop();
    
    std::cout << "SC2 Driver IO shutdown complete." << std::endl;
    std::cout << "Total CAN messages processed: " << can_bridge.getMessagesReceived() << std::endl;
    return 0;
}
