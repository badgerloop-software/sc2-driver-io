#include "InfluxWriter.h"

#include <curl/curl.h>
#include <stdexcept>
#include <sstream>
#include <iomanip>
#include <cstdlib>
#include <numeric>
#include <vector>

// ─────────────────────────────────────────────────────────────────────────────
//  Constructor — load config from environment
// ─────────────────────────────────────────────────────────────────────────────

static std::string requireEnv(const char* name) {
    const char* v = std::getenv(name);
    if (!v || v[0] == '\0') {
        throw std::runtime_error(
            std::string("InfluxWriter: missing required env var: ") + name);
    }
    return std::string(v);
}

InfluxWriter::InfluxWriter()
    : url_   (requireEnv("INFLUX_URL"))
    , token_ (requireEnv("INFLUX_TOKEN"))
    , org_   (requireEnv("INFLUX_ORG"))
    , bucket_(requireEnv("INFLUX_BUCKET"))
{}

// ─────────────────────────────────────────────────────────────────────────────
//  toLineProtocol
// ─────────────────────────────────────────────────────────────────────────────

// Helper: append a float field to the stream.
// All numbers are written without integer 'i' suffix to avoid schema conflicts.
static void appendFloat(std::ostringstream& os, const char* key, double val, bool& first) {
    if (!first) os << ',';
    os << key << '=' << std::setprecision(6) << val;
    first = false;
}

// Helper: append a boolean field (true/false string form for InfluxDB).
static void appendBool(std::ostringstream& os, const char* key, bool val, bool& first) {
    if (!first) os << ',';
    os << key << '=' << (val ? "true" : "false");
    first = false;
}

std::string InfluxWriter::toLineProtocol(const TelemetryRecord& r,
                                         int64_t timestampNs) const {
    std::ostringstream os;
    os << std::fixed;

    // Measurement name (no spaces, no commas — safe as-is)
    os << "sc2_telemetry ";

    bool first = true;

    // ── MCC / Motor Control ──────────────────────────────────────────────────
    appendFloat(os, "accelerator_pedal",         r.accelerator_pedal,          first);
    appendFloat(os, "speed",                     r.speed,                      first);
    appendFloat(os, "mcc_state",                 r.mcc_state,                  first);
    appendBool (os, "fr_telem",                  r.fr_telem,                   first);
    appendBool (os, "crz_pwr_mode",              r.crz_pwr_mode,               first);
    appendBool (os, "crz_spd_mode",              r.crz_spd_mode,               first);
    appendFloat(os, "crz_pwr_setpt",             r.crz_pwr_setpt,              first);
    appendFloat(os, "crz_spd_setpt",             r.crz_spd_setpt,              first);
    appendBool (os, "eco",                       r.eco,                        first);
    appendBool (os, "main_telem",                r.main_telem,                 first);
    appendBool (os, "foot_brake",                r.foot_brake,                 first);
    appendFloat(os, "regen_brake",               r.regen_brake,                first);
    appendFloat(os, "motor_current",             r.motor_current,              first);
    appendFloat(os, "motor_power",               r.motor_power,                first);
    appendFloat(os, "mc_status",                 r.mc_status,                  first);

    // ── High Voltage / Shutdown ──────────────────────────────────────────────
    appendBool (os, "driver_eStop",              r.driver_eStop,               first);
    appendBool (os, "external_eStop",            r.external_eStop,             first);
    appendBool (os, "crash",                     r.crash,                      first);
    appendBool (os, "discharge_enable",          r.discharge_enable,           first);
    appendBool (os, "discharge_enabled",         r.discharge_enabled,          first);
    appendBool (os, "charge_enable",             r.charge_enable,              first);
    appendBool (os, "charge_enabled",            r.charge_enabled,             first);
    appendBool (os, "isolation",                 r.isolation,                  first);
    appendBool (os, "mcu_hv_en",                 r.mcu_hv_en,                  first);
    appendBool (os, "mcu_stat_fdbk",             r.mcu_stat_fdbk,              first);

    // ── High Voltage / MPS ──────────────────────────────────────────────────
    appendBool (os, "mppt_contactor",            r.mppt_contactor,             first);
    appendBool (os, "motor_controller_contactor",r.motor_controller_contactor, first);
    appendBool (os, "low_contactor",             r.low_contactor,              first);
    appendFloat(os, "dcdc_current",              r.dcdc_current,               first);
    appendBool (os, "dcdc_deg",                  r.dcdc_deg,                   first);
    appendBool (os, "use_dcdc",                  r.use_dcdc,                   first);
    appendBool (os, "use_supp",                  r.use_supp,                   first);
    appendBool (os, "bms_mpio1",                 r.bms_mpio1,                  first);

    // ── Battery / Supplemental ───────────────────────────────────────────────
    appendFloat(os, "supplemental_current",      r.supplemental_current,       first);
    appendFloat(os, "supplemental_voltage",      r.supplemental_voltage,       first);
    appendBool (os, "supplemental_deg",          r.supplemental_deg,           first);
    appendFloat(os, "est_supplemental_soc",      r.est_supplemental_soc,       first);

    // ── Main IO / Sensors ────────────────────────────────────────────────────
    appendBool (os, "park_brake",                r.park_brake,                 first);
    appendFloat(os, "air_temp",                  r.air_temp,                   first);
    appendFloat(os, "brake_temp",                r.brake_temp,                 first);
    appendFloat(os, "dcdc_temp",                 r.dcdc_temp,                  first);
    appendFloat(os, "mainIO_temp",               r.mainIO_temp,                first);
    appendFloat(os, "motor_controller_temp",     r.motor_controller_temp,      first);
    appendFloat(os, "motor_temp",                r.motor_temp,                 first);
    appendFloat(os, "road_temp",                 r.road_temp,                  first);

    // ── Main IO / Lights ─────────────────────────────────────────────────────
    appendBool (os, "l_turn_led_en",             r.l_turn_led_en,              first);
    appendBool (os, "r_turn_led_en",             r.r_turn_led_en,              first);
    appendBool (os, "brake_led_en",              r.brake_led_en,               first);
    appendBool (os, "headlights_led_en",         r.headlights_led_en,          first);
    appendBool (os, "hazards",                   r.hazards,                    first);

    // ── Main IO / Power Bus ──────────────────────────────────────────────────
    appendFloat(os, "main_5V_bus",               r.main_5V_bus,                first);
    appendFloat(os, "main_12V_bus",              r.main_12V_bus,               first);
    appendFloat(os, "main_24V_bus",              r.main_24V_bus,               first);
    appendFloat(os, "main_5V_current",           r.main_5V_current,            first);
    appendFloat(os, "main_12V_current",          r.main_12V_current,           first);
    appendFloat(os, "main_24V_current",          r.main_24V_current,           first);

    // ── Main IO / Firmware Heartbeats ────────────────────────────────────────
    appendBool (os, "bms_can_heartbeat",         r.bms_can_heartbeat,          first);
    appendBool (os, "hv_can_heartbeat",          r.hv_can_heartbeat,           first);
    appendBool (os, "mainIO_heartbeat",          r.mainIO_heartbeat,           first);
    appendBool (os, "mcc_can_heartbeat",         r.mcc_can_heartbeat,          first);
    appendBool (os, "mppt_can_heartbeat",        r.mppt_can_heartbeat,         first);

    // ── Solar / MPPT ─────────────────────────────────────────────────────────
    appendBool (os, "mppt_mode",                 r.mppt_mode,                  first);
    appendFloat(os, "mppt_current_out",          r.mppt_current_out,           first);
    appendFloat(os, "mppt_power_out",            r.mppt_power_out,             first);
    appendFloat(os, "string1_temp",              r.string1_temp,               first);
    appendFloat(os, "string2_temp",              r.string2_temp,               first);
    appendFloat(os, "string3_temp",              r.string3_temp,               first);
    appendFloat(os, "string1_V_in",              r.string1_V_in,               first);
    appendFloat(os, "string2_V_in",              r.string2_V_in,               first);
    appendFloat(os, "string3_V_in",              r.string3_V_in,               first);
    appendFloat(os, "string1_I_in",              r.string1_I_in,               first);
    appendFloat(os, "string2_I_in",              r.string2_I_in,               first);
    appendFloat(os, "string3_I_in",              r.string3_I_in,               first);

    // ── Battery / BMS CAN ────────────────────────────────────────────────────
    appendFloat(os, "pack_temp",                 r.pack_temp,                  first);
    appendFloat(os, "pack_internal_temp",        r.pack_internal_temp,         first);
    appendFloat(os, "pack_current",              r.pack_current,               first);
    appendFloat(os, "pack_voltage",              r.pack_voltage,               first);
    appendFloat(os, "pack_power",                r.pack_power,                 first);
    appendFloat(os, "populated_cells",           r.populated_cells,            first);
    appendFloat(os, "soc",                       r.soc,                        first);
    appendFloat(os, "soh",                       r.soh,                        first);
    appendFloat(os, "pack_amphours",             r.pack_amphours,              first);
    appendFloat(os, "adaptive_total_capacity",   r.adaptive_total_capacity,    first);
    appendFloat(os, "fan_speed",                 r.fan_speed,                  first);
    appendFloat(os, "pack_resistance",           r.pack_resistance,            first);
    appendFloat(os, "bms_input_voltage",         r.bms_input_voltage,          first);

    // ── Battery / BMS Faults ─────────────────────────────────────────────────
    appendBool (os, "bps_fault",                               r.bps_fault,                               first);
    appendBool (os, "voltage_failsafe",                        r.voltage_failsafe,                        first);
    appendBool (os, "current_failsafe",                        r.current_failsafe,                        first);
    appendBool (os, "relay_failsafe",                          r.relay_failsafe,                          first);
    appendBool (os, "cell_balancing_active",                   r.cell_balancing_active,                   first);
    appendBool (os, "charge_interlock_failsafe",               r.charge_interlock_failsafe,               first);
    appendBool (os, "thermistor_b_value_table_invalid",        r.thermistor_b_value_table_invalid,        first);
    appendBool (os, "input_power_supply_failsafe",             r.input_power_supply_failsafe,             first);
    appendBool (os, "discharge_limit_enforcement_fault",       r.discharge_limit_enforcement_fault,       first);
    appendBool (os, "charger_safety_relay_fault",              r.charger_safety_relay_fault,              first);
    appendBool (os, "internal_hardware_fault",                 r.internal_hardware_fault,                 first);
    appendBool (os, "internal_heatsink_fault",                 r.internal_heatsink_fault,                 first);
    appendBool (os, "internal_software_fault",                 r.internal_software_fault,                 first);
    appendBool (os, "highest_cell_voltage_too_high_fault",     r.highest_cell_voltage_too_high_fault,     first);
    appendBool (os, "lowest_cell_voltage_too_low_fault",       r.lowest_cell_voltage_too_low_fault,       first);
    appendBool (os, "pack_too_hot_fault",                      r.pack_too_hot_fault,                      first);
    appendBool (os, "high_voltage_interlock_signal_fault",     r.high_voltage_interlock_signal_fault,     first);
    appendBool (os, "precharge_circuit_malfunction",           r.precharge_circuit_malfunction,           first);
    appendBool (os, "abnormal_state_of_charge_behavior",       r.abnormal_state_of_charge_behavior,       first);
    appendBool (os, "internal_communication_fault",            r.internal_communication_fault,            first);
    appendBool (os, "cell_balancing_stuck_off_fault",          r.cell_balancing_stuck_off_fault,          first);
    appendBool (os, "weak_cell_fault",                         r.weak_cell_fault,                         first);
    appendBool (os, "low_cell_voltage_fault",                  r.low_cell_voltage_fault,                  first);
    appendBool (os, "open_wiring_fault",                       r.open_wiring_fault,                       first);
    appendBool (os, "current_sensor_fault",                    r.current_sensor_fault,                    first);
    appendBool (os, "highest_cell_voltage_over_5V_fault",      r.highest_cell_voltage_over_5V_fault,      first);
    appendBool (os, "cell_asic_fault",                         r.cell_asic_fault,                         first);
    appendBool (os, "weak_pack_fault",                         r.weak_pack_fault,                         first);
    appendBool (os, "fan_monitor_fault",                       r.fan_monitor_fault,                       first);
    appendBool (os, "thermistor_fault",                        r.thermistor_fault,                        first);
    appendBool (os, "external_communication_fault",            r.external_communication_fault,            first);
    appendBool (os, "redundant_power_supply_fault",            r.redundant_power_supply_fault,            first);
    appendBool (os, "high_voltage_isolation_fault",            r.high_voltage_isolation_fault,            first);
    appendBool (os, "input_power_supply_fault",                r.input_power_supply_fault,                first);
    appendBool (os, "charge_limit_enforcement_fault",          r.charge_limit_enforcement_fault,          first);

    // ── Battery / Cell Group Voltages ────────────────────────────────────────
    appendFloat(os, "cell_group1_voltage",  r.cell_group1_voltage,  first);
    appendFloat(os, "cell_group2_voltage",  r.cell_group2_voltage,  first);
    appendFloat(os, "cell_group3_voltage",  r.cell_group3_voltage,  first);
    appendFloat(os, "cell_group4_voltage",  r.cell_group4_voltage,  first);
    appendFloat(os, "cell_group5_voltage",  r.cell_group5_voltage,  first);
    appendFloat(os, "cell_group6_voltage",  r.cell_group6_voltage,  first);
    appendFloat(os, "cell_group7_voltage",  r.cell_group7_voltage,  first);
    appendFloat(os, "cell_group8_voltage",  r.cell_group8_voltage,  first);
    appendFloat(os, "cell_group9_voltage",  r.cell_group9_voltage,  first);
    appendFloat(os, "cell_group10_voltage", r.cell_group10_voltage, first);
    appendFloat(os, "cell_group11_voltage", r.cell_group11_voltage, first);
    appendFloat(os, "cell_group12_voltage", r.cell_group12_voltage, first);
    appendFloat(os, "cell_group13_voltage", r.cell_group13_voltage, first);
    appendFloat(os, "cell_group14_voltage", r.cell_group14_voltage, first);
    appendFloat(os, "cell_group15_voltage", r.cell_group15_voltage, first);
    appendFloat(os, "cell_group16_voltage", r.cell_group16_voltage, first);
    appendFloat(os, "cell_group17_voltage", r.cell_group17_voltage, first);
    appendFloat(os, "cell_group18_voltage", r.cell_group18_voltage, first);
    appendFloat(os, "cell_group19_voltage", r.cell_group19_voltage, first);
    appendFloat(os, "cell_group20_voltage", r.cell_group20_voltage, first);
    appendFloat(os, "cell_group21_voltage", r.cell_group21_voltage, first);
    appendFloat(os, "cell_group22_voltage", r.cell_group22_voltage, first);
    appendFloat(os, "cell_group23_voltage", r.cell_group23_voltage, first);
    appendFloat(os, "cell_group24_voltage", r.cell_group24_voltage, first);
    appendFloat(os, "cell_group25_voltage", r.cell_group25_voltage, first);
    appendFloat(os, "cell_group26_voltage", r.cell_group26_voltage, first);
    appendFloat(os, "cell_group27_voltage", r.cell_group27_voltage, first);
    appendFloat(os, "cell_group28_voltage", r.cell_group28_voltage, first);
    appendFloat(os, "cell_group29_voltage", r.cell_group29_voltage, first);
    appendFloat(os, "cell_group30_voltage", r.cell_group30_voltage, first);
    appendFloat(os, "cell_group31_voltage", r.cell_group31_voltage, first);

    // ── Software / Timestamps ────────────────────────────────────────────────
    appendFloat(os, "tstamp_ms",   r.tstamp_ms,   first);
    appendFloat(os, "tstamp_sc",   r.tstamp_sc,   first);
    appendFloat(os, "tstamp_mn",   r.tstamp_mn,   first);
    appendFloat(os, "tstamp_hr",   r.tstamp_hr,   first);
    appendFloat(os, "tstamp_unix", static_cast<double>(r.tstamp_unix), first);

    // ── Software / GPS ───────────────────────────────────────────────────────
    appendFloat(os, "lat",  r.lat,  first);
    appendFloat(os, "lon",  r.lon,  first);
    appendFloat(os, "elev", r.elev, first);

    // ── Software / Lap ───────────────────────────────────────────────────────
    appendFloat(os, "lap_count",       r.lap_count,       first);
    appendFloat(os, "current_section", r.current_section, first);
    appendFloat(os, "lap_duration",    r.lap_duration,    first);

    // ── Race Strategy ────────────────────────────────────────────────────────
    appendFloat(os, "optimized_target_power",    r.optimized_target_power,    first);
    appendFloat(os, "maximum_distance_traveled", r.maximum_distance_traveled, first);

    // Optional nanosecond timestamp
    if (timestampNs != 0) {
        os << ' ' << timestampNs;
    }

    return os.str();
}

// ─────────────────────────────────────────────────────────────────────────────
//  Public write helpers
// ─────────────────────────────────────────────────────────────────────────────

void InfluxWriter::write(const std::string& lineProtocol) const {
    httpPost(lineProtocol);
}

void InfluxWriter::writeBatch(const std::vector<std::string>& lines) const {
    if (lines.empty()) return;
    std::string body;
    for (size_t i = 0; i < lines.size(); ++i) {
        body += lines[i];
        if (i + 1 < lines.size()) body += '\n';
    }
    httpPost(body);
}

// ─────────────────────────────────────────────────────────────────────────────
//  libcurl HTTP POST
// ─────────────────────────────────────────────────────────────────────────────

// Collects the HTTP response body so we can surface error messages.
static size_t curlWriteCallback(char* ptr, size_t size, size_t nmemb, void* userdata) {
    std::string* out = static_cast<std::string*>(userdata);
    out->append(ptr, size * nmemb);
    return size * nmemb;
}

void InfluxWriter::httpPost(const std::string& body) const {
    // Build endpoint URL
    std::string endpoint = url_
        + "/api/v2/write?org=" + org_
        + "&bucket="           + bucket_
        + "&precision=ns";

    CURL* curl = curl_easy_init();
    if (!curl) {
        throw std::runtime_error("InfluxWriter: curl_easy_init() failed");
    }

    std::string responseBody;
    struct curl_slist* headers = nullptr;

    std::string authHeader = "Authorization: Token " + token_;
    headers = curl_slist_append(headers, authHeader.c_str());
    headers = curl_slist_append(headers, "Content-Type: text/plain; charset=utf-8");

    curl_easy_setopt(curl, CURLOPT_URL,            endpoint.c_str());
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER,     headers);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS,     body.c_str());
    curl_easy_setopt(curl, CURLOPT_POSTFIELDSIZE,  static_cast<long>(body.size()));
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION,  curlWriteCallback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA,      &responseBody);

    CURLcode res = curl_easy_perform(curl);

    if (res != CURLE_OK) {
        std::string err = curl_easy_strerror(res);
        curl_slist_free_all(headers);
        curl_easy_cleanup(curl);
        throw std::runtime_error("InfluxWriter: curl error: " + err);
    }

    long httpCode = 0;
    curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &httpCode);
    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);

    // InfluxDB returns 204 No Content on success
    if (httpCode < 200 || httpCode >= 300) {
        throw std::runtime_error(
            "InfluxWriter: HTTP " + std::to_string(httpCode) + ": " + responseBody);
    }
}
