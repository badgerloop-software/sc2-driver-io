#pragma once
#include <cstdint>
#include <string>

/**
 * TelemetryRecord
 *
 * Mirrors the full signal set defined in data/data_format.json.
 * Field types match the data_format spec:
 *   float  → double  (4-byte float fields)
 *   bool   → bool
 *   uint8  → uint8_t
 *   uint16 → uint16_t
 *   uint32 → uint32_t
 *   uint64 → uint64_t
 *   int32  → int32_t
 *
 * Default values are set to the "expected" safe state from data_format.json
 * (the min value for most fields, max for contactors/heartbeats).
 */
struct TelemetryRecord {

    // ── MCC / Motor Control ───────────────────────────────────────────────────
    double   accelerator_pedal          = 0.0;
    double   speed                      = 0.0;
    uint8_t  mcc_state                  = 0;
    bool     fr_telem                   = false;
    bool     crz_pwr_mode               = false;
    bool     crz_spd_mode               = false;
    double   crz_pwr_setpt              = 0.0;
    double   crz_spd_setpt              = 0.0;
    bool     eco                        = false;
    bool     main_telem                 = false;
    bool     foot_brake                 = false;
    double   regen_brake                = 0.0;
    double   motor_current              = 0.0;
    double   motor_power                = 0.0;
    uint8_t  mc_status                  = 0;

    // ── High Voltage / Shutdown ───────────────────────────────────────────────
    bool     driver_eStop               = false;
    bool     external_eStop             = false;
    bool     crash                      = false;
    bool     discharge_enable           = false;
    bool     discharge_enabled          = false;
    bool     charge_enable              = false;
    bool     charge_enabled             = false;
    bool     isolation                  = false;
    bool     mcu_hv_en                  = false;
    bool     mcu_stat_fdbk              = false;

    // ── High Voltage / MPS ───────────────────────────────────────────────────
    bool     mppt_contactor             = true;
    bool     motor_controller_contactor = true;
    bool     low_contactor              = true;
    double   dcdc_current               = 0.0;
    bool     dcdc_deg                   = true;
    bool     use_dcdc                   = false;
    bool     use_supp                   = false;
    bool     bms_mpio1                  = false;

    // ── Battery / Supplemental ────────────────────────────────────────────────
    double   supplemental_current       = 0.0;
    double   supplemental_voltage       = 0.0;
    bool     supplemental_deg           = true;
    double   est_supplemental_soc       = 0.0;

    // ── Main IO / Sensors ─────────────────────────────────────────────────────
    bool     park_brake                 = false;
    double   air_temp                   = 0.0;
    double   brake_temp                 = 0.0;
    double   dcdc_temp                  = 0.0;
    double   mainIO_temp                = 0.0;
    double   motor_controller_temp      = 0.0;
    double   motor_temp                 = 0.0;
    double   road_temp                  = 0.0;

    // ── Main IO / Lights ──────────────────────────────────────────────────────
    bool     l_turn_led_en              = false;
    bool     r_turn_led_en              = false;
    bool     brake_led_en               = false;
    bool     headlights_led_en          = false;
    bool     hazards                    = false;

    // ── Main IO / Power Bus ───────────────────────────────────────────────────
    double   main_5V_bus                = 0.0;
    double   main_12V_bus               = 0.0;
    double   main_24V_bus               = 0.0;
    double   main_5V_current            = 0.0;
    double   main_12V_current           = 0.0;
    double   main_24V_current           = 0.0;

    // ── Main IO / Firmware Heartbeats ─────────────────────────────────────────
    bool     bms_can_heartbeat          = true;
    bool     hv_can_heartbeat           = true;
    bool     mainIO_heartbeat           = true;
    bool     mcc_can_heartbeat          = true;
    bool     mppt_can_heartbeat         = true;

    // ── Solar Array / MPPT ────────────────────────────────────────────────────
    bool     mppt_mode                  = false;
    double   mppt_current_out           = 0.0;
    double   mppt_power_out             = 0.0;
    double   string1_temp               = 20.0;
    double   string2_temp               = 20.0;
    double   string3_temp               = 20.0;
    double   string1_V_in               = 0.0;
    double   string2_V_in               = 0.0;
    double   string3_V_in               = 0.0;
    double   string1_I_in               = 0.0;
    double   string2_I_in               = 0.0;
    double   string3_I_in               = 0.0;

    // ── Battery / BMS CAN ─────────────────────────────────────────────────────
    double   pack_temp                  = 0.0;
    double   pack_internal_temp         = 0.0;
    double   pack_current               = 0.0;
    double   pack_voltage               = 77.5;
    double   pack_power                 = 0.0;
    uint16_t populated_cells            = 0;
    double   soc                        = 0.0;
    double   soh                        = 100.0;
    double   pack_amphours              = 57.0;
    double   adaptive_total_capacity    = 57.0;
    uint8_t  fan_speed                  = 0;
    double   pack_resistance            = 0.0;
    double   bms_input_voltage          = 12.0;

    // ── Battery / BMS Faults ──────────────────────────────────────────────────
    bool     bps_fault                                  = false;
    bool     voltage_failsafe                           = false;
    bool     current_failsafe                           = false;
    bool     relay_failsafe                             = false;
    bool     cell_balancing_active                      = true;
    bool     charge_interlock_failsafe                  = false;
    bool     thermistor_b_value_table_invalid           = false;
    bool     input_power_supply_failsafe                = false;
    bool     discharge_limit_enforcement_fault          = false;
    bool     charger_safety_relay_fault                 = false;
    bool     internal_hardware_fault                    = false;
    bool     internal_heatsink_fault                    = false;
    bool     internal_software_fault                    = false;
    bool     highest_cell_voltage_too_high_fault        = false;
    bool     lowest_cell_voltage_too_low_fault          = false;
    bool     pack_too_hot_fault                         = false;
    bool     high_voltage_interlock_signal_fault        = false;
    bool     precharge_circuit_malfunction              = false;
    bool     abnormal_state_of_charge_behavior          = false;
    bool     internal_communication_fault               = false;
    bool     cell_balancing_stuck_off_fault             = false;
    bool     weak_cell_fault                            = false;
    bool     low_cell_voltage_fault                     = false;
    bool     open_wiring_fault                          = false;
    bool     current_sensor_fault                       = false;
    bool     highest_cell_voltage_over_5V_fault         = false;
    bool     cell_asic_fault                            = false;
    bool     weak_pack_fault                            = false;
    bool     fan_monitor_fault                          = false;
    bool     thermistor_fault                           = false;
    bool     external_communication_fault               = false;
    bool     redundant_power_supply_fault               = false;
    bool     high_voltage_isolation_fault               = false;
    bool     input_power_supply_fault                   = false;
    bool     charge_limit_enforcement_fault             = false;

    // ── Battery / Cell Group Voltages ─────────────────────────────────────────
    double   cell_group1_voltage        = 3.0;
    double   cell_group2_voltage        = 3.0;
    double   cell_group3_voltage        = 3.0;
    double   cell_group4_voltage        = 3.0;
    double   cell_group5_voltage        = 3.0;
    double   cell_group6_voltage        = 3.0;
    double   cell_group7_voltage        = 3.0;
    double   cell_group8_voltage        = 3.0;
    double   cell_group9_voltage        = 3.0;
    double   cell_group10_voltage       = 3.0;
    double   cell_group11_voltage       = 3.0;
    double   cell_group12_voltage       = 3.0;
    double   cell_group13_voltage       = 3.0;
    double   cell_group14_voltage       = 3.0;
    double   cell_group15_voltage       = 3.0;
    double   cell_group16_voltage       = 3.0;
    double   cell_group17_voltage       = 3.0;
    double   cell_group18_voltage       = 3.0;
    double   cell_group19_voltage       = 3.0;
    double   cell_group20_voltage       = 3.0;
    double   cell_group21_voltage       = 3.0;
    double   cell_group22_voltage       = 3.0;
    double   cell_group23_voltage       = 3.0;
    double   cell_group24_voltage       = 3.0;
    double   cell_group25_voltage       = 3.0;
    double   cell_group26_voltage       = 3.0;
    double   cell_group27_voltage       = 3.0;
    double   cell_group28_voltage       = 3.0;
    double   cell_group29_voltage       = 3.0;
    double   cell_group30_voltage       = 3.0;
    double   cell_group31_voltage       = 3.0;

    // ── Software / Timestamps ─────────────────────────────────────────────────
    uint16_t tstamp_ms                  = 0;
    uint8_t  tstamp_sc                  = 0;
    uint8_t  tstamp_mn                  = 0;
    uint8_t  tstamp_hr                  = 0;
    uint64_t tstamp_unix                = 0;

    // ── Software / GPS ────────────────────────────────────────────────────────
    double   lat                        = 43.0731;
    double   lon                        = -89.4012;
    double   elev                       = 0.0;

    // ── Software / Lap Counter ────────────────────────────────────────────────
    int32_t  lap_count                  = 0;
    int32_t  current_section            = 0;
    uint32_t lap_duration               = 0;

    // ── Race Strategy / Model Outputs ─────────────────────────────────────────
    double   optimized_target_power     = 0.0;
    double   maximum_distance_traveled  = 0.0;
};
