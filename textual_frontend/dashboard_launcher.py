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
        
    def start_dashboard(self):
        """Start the Textual dashboard in a separate thread"""
        def run_dashboard():
            self.dashboard = SC2Dashboard()
            self.dashboard.run()
        
        dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
        dashboard_thread.start()
        return dashboard_thread
    
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
            
            self.update_telemetry_file(telemetry_data)
            time.sleep(0.1)  # 10Hz updates
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        print("\nShutting down SC2 Dashboard...")
        self.running = False
        if self.dashboard:
            self.dashboard.exit()
        sys.exit(0)

def main():
    """Main entry point for dashboard integration"""
    print("Starting SC2 Driver IO Terminal Dashboard...")
    
    bridge = TelemetryBridge()
    
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, bridge.signal_handler)
    signal.signal(signal.SIGTERM, bridge.signal_handler)
    
    try:
        # Start the dashboard
        dashboard_thread = bridge.start_dashboard()
        
        # Start telemetry simulation (replace with actual C++ interface)
        print("Starting telemetry bridge...")
        bridge.simulate_telemetry_data()
        
    except KeyboardInterrupt:
        bridge.signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main()