//
// Created by Mingcan Li on 11/16/21.
//

#include "dataUnpacker.h"

double bytesToDouble(const std::vector<uint8_t>& data, int start_pos)
{
    double number;
    const uint8_t* dataPtr = data.data();
    memcpy(&number, &dataPtr[start_pos], sizeof(double));
    return number;
}

float bytesToFloat(const std::vector<uint8_t>& data, int start_pos)
{
    float number;
    const uint8_t* dataPtr = data.data();
    memcpy(&number, &dataPtr[start_pos], sizeof(float));
    return number;
}

template <typename E>
E bytesToGeneralData(const std::vector<uint8_t>& data, int startPos, int endPos, E typeZero)
{
    int byteNum=endPos-startPos;
    auto var = typeZero;

    for(int i = endPos ; i>=startPos ; i--) {
        var = var + (((uint8_t) data[i]) << (byteNum * 8));
        byteNum--;
    }

    return var;
}



DataUnpacker::DataUnpacker()
{
    FILE* fp = fopen("./sc1-data-format/format.json", "r"); // NOTE: Windows: "rb"; non-Windows: "r"
    if(fp == 0) {
        fp = fopen("../sc1-data-format/format.json", "r"); // NOTE: Windows: "rb"; non-Windows: "r"
    }

    char readBuffer[65536];
    FileReadStream is(fp, readBuffer, sizeof(readBuffer));

    Document d;
    d.ParseStream(is);

    int arrayOffset = 0;
    timestampOffsets tstampOff;
    int dataCount = 0;
    cell_group_voltages_begin = -1;
    cell_group_voltages_end = -1;

    for(Value::ConstMemberIterator itr = d.MemberBegin(); itr != d.MemberEnd(); ++itr) {
        std::string name = itr->name.GetString();
        const Value& arr = itr->value.GetArray();

        names.push_back(name);
        byteNums.push_back(arr[0].GetInt());
        types.push_back(arr[1].GetString());

        if(name == "tstamp_hr") {
            tstampOff.hr = arrayOffset;
        } else if(name == "tstamp_mn") {
            tstampOff.mn = arrayOffset;
        } else if(name == "tstamp_sc") {
            tstampOff.sc = arrayOffset;
        } else if(name == "tstamp_ms") {
            tstampOff.ms = arrayOffset;
        } else if(name == "tstamp_unix") {
            tstampOff.unix = arrayOffset;
        } else if(name.substr(0, 10) == "cell_group") {
            if(cell_group_voltages_begin == -1) {
                cell_group_voltages_begin = dataCount;
            } else {
                cell_group_voltages_end = dataCount;
            }
            cell_group_voltages.push_back(0);
        } else if (name == "lat") {
            gpsOffset.lat = arrayOffset;
        } else if (name == "lon") {
            gpsOffset.lon = arrayOffset;
        } else if (name == "elev") {
            gpsOffset.alt = arrayOffset;
        }
        std::cout << "Cell group voltages begin: " << cell_group_voltages_begin << std::endl;
        arrayOffset += arr[0].GetInt();
        dataCount++;
    }

    fclose(fp);

    // NOTE: Per architecture review, DataFetcher is removed.
    // Future implementation will use CAN bridge from Python coordinator.
    // For now, BackendProcesses can be initialized but won't receive data until
    // the CAN bridge is implemented.
    
    std::cout << "DataUnpacker initialized with " << names.size() << " data fields" << std::endl;
    std::cout << "Waiting for CAN bridge implementation..." << std::endl;
    
    // TODO: Initialize CAN bridge here when implemented
    // The CAN bridge will receive data from Python's CAN reader via Unix socket
    // and trigger the unpack() method via callback
}

DataUnpacker::~DataUnpacker()
{
    stop(); // Ensure threads are properly stopped
}

void DataUnpacker::unpack()
{
    int currByte = 0;

    mutex.lock();

    // TODO: Replace Qt property system with direct member variable mapping
    // For now, this is a stub that processes the byte buffer but doesn't
    // populate all member variables. This should be replaced with a proper
    // mapping based on the signal names from format.json to the member variables
    // defined in the header file.
    
    for(uint i=0; i < names.size(); i++) {
        if(types[i] == "float") {
            float value = bytesToFloat(bytes, currByte);
            
            // Map known float values to member variables
            if(names[i] == "speed") speed = value;
            else if(names[i] == "accelerator_pedal") accelerator_pedal = value;
            else if(names[i] == "soc") soc = value;
            else if(names[i] == "mppt_current_out") mppt_current_out = value;
            else if(names[i] == "pack_voltage") pack_voltage = value;
            else if(names[i] == "pack_current") pack_current = value;
            else if(names[i] == "pack_temp") pack_temp = value;
            else if(names[i] == "motor_temp") motor_temp = value;
            else if(names[i] == "motor_power") motor_power = value;
            else if(names[i] == "lat") lat = value;
            else if(names[i] == "lon") lon = value;
            else if(names[i] == "elev") elev = value;
            else if((i >= cell_group_voltages_begin) && (i <= cell_group_voltages_end)) {
                cell_group_voltages[i - cell_group_voltages_begin] = value;
            }
            // Add more mappings as needed
            
        } else if(types[i] == "uint8") {
            uint8_t value = bytesToGeneralData(bytes, currByte, currByte + byteNums[i] - 1, (uint8_t)0);
            
            // Map known uint8 values
            if(names[i] == "fan_speed") fan_speed = value;
            else if(names[i] == "tstamp_hr") tstamp_hr = value;
            else if(names[i] == "tstamp_mn") tstamp_mn = value;
            else if(names[i] == "tstamp_sc") tstamp_sc = value;
            // Add more mappings as needed
            
        } else if(types[i] == "uint16") {
            uint16_t value = bytesToGeneralData(bytes, currByte, currByte + byteNums[i] - 1, (uint16_t)0);
            
            // Map known uint16 values
            if(names[i] == "tstamp_ms") tstamp_ms = value;
            // Add more mappings as needed
            
        } else if(types[i] == "bool") {
            bool value = bytesToGeneralData(bytes, currByte, currByte + byteNums[i] - 1, false);
            
            // Map known bool values
            if(names[i] == "headlights") headlights = value;
            else if(names[i] == "l_turn_led_en") l_turn_led_en = value;
            else if(names[i] == "r_turn_led_en") r_turn_led_en = value;
            else if(names[i] == "hazards") hazards = value;
            else if(names[i] == "parking_brake") parking_brake = value;
            else if(names[i] == "driver_eStop") driver_eStop = value;
            else if(names[i] == "external_eStop") external_eStop = value;
            else if(names[i] == "crash") crash = value;
            else if(names[i] == "door") door = value;
            else if(names[i] == "mcu_check") mcu_check = value;
            else if(names[i] == "isolation") isolation = value;
            else if(names[i] == "discharge_enable") discharge_enable = value;
            else if(names[i] == "mcu_hv_en") mcu_hv_en = value;
            // Add more mappings as needed
            
        } else if(types[i] == "char") {
            // char c = bytesToGeneralData(bytes, currByte, currByte + byteNums[i] - 1, (char)0);
            // TODO: Map char values if needed
            
        } else if(types[i] == "double") {
            // TODO: No double data yet; Implement when there is double data
        }

        currByte += byteNums[i];
    }

    mutex.unlock();

    this->restart_enable = checkRestartEnable();

    // Notify any registered callbacks that data has changed
    notifyDataChanged();
}

void DataUnpacker::eng_dash_connection(bool state) {
    eng_dash_commfail = !state;
}

bool DataUnpacker::checkRestartEnable() {
    return (!restart_enable ? !mcu_hv_en : false) || driver_eStop || external_eStop || isolation || door || crash || mcu_check || discharge_enable || restart_enable;
}

void DataUnpacker::enableRestart() {
    // Send restart signal to backend
    // TODO: Implement backend communication without Qt signals
}

void DataUnpacker::start() {
    running = true;
    // TODO: Start data processing threads
}

void DataUnpacker::stop() {
    running = false;
    if (dataFetchThread.joinable()) {
        dataFetchThread.join();
    }
    if (backendThread.joinable()) {
        backendThread.join();
    }
}

void DataUnpacker::setDataChangeCallback(DataChangeCallback callback) {
    dataChangeCallback = callback;
}

void DataUnpacker::notifyDataChanged() {
    if (dataChangeCallback) {
        dataChangeCallback();
    }
}

