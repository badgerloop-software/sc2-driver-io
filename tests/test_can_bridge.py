#!/usr/bin/env python3
"""
Test script for CAN Bridge communication
Sends test CAN messages to the C++ telemetry system
"""

import sys
import time
sys.path.insert(0, '/Users/shobhin/sc2-driver-io')

from core.ipc.telemetry_bridge import TelemetryBridge

def main():
    print("=" * 60)
    print("CAN Bridge Test - Sending messages to C++ telemetry")
    print("=" * 60)
    
    bridge = TelemetryBridge()
    
    if not bridge.connected:
        print("ERROR: Failed to create bridge socket!")
        return 1
    
    print(f"Bridge initialized, sending to: {bridge.SOCKET_PATH}")
    print()
    
    # Send test messages
    test_messages = [
        (0x100, b'\x01\x02\x03\x04', "Battery voltage"),
        (0x101, b'\x05\x06\x07\x08', "Motor controller"),
        (0x102, b'\x11\x22\x33\x44\x55\x66\x77\x88', "Full 8-byte message"),
        (0x200, b'\xAA\xBB', "Short message"),
        (0x300, b'', "Empty message"),
    ]
    
    success_count = 0
    for can_id, data, description in test_messages:
        timestamp_us = int(time.time() * 1_000_000)
        success = bridge.send(can_id, data, timestamp_us)
        
        status = "✓" if success else "✗"
        print(f"{status} CAN ID: 0x{can_id:03X} - {description}")
        print(f"  Data: {data.hex() if data else '(empty)'} ({len(data)} bytes)")
        print(f"  Timestamp: {timestamp_us}")
        
        if success:
            success_count += 1
        
        time.sleep(0.1)  # Small delay between messages
    
    print()
    print(f"Test complete: {success_count}/{len(test_messages)} messages sent successfully")
    
    # Send a burst of messages to test throughput
    print()
    print("Sending burst of 1000 messages...")
    burst_start = time.time()
    burst_count = 0
    
    for i in range(1000):
        timestamp_us = int(time.time() * 1_000_000)
        if bridge.send(0x400 + (i % 256), b'\x00\x00\x00\x00', timestamp_us):
            burst_count += 1
    
    burst_duration = time.time() - burst_start
    print(f"Burst complete: {burst_count}/1000 messages in {burst_duration:.3f}s")
    print(f"Throughput: {burst_count / burst_duration:.0f} messages/second")
    
    bridge.close()
    print()
    print("Bridge closed successfully")
    return 0

if __name__ == "__main__":
    sys.exit(main())
