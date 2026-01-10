#ifndef GPS_H
#define GPS_H

#include <cstdio>
#include "3rdparty/serial/serialib.h"
#include <string>
#include <atomic>
#include <vector>
#include <functional>

using namespace std;

struct GPSData {
    float lat;
    float lon;
    float alt;
};

class GPS {
public:
    GPS();
    ~GPS();
    bool init(string device);
    bool initialized();
    void start_loop(string nmeaDevice);
    GPSData getLoc();
    
    // Public method to trigger auto-init (replaces Qt slot)
    void autoInit(); // automatically find and init gps device
    
private:
    string usbnmeaprobe(vector<string> devices);
    serialib serial;
    atomic<bool> initSuccess = false;
    atomic<float> lat=-1000, lon=-1000, alt=-1000;
};

#endif // GPS_H