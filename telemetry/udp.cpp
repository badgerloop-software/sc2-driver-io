//
// Created by Mingcan Li on 1/30/24.
// Updated to remove Qt dependencies
//

#include "DTI.h"
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <cstring>
#include <iostream>
#include <stdexcept>
#include <atomic>

class UDP : public DTI {
public:
    UDP(const std::string& serverAddress, int serverPort) 
        : serverAddress_(serverAddress), serverPort_(serverPort), connection_(true) {
        
        // Create UDP socket
        socketFd_ = socket(AF_INET, SOCK_DGRAM, 0);
        if (socketFd_ < 0) {
            throw std::runtime_error("Failed to create UDP socket");
        }
        
        // Set up server address structure
        memset(&serverAddr_, 0, sizeof(serverAddr_));
        serverAddr_.sin_family = AF_INET;
        serverAddr_.sin_port = htons(serverPort);
        
        if (inet_pton(AF_INET, serverAddress.c_str(), &serverAddr_.sin_addr) <= 0) {
            close(socketFd_);
            throw std::runtime_error("Invalid server address: " + serverAddress);
        }
        
        std::cout << "UDP initialized for " << serverAddress << ":" << serverPort << std::endl;
        
        // Notify connection status changed
        if (connectionStatusCallback) {
            connectionStatusCallback();
        }
    }

    ~UDP() {
        if (socketFd_ >= 0) {
            close(socketFd_);
        }
    }

    void sendData(const std::vector<uint8_t>& bytes, long long timestamp) override {
        std::cout << "Sending via UDP" << std::endl;
        
        // Add framing tags
        std::vector<uint8_t> framed;
        framed.reserve(bytes.size() + 11);
        
        const char* start = "<bsr>";
        const char* end = "</bsr>";
        framed.insert(framed.end(), start, start + 5);
        framed.insert(framed.end(), bytes.begin(), bytes.end());
        framed.insert(framed.end(), end, end + 6);
        
        // Send datagram
        ssize_t sent = sendto(socketFd_, framed.data(), framed.size(), 0,
                             (struct sockaddr*)&serverAddr_, sizeof(serverAddr_));
        
        if (sent < 0) {
            std::cerr << "Failed to send UDP datagram: " << strerror(errno) << std::endl;
        } else {
            std::cout << "Sent " << sent << " bytes via UDP" << std::endl;
        }
    }

private:
    int socketFd_;
    std::string serverAddress_;
    int serverPort_;
    struct sockaddr_in serverAddr_;
    std::atomic<bool> connection_;
};