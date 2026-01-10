//
// CAN Bridge - Receives CAN data from Python via Unix domain socket
// Implementation
//

#include "can_bridge.h"
#include <cerrno>

CANBridge::CANBridge() 
    : running_(false), socket_fd_(-1) {
}

CANBridge::~CANBridge() {
    stop();
}

bool CANBridge::start() {
    if (running_) {
        std::cerr << "CAN Bridge already running" << std::endl;
        return false;
    }
    
    // Create Unix domain socket
    socket_fd_ = socket(AF_UNIX, SOCK_DGRAM, 0);
    if (socket_fd_ < 0) {
        std::cerr << "Failed to create CAN bridge socket: " << strerror(errno) << std::endl;
        return false;
    }
    
    // Remove any existing socket file
    unlink(SOCKET_PATH);
    
    // Bind to socket path
    struct sockaddr_un addr;
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, SOCKET_PATH, sizeof(addr.sun_path) - 1);
    
    if (bind(socket_fd_, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        std::cerr << "Failed to bind CAN bridge socket: " << strerror(errno) << std::endl;
        close(socket_fd_);
        socket_fd_ = -1;
        return false;
    }
    
    std::cout << "CAN Bridge listening on " << SOCKET_PATH << std::endl;
    
    // Start receive thread
    running_ = true;
    recv_thread_ = std::thread(&CANBridge::receiveLoop, this);
    
    return true;
}

void CANBridge::stop() {
    if (!running_) {
        return;
    }
    
    running_ = false;
    
    // Close socket to unblock recv
    if (socket_fd_ >= 0) {
        close(socket_fd_);
        socket_fd_ = -1;
    }
    
    // Wait for thread to finish
    if (recv_thread_.joinable()) {
        recv_thread_.join();
    }
    
    // Clean up socket file
    unlink(SOCKET_PATH);
    
    std::cout << "CAN Bridge stopped. Messages received: " << messages_received_ 
              << ", dropped: " << messages_dropped_ << std::endl;
}

void CANBridge::setMessageCallback(MessageCallback callback) {
    callback_ = callback;
}

void CANBridge::receiveLoop() {
    CANBridgeMessage msg;
    
    std::cout << "CAN Bridge receive loop started" << std::endl;
    
    while (running_) {
        ssize_t n = recv(socket_fd_, &msg, sizeof(msg), 0);
        
        if (n < 0) {
            if (running_) {
                std::cerr << "CAN Bridge recv error: " << strerror(errno) << std::endl;
            }
            break;
        }
        
        if (n != sizeof(msg)) {
            std::cerr << "CAN Bridge received malformed message (expected " 
                      << sizeof(msg) << " bytes, got " << n << ")" << std::endl;
            messages_dropped_++;
            continue;
        }
        
        messages_received_++;
        
        // Call registered callback if set
        if (callback_) {
            callback_(msg);
        }
        
        // Log every 1000 messages
        if (messages_received_ % 1000 == 0) {
            std::cout << "CAN Bridge: " << messages_received_ << " messages received" << std::endl;
        }
    }
    
    std::cout << "CAN Bridge receive loop ended" << std::endl;
}
