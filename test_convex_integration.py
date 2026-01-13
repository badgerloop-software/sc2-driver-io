#!/usr/bin/env python3
"""
Test script for Convex integration
Simulates telemetry data being sent via the C++ system
"""

import requests
import json
import time
import struct

def bytes_to_hex(data: bytes) -> str:
    """Convert bytes to hex string"""
    return data.hex()

def create_test_telemetry_packet():
    """Create a fake telemetry packet similar to what the C++ system would send"""
    # Example: pack some float values (speed, SOC, voltage, current)
    data = struct.pack('<ffff', 45.5, 87.3, 112.8, 23.4)
    return data

def send_to_convex(convex_url: str, data: bytes, timestamp: int):
    """Send telemetry data to Convex via HTTP API"""
    
    hex_data = bytes_to_hex(data)
    
    payload = {
        "path": "telemetry:storeTelemetry",
        "args": [{
            "timestamp": timestamp,
            "data": hex_data,
            "dataSize": len(data),
            "source": "python_test",
            "dataFormat": "sc1-data-format",
            "formatVersion": "1.0",
            "receivedAt": int(time.time() * 1000)
        }]
    }
    
    url = f"{convex_url}/api/mutation"
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        
        if response.status_code >= 200 and response.status_code < 300:
            print(f"✅ Success: Sent {len(data)} bytes - HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return True
        else:
            print(f"❌ Failed: HTTP {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False

def test_convex_integration():
    """Main test function"""
    
    # Load config
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("❌ config.json not found")
        return
    
    convex_url = config.get('convex_deployment_url', '')
    
    if not convex_url:
        print("❌ convex_deployment_url not set in config.json")
        print("\nPlease update config.json with your Convex deployment URL:")
        print('  "convex_deployment_url": "https://your-deployment.convex.site"')
        return
    
    print("Convex Integration Test")
    print("=" * 50)
    print(f"Convex URL: {convex_url}")
    print()
    
    # Test 1: Send a single packet
    print("Test 1: Sending single telemetry packet...")
    data = create_test_telemetry_packet()
    timestamp = int(time.time() * 1000)
    success = send_to_convex(convex_url, data, timestamp)
    print()
    
    if success:
        # Test 2: Send multiple packets
        print("Test 2: Sending 5 packets in sequence...")
        for i in range(5):
            data = create_test_telemetry_packet()
            timestamp = int(time.time() * 1000)
            send_to_convex(convex_url, data, timestamp)
            time.sleep(0.5)
        print()
        
        print("✅ Tests complete! Check your Convex dashboard to see the data:")
        print(f"   {convex_url.replace('.site', '.dev')}/")
    else:
        print("\n⚠️  Initial test failed. Please check:")
        print("   1. Convex URL is correct in config.json")
        print("   2. Convex mutation function is deployed")
        print("   3. Internet connection is working")

if __name__ == "__main__":
    test_convex_integration()
