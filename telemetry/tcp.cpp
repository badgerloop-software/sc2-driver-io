//
// Created by Mingcan Li on 1/22/23.
// Updated to remove Qt dependencies
//

#include "DTI.h"
#include "Config.h"
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <fcntl.h>
#include <cstring>
#include <iostream>
#include <vector>
#include <thread>
#include <atomic>
#include <algorithm>

// macOS doesn't have MSG_NOSIGNAL, use SO_NOSIGPIPE instead
#ifdef __APPLE__
#define MSG_NOSIGNAL 0
#endif

class TCP : public DTI {
public:
    void sendData(const std::vector<uint8_t>& bytes, long long timestamp) override {
        std::cout << "Sending via TCP" << std::endl;
        
        // Add framing tags
        std::vector<uint8_t> framed;
        framed.reserve(bytes.size() + 11);
        
        const char* start = "<bsr>";
        const char* end = "</bsr>";
        framed.insert(framed.end(), start, start + 5);
        framed.insert(framed.end(), bytes.begin(), bytes.end());
        framed.insert(framed.end(), end, end + 6);
        
        // Send to all connected clients
        std::lock_guard<std::mutex> lock(socketsMutex_);
        for (auto it = clientSockets_.begin(); it != clientSockets_.end(); ) {
            ssize_t sent = send(*it, framed.data(), framed.size(), MSG_NOSIGNAL);
            if (sent < 0) {
                std::cerr << "Failed to send to client, closing connection" << std::endl;
                close(*it);
                it = clientSockets_.erase(it);
            } else {
                ++it;
            }
        }
    }

    bool getConnectionStatus() {
        return connection_;
    }

    TCP(const std::string& addr, int port) : connection_(false), finish_(false) {
        // Create server socket
        serverFd_ = socket(AF_INET, SOCK_STREAM, 0);
        if (serverFd_ < 0) {
            throw std::runtime_error("Failed to create TCP server socket");
        }
        
        // Set socket options
        int opt = 1;
        setsockopt(serverFd_, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
        
        // Bind to address
        struct sockaddr_in serverAddr;
        memset(&serverAddr, 0, sizeof(serverAddr));
        serverAddr.sin_family = AF_INET;
        serverAddr.sin_port = htons(port);
        
        if (inet_pton(AF_INET, addr.c_str(), &serverAddr.sin_addr) <= 0) {
            close(serverFd_);
            throw std::runtime_error("Invalid TCP server address: " + addr);
        }
        
        if (bind(serverFd_, (struct sockaddr*)&serverAddr, sizeof(serverAddr)) < 0) {
            close(serverFd_);
            throw std::runtime_error("Failed to bind TCP server socket");
        }
        
        // Listen for connections
        if (listen(serverFd_, 5) < 0) {
            close(serverFd_);
            throw std::runtime_error("Failed to listen on TCP server socket");
        }
        
        std::cout << "TCP server listening on " << addr << ":" << port << std::endl;
        
        // Start accept thread
        acceptThread_ = std::thread(&TCP::acceptLoop, this);
        
        // Start connection check thread
        checkThread_ = std::thread(&TCP::checkConnection, this);
    }

    ~TCP() {
        finish_ = true;
        
        // Close server socket to unblock accept
        if (serverFd_ >= 0) {
            close(serverFd_);
        }
        
        if (acceptThread_.joinable()) {
            acceptThread_.join();
        }
        
        if (checkThread_.joinable()) {
            checkThread_.join();
        }
        
        // Close all client sockets
        std::lock_guard<std::mutex> lock(socketsMutex_);
        for (int fd : clientSockets_) {
            close(fd);
        }
    }

private:
    int serverFd_;
    std::vector<int> clientSockets_;
    std::mutex socketsMutex_;
    std::atomic<bool> connection_;
    std::atomic<bool> finish_;
    std::thread acceptThread_;
    std::thread checkThread_;
    
    void acceptLoop() {
        while (!finish_) {
            struct sockaddr_in clientAddr;
            socklen_t clientLen = sizeof(clientAddr);
            
            int clientFd = accept(serverFd_, (struct sockaddr*)&clientAddr, &clientLen);
            if (clientFd < 0) {
                if (!finish_) {
                    std::cerr << "Accept failed: " << strerror(errno) << std::endl;
                }
                break;
            }
            
            char clientIP[INET_ADDRSTRLEN];
            inet_ntop(AF_INET, &clientAddr.sin_addr, clientIP, INET_ADDRSTRLEN);
            std::cout << "New TCP connection from " << clientIP << std::endl;
            
            {
                std::lock_guard<std::mutex> lock(socketsMutex_);
                clientSockets_.push_back(clientFd);
                connection_ = true;
            }
            
            if (connectionStatusCallback) {
                connectionStatusCallback();
            }
        }
    }
    
    void checkConnection() {
        std::string serverIP = Config::getInstance().getString("tcp_server_ip", "127.0.0.1");
        int serverPort = Config::getInstance().getInt("tcp_port", 8080);
        
        while (!finish_) {
            int testFd = socket(AF_INET, SOCK_STREAM, 0);
            if (testFd >= 0) {
                struct sockaddr_in testAddr;
                memset(&testAddr, 0, sizeof(testAddr));
                testAddr.sin_family = AF_INET;
                testAddr.sin_port = htons(serverPort);
                inet_pton(AF_INET, serverIP.c_str(), &testAddr.sin_addr);
                
                // Set non-blocking for timeout
                int flags = fcntl(testFd, F_GETFL, 0);
                fcntl(testFd, F_SETFL, flags | O_NONBLOCK);
                
                connect(testFd, (struct sockaddr*)&testAddr, sizeof(testAddr));
                
                fd_set writefds;
                FD_ZERO(&writefds);
                FD_SET(testFd, &writefds);
                
                struct timeval timeout;
                timeout.tv_sec = 4;
                timeout.tv_usec = 0;
                
                bool connected = (select(testFd + 1, NULL, &writefds, NULL, &timeout) > 0);
                close(testFd);
                
                bool prevConnection = connection_;
                connection_ = connected;
                
                if (prevConnection != connected && connectionStatusCallback) {
                    connectionStatusCallback();
                }
            }
            
            usleep(50000); // 50ms
        }
    }
};

