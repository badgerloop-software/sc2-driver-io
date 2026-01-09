//
// Created by Mingcan Li on 1/22/23.
// Modernized to remove Qt dependencies
//

#ifndef TELEMETRYLIB_DTI_H
#define TELEMETRYLIB_DTI_H

#include <vector>
#include <functional>
#include <cstdint>
#include <unistd.h>

// Network socket state enum (replacement for QAbstractSocket::SocketState)
enum class SocketState {
    UnconnectedState,
    HostLookupState,
    ConnectingState,
    ConnectedState,
    BoundState,
    ListeningState,
    ClosingState
};

// Data Telemetry Interface base class
class DTI {
public:
    // Callback types for event notifications
    using ConnectionStatusCallback = std::function<void()>;
    
    virtual ~DTI() = default;
    
    /**
     * Send bytes via channel to be implemented, do not record data in this function.
     * @param bytes data buffer to send
     * @param timestamp when the data was created
     */
    virtual void sendData(const std::vector<uint8_t>& bytes, long long timestamp) = 0;
    
    /**
     * Set callback for connection status changes
     */
    void setConnectionStatusCallback(ConnectionStatusCallback callback) {
        connectionStatusCallback = callback;
    }
    
    // Virtual methods for derived classes to override
    virtual void onNewConnection() {}
    virtual void onSocketStateChanged(SocketState state) {}
    virtual void readReply() {}
    
protected:
    // Helper method to notify connection status changes
    void notifyConnectionStatusChanged() {
        if (connectionStatusCallback) {
            connectionStatusCallback();
        }
    }
    
private:
    ConnectionStatusCallback connectionStatusCallback;
};

#endif //TELEMETRY
// LIB_DMIF_H
