//
// Created by Mingcan Li on 2/3/23.
// Modernized to remove Qt dependencies
//
#include "telemetry.h"
#include <iostream>

// Default constructor
Telemetry::Telemetry() {}

// Constructor with commChannels initialization
Telemetry::Telemetry(std::vector<DTI *> commChannels) {
    comm = commChannels;
    // Output the number of initialized communication channels to console
    std::cout << "Comm channels initialized: " << comm.size() << std::endl;
}

// Broadcast data to all communication channels 
void Telemetry::sendData(const std::vector<uint8_t>& bytes, long long timestamp) {
    // Loop through all communication channels
    for (size_t i = 0; i < comm.size(); i++) {
        // Send data to the current communication channel
        comm[i]->sendData(bytes, timestamp);
    }
}