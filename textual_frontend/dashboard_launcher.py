#!/usr/bin/env python3
"""
SC2 Driver IO - Textual Dashboard Integration
Bridge between C++ backend and Textual terminal GUI
"""

import json
import time
import signal
import sys
import threading
from pathlib import Path
from textual_dashboard import SC2Dashboard

class TelemetryBridge:
    """Bridge between C++ telemetry data and Textual dashboard"""
    
    def __init__(self, data_file="../telemetry_data.json"):
        self.data_file = Path(data_file)
        self.running = True
        self.lock = threading.Lock()
        self.dashboard = None
        
    def start_telemetry_simulation(self):
        """Start telemetry simulation in a background thread"""
        def run_simulation():
            self.simulate_telemetry_data()
        
        sim_thread = threading.Thread(target=run_simulation, daemon=True)
        sim_thread.start()
        return sim_thread
    
    def update_telemetry_file(self, telemetry_data):
        """Write telemetry data to JSON file for dashboard consumption"""
        with self.lock:
            try:
                with open(self.data_file, 'w') as f:
                    json.dump(telemetry_data, f, indent=2)
            except Exception as e:
                print(f"Error writing telemetry data: {e}")
    
    def simulate_telemetry_data(self):
        """Simulate telemetry data for testing (replace with actual C++ interface)"""
        import random
        
        # Define all possible faults
        all_faults = [
            "bps_fault",
            "voltage_failsafe",
            "current_failsafe", 
            "relay_failsafe",
            "charge_interlock_failsafe",
            "thermistor_b_value_table_invalid",
            "input_power_supply_failsafe",
            "discharge_limit_enforcement_fault",
            "charger_safety_relay_fault",
            "internal_hardware_fault",
            "internal_heatsink_fault",
            "internal_software_fault",
            "highest_cell_voltage_too_high_fault",
            "lowest_cell_voltage_too_low_fault",
            "pack_too_hot_fault",
            "high_voltage_interlock_signal_fault",
            "precharge_circuit_malfunction",
            "abnormal_state_of_charge_behavior",
            "internal_communication_fault",
            "cell_balancing_stuck_off_fault",
            "weak_cell_fault",
            "low_cell_voltage_fault",
            "open_wiring_fault",
            "current_sensor_fault",
            "highest_cell_voltage_over_5V_fault",
            "cell_asic_fault",
            "weak_pack_fault",
            "fan_monitor_fault",
            "thermistor_fault",
            "external_communication_fault",
            "redundant_power_supply_fault",
            "high_voltage_isolation_fault",
            "input_power_supply_fault",
            "charge_limit_enforcement_fault"
        ]
        
        while self.running:
            # Simulate realistic telemetry data
            telemetry_data = {
                "speed": random.uniform(0, 120),
                "soc": random.uniform(20, 100),
                "pack_voltage": random.uniform(300, 400),
                "pack_current": random.uniform(-50, 50),
                "motor_temp": random.uniform(25, 85),
                "headlights": random.choice([True, False]),
                "l_turn_led_en": random.choice([True, False]),
                "r_turn_led_en": random.choice([True, False]),
                "hazards": random.choice([True, False]),
                "parking_brake": random.choice([True, False]),
                "timestamp": time.time()
            }
            
            # Add faults - mostly false, but occasionally set some to true
            for fault in all_faults:
                telemetry_data[fault] = False
            
            # 15% chance to have 1-3 random faults active
            if random.random() < 0.15:
                num_faults = random.randint(1, 3)
                active_faults = random.sample(all_faults, num_faults)
                for fault in active_faults:
                    telemetry_data[fault] = True
            
            self.update_telemetry_file(telemetry_data)
            time.sleep(0.1)  # 10Hz updates
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print("\nShutting down SC2 Dashboard...")
        self.running = False
        # Textual handles its own shutdown when running in main thread
        sys.exit(0)

def main():
    """Main entry point for dashboard integration"""
    print("Starting SC2 Driver IO Terminal Dashboard...")
    
    bridge = TelemetryBridge()
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, bridge.signal_handler)
    signal.signal(signal.SIGTERM, bridge.signal_handler)
    
    try:
        # Start telemetry simulation in background thread
        print("Starting telemetry bridge...")
        sim_thread = bridge.start_telemetry_simulation()
        
        # Run dashboard in main thread (required for Textual)
        bridge.dashboard = SC2Dashboard()
        bridge.dashboard.run()
        
    except KeyboardInterrupt:
        bridge.signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main()