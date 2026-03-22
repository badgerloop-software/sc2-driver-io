//
// Created by Mingcan Li on 11/16/21.
//

#include "dataUnpacker.h"

// ─────────────────────────────────────────────────────────────────────────────
//  buildTelemetryRecord
//  Maps all live DataUnpacker fields into a TelemetryRecord for InfluxDB.
// ─────────────────────────────────────────────────────────────────────────────

TelemetryRecord DataUnpacker::buildTelemetryRecord() const {
    TelemetryRecord r;

    // ── MCC / Motor Control ──────────────────────────────────────────────────
    r.accelerator_pedal         = getAcceleratorPedal();
    r.speed                     = getSpeed();
    r.mc_status                 = static_cast<uint8_t>(getMcStatus());
    r.crz_pwr_mode              = getCrzPwrMode();
    r.crz_spd_mode              = getCrzSpdMode();
    r.crz_pwr_setpt             = getCrzPwrSetpt();
    r.crz_spd_setpt             = getCrzSpdSetpt();
    r.eco                       = getEco();
    r.main_telem                = getMainTelem();
    r.motor_power               = getMotorPower();

    // ── High Voltage / Shutdown ──────────────────────────────────────────────
    r.driver_eStop              = getDriverEStop();
    r.external_eStop            = getExternalEStop();
    r.crash                     = getCrash();
    r.discharge_enable          = getDischargeEnable();
    r.charge_enable             = getChargeEnable();
    r.isolation                 = getIsolation();
    r.mcu_hv_en                 = getMcuHvEn();
    r.mcu_stat_fdbk             = getMcuStatFdbk();

    // ── High Voltage / MPS ───────────────────────────────────────────────────
    r.low_contactor             = getLowContactor();
    r.use_dcdc                  = getUseDcdc();

    // ── Battery / Supplemental ───────────────────────────────────────────────
    r.supplemental_voltage      = getSupplementalVoltage();
    r.est_supplemental_soc      = getEstSupplementalSoc();

    // ── Main IO / Sensors ────────────────────────────────────────────────────
    r.park_brake                = getParkingBrake();
    r.mainIO_temp               = getMainIOTemp();
    r.motor_controller_temp     = getMotorControllerTemp();
    r.motor_temp                = getMotorTemp();

    // ── Main IO / Lights ─────────────────────────────────────────────────────
    r.l_turn_led_en             = getLTurnLedEn();
    r.r_turn_led_en             = getRTurnLedEn();
    r.headlights_led_en         = getHeadlights();
    r.hazards                   = getHazards();

    // ── Main IO / Firmware Heartbeats ────────────────────────────────────────
    r.bms_can_heartbeat         = getBmsCanHeartbeat();
    r.mainIO_heartbeat          = getMainIOHeartbeat();

    // ── Solar / MPPT ─────────────────────────────────────────────────────────
    r.mppt_current_out          = getMpptCurrentOut();
    r.string1_temp              = getString1Temp();
    r.string2_temp              = getString2Temp();
    r.string3_temp              = getString3Temp();

    // ── Battery / BMS CAN ────────────────────────────────────────────────────
    r.pack_temp                 = getPackTemp();
    r.pack_current              = getPackCurrent();
    r.pack_voltage              = getPackVoltage();
    r.soc                       = getSoc();
    r.fan_speed                 = static_cast<uint8_t>(getFanSpeed());
    r.bms_input_voltage         = getBmsInputVoltage();

    // ── Battery / BMS Faults ─────────────────────────────────────────────────
    r.bps_fault                             = getBpsFault();
    r.voltage_failsafe                      = getVoltageFailsafe();
    r.current_failsafe                      = getCurrentFailsafe();
    r.relay_failsafe                        = getRelayFailsafe();
    r.cell_balancing_active                 = getCellBalancingActive();
    r.charge_interlock_failsafe             = getChargeInterlockFailsafe();
    r.thermistor_b_value_table_invalid      = getThermistorBValueTableInvalid();
    r.input_power_supply_failsafe           = getInputPowerSupplyFailsafe();

    // ── Battery / Cell Group Voltages ────────────────────────────────────────
    const auto& cgv = getCellGroupVoltages();
    if (cgv.size() > 0)  r.cell_group1_voltage  = cgv[0];
    if (cgv.size() > 1)  r.cell_group2_voltage  = cgv[1];
    if (cgv.size() > 2)  r.cell_group3_voltage  = cgv[2];
    if (cgv.size() > 3)  r.cell_group4_voltage  = cgv[3];
    if (cgv.size() > 4)  r.cell_group5_voltage  = cgv[4];
    if (cgv.size() > 5)  r.cell_group6_voltage  = cgv[5];
    if (cgv.size() > 6)  r.cell_group7_voltage  = cgv[6];
    if (cgv.size() > 7)  r.cell_group8_voltage  = cgv[7];
    if (cgv.size() > 8)  r.cell_group9_voltage  = cgv[8];
    if (cgv.size() > 9)  r.cell_group10_voltage = cgv[9];
    if (cgv.size() > 10) r.cell_group11_voltage = cgv[10];
    if (cgv.size() > 11) r.cell_group12_voltage = cgv[11];
    if (cgv.size() > 12) r.cell_group13_voltage = cgv[12];
    if (cgv.size() > 13) r.cell_group14_voltage = cgv[13];
    if (cgv.size() > 14) r.cell_group15_voltage = cgv[14];
    if (cgv.size() > 15) r.cell_group16_voltage = cgv[15];
    if (cgv.size() > 16) r.cell_group17_voltage = cgv[16];
    if (cgv.size() > 17) r.cell_group18_voltage = cgv[17];
    if (cgv.size() > 18) r.cell_group19_voltage = cgv[18];
    if (cgv.size() > 19) r.cell_group20_voltage = cgv[19];
    if (cgv.size() > 20) r.cell_group21_voltage = cgv[20];
    if (cgv.size() > 21) r.cell_group22_voltage = cgv[21];
    if (cgv.size() > 22) r.cell_group23_voltage = cgv[22];
    if (cgv.size() > 23) r.cell_group24_voltage = cgv[23];
    if (cgv.size() > 24) r.cell_group25_voltage = cgv[24];
    if (cgv.size() > 25) r.cell_group26_voltage = cgv[25];
    if (cgv.size() > 26) r.cell_group27_voltage = cgv[26];
    if (cgv.size() > 27) r.cell_group28_voltage = cgv[27];
    if (cgv.size() > 28) r.cell_group29_voltage = cgv[28];
    if (cgv.size() > 29) r.cell_group30_voltage = cgv[29];
    if (cgv.size() > 30) r.cell_group31_voltage = cgv[30];

    // ── Software / Timestamps ────────────────────────────────────────────────
    r.tstamp_hr  = static_cast<uint8_t>(getTstampHr());
    r.tstamp_mn  = static_cast<uint8_t>(getTstampMn());
    r.tstamp_sc  = static_cast<uint8_t>(getTstampSc());
    r.tstamp_ms  = static_cast<uint16_t>(getTstampMs());

    // ── Software / GPS ───────────────────────────────────────────────────────
    r.lat  = getLat();
    r.lon  = getLon();
    r.elev = getElev();

    return r;
}

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
        qDebug() << cell_group_voltages_begin;
        arrayOffset += arr[0].GetInt();
        dataCount++;
    }

    fclose(fp);


    BackendProcesses* retriever = new BackendProcesses(bytes, names, types, tstampOff, mutex, arrayOffset);
    fetcher = new DataFetcher(bytes, arrayOffset, mutex, gpsOffset);
    retriever->moveToThread(&backendThread);
    fetcher->moveToThread(&dataFetchThread);

    connect(&dataFetchThread, &QThread::started, fetcher, &DataFetcher::startThread);
    connect(this, &DataUnpacker::sendSignal, fetcher, &DataFetcher::sendData);
    connect(&backendThread, &QThread::started, retriever, &BackendProcesses::startThread);
    connect(retriever, &BackendProcesses::dataReady, this, &DataUnpacker::unpack);
    connect(retriever, &BackendProcesses::eng_dash_connection, this, &DataUnpacker::eng_dash_connection);
    connect(&backendThread, &QThread::finished, retriever, &QObject::deleteLater);
    connect(&backendThread, &QThread::finished, &backendThread, &QThread::deleteLater);
    connect(&dataFetchThread, &QThread::finished, fetcher, &DataFetcher::deleteLater);
    connect(&dataFetchThread, &QThread::finished, &dataFetchThread, &QThread::deleteLater);

    connect(fetcher, &DataFetcher::dataFetched, retriever, &BackendProcesses::threadProcedure);

    backendThread.start();
    dataFetchThread.start();
}

DataUnpacker::~DataUnpacker()
{
    stop(); // Ensure threads are properly stopped
}

void DataUnpacker::unpack()
{
    int currByte = 0;

    mutex.lock();

    for(uint i=0; i < names.size(); i++) {
        if(types[i] == "float") {
            // Make sure the property exists
            if(this->property(names[i].c_str()).isValid()) {
                this->setProperty(names[i].c_str(), bytesToFloat(bytes, currByte));
            } else if((i >= cell_group_voltages_begin) && (i <= cell_group_voltages_end)) {
                cell_group_voltages[i - cell_group_voltages_begin] = bytesToFloat(bytes, currByte);
            }
        } else if(types[i] == "uint8") {
            // Make sure the property exists
            if(this->property(names[i].c_str()).isValid()) {
                this->setProperty(names[i].c_str(), bytesToGeneralData(bytes, currByte, currByte + byteNums[i] - 1, (uint8_t)0));
            }
        } else if(types[i] == "uint16") {
            // Make sure the property exists
            if(this->property(names[i].c_str()).isValid()) {
                this->setProperty(names[i].c_str(), bytesToGeneralData(bytes, currByte, currByte + byteNums[i] - 1, (uint16_t)0));
            }
        } else if(types[i] == "bool") {
            // Make sure the property exists
            if(this->property(names[i].c_str()).isValid()) {
                this->setProperty(names[i].c_str(), bytesToGeneralData(bytes, currByte, currByte + byteNums[i] - 1, false));
            }
        } else if(types[i] == "char") {
            // Make sure the property exists
            if(this->property(names[i].c_str()).isValid()) {
                // NOTE: char data is displayed as its ASCII decimal value, not the character, so QString is used instead
                this->setProperty(names[i].c_str(), QString::fromStdString(std::string(1, bytesToGeneralData(bytes, currByte, currByte + byteNums[i] - 1, (char)0))));
            }
        } else if(types[i] == "double") {
            // TODO: No double data yet; Implement when there is double data
        }

        currByte += byteNums[i];
    }

    mutex.unlock();

    this->restart_enable = checkRestartEnable();

    // Refresh frontend
    QGuiApplication::processEvents();
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

