//
// Created by Mingcan Li on 11/16/21.
// Modernized to remove Qt dependencies
//

#ifndef DATAPROCESSOR_DATAUNPACKER_H
#define DATAPROCESSOR_DATAUNPACKER_H

#include <mutex>
#include <thread>
#include <functional>
#include <vector>
#include <string>
#include <atomic>
#include "backend/backendProcesses.h"
#include "backend/dataFetcher.h"
#include "3rdparty/rapidjson/document.h"
#include "3rdparty/rapidjson/filereadstream.h"

using namespace rapidjson;

// Forward declaration for GPS data structure
struct GPSData;

class DataUnpacker
{
public:
    // Callback function type for data change notifications
    using DataChangeCallback = std::function<void()>;
    
    explicit DataUnpacker();
    ~DataUnpacker();
    
    // Start and stop the data processing
    void start();
    void stop();
    
    // Set callback for data change notifications
    void setDataChangeCallback(DataChangeCallback callback);
    
    // Public interface methods (replacements for Qt slots)
    void unpack();
    void eng_dash_connection(bool state);
    void enableRestart();
    
    // Getter methods for telemetry data (replacements for Q_PROPERTY)
    int getFanSpeed() const { return fan_speed; }
    int getTstampHr() const { return tstamp_hr; }
    int getTstampMn() const { return tstamp_mn; }
    int getTstampSc() const { return tstamp_sc; }
    int getTstampMs() const { return tstamp_ms; }
    
    bool getLTurnLedEn() const { return l_turn_led_en; }
    bool getRTurnLedEn() const { return r_turn_led_en; }
    bool getHazards() const { return hazards; }
    bool getHeadlights() const { return headlights; }
    bool getMainIOHeartbeat() const { return mainIO_heartbeat; }
    bool getEngDashCommfail() const { return eng_dash_commfail; }
    bool getCrzPwrMode() const { return crz_pwr_mode; }
    bool getCrzSpdMode() const { return crz_spd_mode; }

    
    // Additional getter methods for shutdown circuit data
    bool getDriverEStop() const { return driver_eStop; }
    bool getExternalEStop() const { return external_eStop; }
    bool getCrash() const { return crash; }
    bool getDoor() const { return door; }
    bool getMcuCheck() const { return mcu_check; }
    bool getIsolation() const { return isolation; }
    bool getDischargeEnable() const { return discharge_enable; }
    bool getLowContactor() const { return low_contactor; }
    bool getBmsCanHeartbeat() const { return bms_can_heartbeat; }
    bool getVoltageFailsafe() const { return voltage_failsafe; }
    bool getCurrentFailsafe() const { return current_failsafe; }
    bool getInputPowerSupplyFailsafe() const { return input_power_supply_failsafe; }
    bool getRelayFailsafe() const { return relay_failsafe; }
    bool getCellBalancingActive() const { return cell_balancing_active; }
    bool getChargeInterlockFailsafe() const { return charge_interlock_failsafe; }
    bool getThermistorBValueTableInvalid() const { return thermistor_b_value_table_invalid; }
    bool getChargeEnable() const { return charge_enable; }
    bool getBpsFault() const { return bps_fault; }
    bool getUseDcdc() const { return use_dcdc; }
    bool getSupplementalValid() const { return supplemental_valid; }
    bool getMcuHvEn() const { return mcu_hv_en; }
    bool getMcuStatFdbk() const { return mcu_stat_fdbk; }
    bool getParkingBrake() const { return parking_brake; }
    bool getEco() const { return eco; }
    bool getMainTelem() const { return main_telem; }
    int getMcStatus() const { return mc_status; }
    bool getRestartEnable() const { return restart_enable; }

    
    // Float getters  
    float getSpeed() const { return speed; }
    float getAcceleratorPedal() const { return accelerator_pedal; }
    float getSoc() const { return soc; }
    float getMpptCurrentOut() const { return mppt_current_out; }
    float getPackVoltage() const { return pack_voltage; }
    float getPackCurrent() const { return pack_current; }
    float getPackTemp() const { return pack_temp; }
    float getBmsInputVoltage() const { return bms_input_voltage; }
    float getMotorTemp() const { return motor_temp; }
    float getMotorPower() const { return motor_power; }
    float getDriverIOTemp() const { return driverIO_temp; }
    float getMainIOTemp() const { return mainIO_temp; }
    float getMotorControllerTemp() const { return motor_controller_temp; }
    float getCabinTemp() const { return cabin_temp; }
    float getString1Temp() const { return string1_temp; }
    float getString2Temp() const { return string2_temp; }
    float getString3Temp() const { return string3_temp; }
    float getCrzPwrSetpt() const { return crz_pwr_setpt; }
    float getCrzSpdSetpt() const { return crz_spd_setpt; }
    float getSupplementalVoltage() const { return supplemental_voltage; }
    float getEstSupplementalSoc() const { return est_supplemental_soc; }
    std::string getState() const { return state; }
    float getLat() const { return lat; }
    float getLon() const { return lon; }
    float getElev() const { return elev; }
    
    const std::vector<float>& getCellGroupVoltages() const { return cell_group_voltages; }
private:
    bool checkRestartEnable();
    
    // Callback for data changes
    DataChangeCallback dataChangeCallback;
    
    // Threading control
    std::thread dataFetchThread, backendThread;
    std::atomic<bool> running{false};

    // TODO Include only the properties that need to be displayed on the driver dashboard
    uint8_t fan_speed, tstamp_hr, tstamp_mn, tstamp_sc;
    uint16_t tstamp_ms;
    float speed, accelerator_pedal, crz_spd_setpt, crz_pwr_setpt;
    float soc, est_supplemental_soc;
    float mppt_current_out;
    float pack_voltage, pack_current, supplemental_voltage, motor_power;
    float pack_temp, motor_temp, driverIO_temp, mainIO_temp, cabin_temp, motor_controller_temp;
    float string1_temp, string2_temp, string3_temp;
    float lat, lon, elev;
    bool headlights, l_turn_led_en, r_turn_led_en, hazards, mainIO_heartbeat, crz_pwr_mode, crz_spd_mode, eco, main_telem, parking_brake;
    bool eng_dash_commfail=1;
    std::string state;
    // Data for shutdown circuit
    // TODO Check initial values (should be nominal values, except for contactors, which should be open/false during restart)
    float bms_input_voltage;
    bool driver_eStop=false, external_eStop=false;
    bool crash=false;
    bool door= false;
    bool mcu_check=false;
    bool isolation=false;
    bool bps_fault=false;
    bool discharge_enable=false, charge_enable=false, bms_can_heartbeat=false;
    bool mcu_hv_en=false, mcu_stat_fdbk=false, use_dcdc=false, supplemental_valid=false, mppt_contactor=false, low_contactor=false, motor_controller_contactor=false;
    bool voltage_failsafe=false, current_failsafe=false, relay_failsafe=false, cell_balancing_active=true, charge_interlock_failsafe=false, thermistor_b_value_table_invalid=false, input_power_supply_failsafe=false;
    std::vector<float> cell_group_voltages;
    bool restart_enable=true;
    int mc_status=0;

    int cell_group_voltages_begin, cell_group_voltages_end; // First and last indices of the cell group voltages in data format

    std::vector<uint8_t> bytes;
    GPSData gpsOffset;
    std::vector<std::string> names;
    std::vector<int> byteNums;
    std::vector<std::string> types;
    std::mutex mutex;
    DataFetcher * fetcher;
    
    // Helper method to trigger data change callbacks
    void notifyDataChanged();
};


#endif //DATAGENERATOR_DATAUNPACKER_H
