#include "CsvParser.h"

#include <fstream>
#include <sstream>
#include <stdexcept>
#include <algorithm>
#include <cctype>

// ─────────────────────────────────────────────────────────────────────────────
//  Public entry point
// ─────────────────────────────────────────────────────────────────────────────

std::vector<TelemetryRecord> CsvParser::parse(const std::string& filePath) {
    std::ifstream file(filePath);
    if (!file.is_open()) {
        throw std::runtime_error("CsvParser: cannot open file: " + filePath);
    }

    std::vector<TelemetryRecord> records;
    std::string line;

    // ── Header row ───────────────────────────────────────────────────────────
    if (!std::getline(file, line)) {
        return records;  // empty file
    }
    std::vector<std::string> headers = splitLine(line);

    // ── Data rows ────────────────────────────────────────────────────────────
    while (std::getline(file, line)) {
        if (line.empty()) continue;

        std::vector<std::string> values = splitLine(line);
        TelemetryRecord rec;

        size_t count = std::min(headers.size(), values.size());
        for (size_t i = 0; i < count; ++i) {
            applyField(rec, headers[i], values[i]);
        }
        records.push_back(rec);
    }

    return records;
}

// ─────────────────────────────────────────────────────────────────────────────
//  Private helpers
// ─────────────────────────────────────────────────────────────────────────────

std::vector<std::string> CsvParser::splitLine(const std::string& line) {
    std::vector<std::string> fields;
    std::string field;
    bool inQuotes = false;

    for (size_t i = 0; i < line.size(); ++i) {
        char c = line[i];
        if (c == '"') {
            if (inQuotes && i + 1 < line.size() && line[i + 1] == '"') {
                field += '"';
                ++i;  // skip escaped quote
            } else {
                inQuotes = !inQuotes;
            }
        } else if (c == ',' && !inQuotes) {
            fields.push_back(field);
            field.clear();
        } else {
            field += c;
        }
    }
    fields.push_back(field);  // last field
    return fields;
}

double CsvParser::toDouble(const std::string& s, double fallback) {
    if (s.empty()) return fallback;
    try { return std::stod(s); } catch (...) { return fallback; }
}

bool CsvParser::toBool(const std::string& s, bool fallback) {
    if (s.empty()) return fallback;
    std::string lower = s;
    std::transform(lower.begin(), lower.end(), lower.begin(), ::tolower);
    if (lower == "true"  || lower == "1" || lower == "yes") return true;
    if (lower == "false" || lower == "0" || lower == "no")  return false;
    return fallback;
}

int64_t CsvParser::toInt64(const std::string& s, int64_t fallback) {
    if (s.empty()) return fallback;
    try { return static_cast<int64_t>(std::stoll(s)); } catch (...) { return fallback; }
}

// ─────────────────────────────────────────────────────────────────────────────
//  Field mapping  (header name → struct member)
// ─────────────────────────────────────────────────────────────────────────────

void CsvParser::applyField(TelemetryRecord& r,
                           const std::string& name,
                           const std::string& value) {
    // ── MCC / Motor Control ──────────────────────────────────────────────────
    if (name == "accelerator_pedal")           { r.accelerator_pedal           = toDouble(value); return; }
    if (name == "speed")                       { r.speed                       = toDouble(value); return; }
    if (name == "mcc_state")                   { r.mcc_state                   = static_cast<uint8_t>(toInt64(value)); return; }
    if (name == "fr_telem")                    { r.fr_telem                    = toBool(value); return; }
    if (name == "crz_pwr_mode")                { r.crz_pwr_mode                = toBool(value); return; }
    if (name == "crz_spd_mode")                { r.crz_spd_mode                = toBool(value); return; }
    if (name == "crz_pwr_setpt")               { r.crz_pwr_setpt               = toDouble(value); return; }
    if (name == "crz_spd_setpt")               { r.crz_spd_setpt               = toDouble(value); return; }
    if (name == "eco")                         { r.eco                         = toBool(value); return; }
    if (name == "main_telem")                  { r.main_telem                  = toBool(value); return; }
    if (name == "foot_brake")                  { r.foot_brake                  = toBool(value); return; }
    if (name == "regen_brake")                 { r.regen_brake                 = toDouble(value); return; }
    if (name == "motor_current")               { r.motor_current               = toDouble(value); return; }
    if (name == "motor_power")                 { r.motor_power                 = toDouble(value); return; }
    if (name == "mc_status")                   { r.mc_status                   = static_cast<uint8_t>(toInt64(value)); return; }

    // ── High Voltage / Shutdown ──────────────────────────────────────────────
    if (name == "driver_eStop")                { r.driver_eStop                = toBool(value); return; }
    if (name == "external_eStop")              { r.external_eStop              = toBool(value); return; }
    if (name == "crash")                       { r.crash                       = toBool(value); return; }
    if (name == "discharge_enable")            { r.discharge_enable            = toBool(value); return; }
    if (name == "discharge_enabled")           { r.discharge_enabled           = toBool(value); return; }
    if (name == "charge_enable")               { r.charge_enable               = toBool(value); return; }
    if (name == "charge_enabled")              { r.charge_enabled              = toBool(value); return; }
    if (name == "isolation")                   { r.isolation                   = toBool(value); return; }
    if (name == "mcu_hv_en")                   { r.mcu_hv_en                   = toBool(value); return; }
    if (name == "mcu_stat_fdbk")               { r.mcu_stat_fdbk               = toBool(value); return; }

    // ── High Voltage / MPS ──────────────────────────────────────────────────
    if (name == "mppt_contactor")              { r.mppt_contactor              = toBool(value); return; }
    if (name == "motor_controller_contactor")  { r.motor_controller_contactor  = toBool(value); return; }
    if (name == "low_contactor")               { r.low_contactor               = toBool(value); return; }
    if (name == "dcdc_current")                { r.dcdc_current                = toDouble(value); return; }
    if (name == "dcdc_deg")                    { r.dcdc_deg                    = toBool(value); return; }
    if (name == "use_dcdc")                    { r.use_dcdc                    = toBool(value); return; }
    if (name == "use_supp")                    { r.use_supp                    = toBool(value); return; }
    if (name == "bms_mpio1")                   { r.bms_mpio1                   = toBool(value); return; }

    // ── Battery / Supplemental ───────────────────────────────────────────────
    if (name == "supplemental_current")        { r.supplemental_current        = toDouble(value); return; }
    if (name == "supplemental_voltage")        { r.supplemental_voltage        = toDouble(value); return; }
    if (name == "supplemental_deg")            { r.supplemental_deg            = toBool(value); return; }
    if (name == "est_supplemental_soc")        { r.est_supplemental_soc        = toDouble(value); return; }

    // ── Main IO / Sensors ────────────────────────────────────────────────────
    if (name == "park_brake")                  { r.park_brake                  = toBool(value); return; }
    if (name == "air_temp")                    { r.air_temp                    = toDouble(value); return; }
    if (name == "brake_temp")                  { r.brake_temp                  = toDouble(value); return; }
    if (name == "dcdc_temp")                   { r.dcdc_temp                   = toDouble(value); return; }
    if (name == "mainIO_temp")                 { r.mainIO_temp                 = toDouble(value); return; }
    if (name == "motor_controller_temp")       { r.motor_controller_temp       = toDouble(value); return; }
    if (name == "motor_temp")                  { r.motor_temp                  = toDouble(value); return; }
    if (name == "road_temp")                   { r.road_temp                   = toDouble(value); return; }

    // ── Main IO / Lights ─────────────────────────────────────────────────────
    if (name == "l_turn_led_en")               { r.l_turn_led_en               = toBool(value); return; }
    if (name == "r_turn_led_en")               { r.r_turn_led_en               = toBool(value); return; }
    if (name == "brake_led_en")                { r.brake_led_en                = toBool(value); return; }
    if (name == "headlights_led_en")           { r.headlights_led_en           = toBool(value); return; }
    if (name == "hazards")                     { r.hazards                     = toBool(value); return; }

    // ── Main IO / Power Bus ──────────────────────────────────────────────────
    if (name == "main_5V_bus")                 { r.main_5V_bus                 = toDouble(value); return; }
    if (name == "main_12V_bus")                { r.main_12V_bus                = toDouble(value); return; }
    if (name == "main_24V_bus")                { r.main_24V_bus                = toDouble(value); return; }
    if (name == "main_5V_current")             { r.main_5V_current             = toDouble(value); return; }
    if (name == "main_12V_current")            { r.main_12V_current            = toDouble(value); return; }
    if (name == "main_24V_current")            { r.main_24V_current            = toDouble(value); return; }

    // ── Main IO / Firmware Heartbeats ────────────────────────────────────────
    if (name == "bms_can_heartbeat")           { r.bms_can_heartbeat           = toBool(value); return; }
    if (name == "hv_can_heartbeat")            { r.hv_can_heartbeat            = toBool(value); return; }
    if (name == "mainIO_heartbeat")            { r.mainIO_heartbeat            = toBool(value); return; }
    if (name == "mcc_can_heartbeat")           { r.mcc_can_heartbeat           = toBool(value); return; }
    if (name == "mppt_can_heartbeat")          { r.mppt_can_heartbeat          = toBool(value); return; }

    // ── Solar / MPPT ─────────────────────────────────────────────────────────
    if (name == "mppt_mode")                   { r.mppt_mode                   = toBool(value); return; }
    if (name == "mppt_current_out")            { r.mppt_current_out            = toDouble(value); return; }
    if (name == "mppt_power_out")              { r.mppt_power_out              = toDouble(value); return; }
    if (name == "string1_temp")                { r.string1_temp                = toDouble(value); return; }
    if (name == "string2_temp")                { r.string2_temp                = toDouble(value); return; }
    if (name == "string3_temp")                { r.string3_temp                = toDouble(value); return; }
    if (name == "string1_V_in")                { r.string1_V_in                = toDouble(value); return; }
    if (name == "string2_V_in")                { r.string2_V_in                = toDouble(value); return; }
    if (name == "string3_V_in")                { r.string3_V_in                = toDouble(value); return; }
    if (name == "string1_I_in")                { r.string1_I_in                = toDouble(value); return; }
    if (name == "string2_I_in")                { r.string2_I_in                = toDouble(value); return; }
    if (name == "string3_I_in")                { r.string3_I_in                = toDouble(value); return; }

    // ── Battery / BMS CAN ────────────────────────────────────────────────────
    if (name == "pack_temp")                   { r.pack_temp                   = toDouble(value); return; }
    if (name == "pack_internal_temp")          { r.pack_internal_temp          = toDouble(value); return; }
    if (name == "pack_current")                { r.pack_current                = toDouble(value); return; }
    if (name == "pack_voltage")                { r.pack_voltage                = toDouble(value); return; }
    if (name == "pack_power")                  { r.pack_power                  = toDouble(value); return; }
    if (name == "populated_cells")             { r.populated_cells             = static_cast<uint16_t>(toInt64(value)); return; }
    if (name == "soc")                         { r.soc                         = toDouble(value); return; }
    if (name == "soh")                         { r.soh                         = toDouble(value); return; }
    if (name == "pack_amphours")               { r.pack_amphours               = toDouble(value); return; }
    if (name == "adaptive_total_capacity")     { r.adaptive_total_capacity     = toDouble(value); return; }
    if (name == "fan_speed")                   { r.fan_speed                   = static_cast<uint8_t>(toInt64(value)); return; }
    if (name == "pack_resistance")             { r.pack_resistance             = toDouble(value); return; }
    if (name == "bms_input_voltage")           { r.bms_input_voltage           = toDouble(value); return; }

    // ── Battery / BMS Faults ─────────────────────────────────────────────────
    if (name == "bps_fault")                                 { r.bps_fault                                 = toBool(value); return; }
    if (name == "voltage_failsafe")                          { r.voltage_failsafe                          = toBool(value); return; }
    if (name == "current_failsafe")                          { r.current_failsafe                          = toBool(value); return; }
    if (name == "relay_failsafe")                            { r.relay_failsafe                            = toBool(value); return; }
    if (name == "cell_balancing_active")                     { r.cell_balancing_active                     = toBool(value); return; }
    if (name == "charge_interlock_failsafe")                 { r.charge_interlock_failsafe                 = toBool(value); return; }
    if (name == "thermistor_b_value_table_invalid")          { r.thermistor_b_value_table_invalid          = toBool(value); return; }
    if (name == "input_power_supply_failsafe")               { r.input_power_supply_failsafe               = toBool(value); return; }
    if (name == "discharge_limit_enforcement_fault")         { r.discharge_limit_enforcement_fault         = toBool(value); return; }
    if (name == "charger_safety_relay_fault")                { r.charger_safety_relay_fault                = toBool(value); return; }
    if (name == "internal_hardware_fault")                   { r.internal_hardware_fault                   = toBool(value); return; }
    if (name == "internal_heatsink_fault")                   { r.internal_heatsink_fault                   = toBool(value); return; }
    if (name == "internal_software_fault")                   { r.internal_software_fault                   = toBool(value); return; }
    if (name == "highest_cell_voltage_too_high_fault")       { r.highest_cell_voltage_too_high_fault       = toBool(value); return; }
    if (name == "lowest_cell_voltage_too_low_fault")         { r.lowest_cell_voltage_too_low_fault         = toBool(value); return; }
    if (name == "pack_too_hot_fault")                        { r.pack_too_hot_fault                        = toBool(value); return; }
    if (name == "high_voltage_interlock_signal_fault")       { r.high_voltage_interlock_signal_fault       = toBool(value); return; }
    if (name == "precharge_circuit_malfunction")             { r.precharge_circuit_malfunction             = toBool(value); return; }
    if (name == "abnormal_state_of_charge_behavior")         { r.abnormal_state_of_charge_behavior         = toBool(value); return; }
    if (name == "internal_communication_fault")              { r.internal_communication_fault              = toBool(value); return; }
    if (name == "cell_balancing_stuck_off_fault")            { r.cell_balancing_stuck_off_fault            = toBool(value); return; }
    if (name == "weak_cell_fault")                           { r.weak_cell_fault                           = toBool(value); return; }
    if (name == "low_cell_voltage_fault")                    { r.low_cell_voltage_fault                    = toBool(value); return; }
    if (name == "open_wiring_fault")                         { r.open_wiring_fault                         = toBool(value); return; }
    if (name == "current_sensor_fault")                      { r.current_sensor_fault                      = toBool(value); return; }
    if (name == "highest_cell_voltage_over_5V_fault")        { r.highest_cell_voltage_over_5V_fault        = toBool(value); return; }
    if (name == "cell_asic_fault")                           { r.cell_asic_fault                           = toBool(value); return; }
    if (name == "weak_pack_fault")                           { r.weak_pack_fault                           = toBool(value); return; }
    if (name == "fan_monitor_fault")                         { r.fan_monitor_fault                         = toBool(value); return; }
    if (name == "thermistor_fault")                          { r.thermistor_fault                          = toBool(value); return; }
    if (name == "external_communication_fault")              { r.external_communication_fault              = toBool(value); return; }
    if (name == "redundant_power_supply_fault")              { r.redundant_power_supply_fault              = toBool(value); return; }
    if (name == "high_voltage_isolation_fault")              { r.high_voltage_isolation_fault              = toBool(value); return; }
    if (name == "input_power_supply_fault")                  { r.input_power_supply_fault                  = toBool(value); return; }
    if (name == "charge_limit_enforcement_fault")            { r.charge_limit_enforcement_fault            = toBool(value); return; }

    // ── Battery / Cell Group Voltages ────────────────────────────────────────
    if (name == "cell_group1_voltage")    { r.cell_group1_voltage    = toDouble(value); return; }
    if (name == "cell_group2_voltage")    { r.cell_group2_voltage    = toDouble(value); return; }
    if (name == "cell_group3_voltage")    { r.cell_group3_voltage    = toDouble(value); return; }
    if (name == "cell_group4_voltage")    { r.cell_group4_voltage    = toDouble(value); return; }
    if (name == "cell_group5_voltage")    { r.cell_group5_voltage    = toDouble(value); return; }
    if (name == "cell_group6_voltage")    { r.cell_group6_voltage    = toDouble(value); return; }
    if (name == "cell_group7_voltage")    { r.cell_group7_voltage    = toDouble(value); return; }
    if (name == "cell_group8_voltage")    { r.cell_group8_voltage    = toDouble(value); return; }
    if (name == "cell_group9_voltage")    { r.cell_group9_voltage    = toDouble(value); return; }
    if (name == "cell_group10_voltage")   { r.cell_group10_voltage   = toDouble(value); return; }
    if (name == "cell_group11_voltage")   { r.cell_group11_voltage   = toDouble(value); return; }
    if (name == "cell_group12_voltage")   { r.cell_group12_voltage   = toDouble(value); return; }
    if (name == "cell_group13_voltage")   { r.cell_group13_voltage   = toDouble(value); return; }
    if (name == "cell_group14_voltage")   { r.cell_group14_voltage   = toDouble(value); return; }
    if (name == "cell_group15_voltage")   { r.cell_group15_voltage   = toDouble(value); return; }
    if (name == "cell_group16_voltage")   { r.cell_group16_voltage   = toDouble(value); return; }
    if (name == "cell_group17_voltage")   { r.cell_group17_voltage   = toDouble(value); return; }
    if (name == "cell_group18_voltage")   { r.cell_group18_voltage   = toDouble(value); return; }
    if (name == "cell_group19_voltage")   { r.cell_group19_voltage   = toDouble(value); return; }
    if (name == "cell_group20_voltage")   { r.cell_group20_voltage   = toDouble(value); return; }
    if (name == "cell_group21_voltage")   { r.cell_group21_voltage   = toDouble(value); return; }
    if (name == "cell_group22_voltage")   { r.cell_group22_voltage   = toDouble(value); return; }
    if (name == "cell_group23_voltage")   { r.cell_group23_voltage   = toDouble(value); return; }
    if (name == "cell_group24_voltage")   { r.cell_group24_voltage   = toDouble(value); return; }
    if (name == "cell_group25_voltage")   { r.cell_group25_voltage   = toDouble(value); return; }
    if (name == "cell_group26_voltage")   { r.cell_group26_voltage   = toDouble(value); return; }
    if (name == "cell_group27_voltage")   { r.cell_group27_voltage   = toDouble(value); return; }
    if (name == "cell_group28_voltage")   { r.cell_group28_voltage   = toDouble(value); return; }
    if (name == "cell_group29_voltage")   { r.cell_group29_voltage   = toDouble(value); return; }
    if (name == "cell_group30_voltage")   { r.cell_group30_voltage   = toDouble(value); return; }
    if (name == "cell_group31_voltage")   { r.cell_group31_voltage   = toDouble(value); return; }

    // ── Software / Timestamps ────────────────────────────────────────────────
    if (name == "tstamp_ms")               { r.tstamp_ms               = static_cast<uint16_t>(toInt64(value)); return; }
    if (name == "tstamp_sc")               { r.tstamp_sc               = static_cast<uint8_t> (toInt64(value)); return; }
    if (name == "tstamp_mn")               { r.tstamp_mn               = static_cast<uint8_t> (toInt64(value)); return; }
    if (name == "tstamp_hr")               { r.tstamp_hr               = static_cast<uint8_t> (toInt64(value)); return; }
    if (name == "tstamp_unix")             { r.tstamp_unix             = static_cast<uint64_t>(toInt64(value)); return; }

    // ── Software / GPS ───────────────────────────────────────────────────────
    if (name == "lat")                     { r.lat                     = toDouble(value); return; }
    if (name == "lon")                     { r.lon                     = toDouble(value); return; }
    if (name == "elev")                    { r.elev                    = toDouble(value); return; }

    // ── Software / Lap Counter ───────────────────────────────────────────────
    if (name == "lap_count")               { r.lap_count               = static_cast<int32_t> (toInt64(value)); return; }
    if (name == "current_section")         { r.current_section         = static_cast<int32_t> (toInt64(value)); return; }
    if (name == "lap_duration")            { r.lap_duration            = static_cast<uint32_t>(toInt64(value)); return; }

    // ── Race Strategy ────────────────────────────────────────────────────────
    if (name == "optimized_target_power")  { r.optimized_target_power  = toDouble(value); return; }
    if (name == "maximum_distance_traveled"){ r.maximum_distance_traveled = toDouble(value); return; }

    // Unknown column — silently ignored.
}
