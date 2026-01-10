//
// CAN Bridge - Receives CAN data from Python via Unix domain socket
//

#ifndef CAN_BRIDGE_H
#define CAN_BRIDGE_H

#include <sys/socket.h>
#include <sys/un.h>
#include <thread>
#include <atomic>
#include <functional>
#include <vector>
#include <cstring>
#include <unistd.h>
#include <iostream>

#define SOCKET_PATH "/tmp/sc2_can_bridge.sock"
#define MAX_MSG_SIZE 64

// Packed structure for CAN message from Python
struct CANBridgeMessage {
    uint32_t can_id;
    uint64_t timestamp_us;
    uint8_t data_len;
    uint8_t data[8];
} __attribute__((packed));

class CANBridge {
public:
    // Callback type for received CAN messages
    using MessageCallback = std::function<void(const CANBridgeMessage&)>;
    
    CANBridge();
    ~CANBridge();
    
    // Start the bridge and begin listening for messages
    bool start();
    
    // Stop the bridge
    void stop();
    
    // Set callback for received messages
    void setMessageCallback(MessageCallback callback);
    
    // Check if bridge is running
    bool isRunning() const { return running_; }
    
    // Get statistics
    uint64_t getMessagesReceived() const { return messages_received_; }
    uint64_t getMessagesDropped() const { return messages_dropped_; }

private:
    void receiveLoop();
    
    std::atomic<bool> running_;
    int socket_fd_;
    std::thread recv_thread_;
    MessageCallback callback_;
    
    // Statistics
    std::atomic<uint64_t> messages_received_{0};
    std::atomic<uint64_t> messages_dropped_{0};
};

#endif // CAN_BRIDGE_H
