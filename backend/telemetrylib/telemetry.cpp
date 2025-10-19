//
// Created by Mingcan Li on 2/3/23.
// Commented by ChatGPT
//
#include "telemetry.h"

// Default constructor
Telemetry::Telemetry() {
    threadPool = new QThreadPool(this);
    // Set max thread count to ensure all channels can run simultaneously
    threadPool->setMaxThreadCount(10);
}

// Constructor with commChannels initialization
Telemetry::Telemetry(std::vector<DTI *> commChannels) {
    comm = commChannels;
    // Output the number of initialized communication channels to console
    qDebug() << "comm channels initialized: " << comm.size();

    // Initialize thread pool
    threadPool = new QThreadPool(this);
    // Set max thread count to ensure all channels can run simultaneously
    threadPool->setMaxThreadCount(qMax(comm.size(), 2));
    qDebug() << "Thread pool max threads: " << threadPool->maxThreadCount();
}

// Destructor
Telemetry::~Telemetry(){
    // Wait for all tasks complete before destruction
    threadPool->waitForDone();
}

// Broadcast data to all communication channels IN PARALLEL (non-blocking)
void Telemetry::sendData(QByteArray bytes, long long timestamp) {
    // Loop through all communication channels and submit each as a task
    for (int i = 0; i < comm.size(); i++) {
        // Create a new SendDataTask for the current channel
        SendDataTask* task = new SendDataTask(comm[i], bytes, timestamp);
        // Submit to thread pool - returns immediately without blocking
        threadPool->start(task);
    }
    qDebug() << "Data queued for parallel transmission across" << comm.size() << "channels.";
}

// Broadcast data to all communication channels IN PARALLEL (blocking - waits for completion)
void Telemetry::sendDataSync(QByteArray bytes, long long timestamp) {
    // Loop through all communication channels and submit each as a task
    for (int i = 0; i < comm.size(); i++) {
        // Create a new SendDataTask for the current channel
        SendDataTask* task = new SendDataTask(comm[i], bytes, timestamp);
        // Submit to thread pool - returns immediately without blocking
        threadPool->start(task);
    }
    // Wait for all tasks to complete before returning
    threadPool->waitForDone();
    qDebug() << "Data sent synchronously across" << comm.size() << "channels.";
}