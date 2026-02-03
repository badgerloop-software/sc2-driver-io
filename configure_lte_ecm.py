#!/usr/bin/env python3
"""
Configure Quectel EG25 modem to use ECM mode for better compatibility
"""
import serial
import time

def send_at_command(ser, command, wait=1):
    """Send AT command and get response"""
    ser.write(f"{command}\r\n".encode())
    time.sleep(wait)
    response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
    print(f"Command: {command}")
    print(f"Response: {response}")
    return response

def configure_ecm_mode():
    """Configure modem to use ECM mode"""
    try:
        # Open serial connection to AT port
        with serial.Serial('/dev/ttyUSB2', 115200, timeout=2) as ser:
            print("Connected to modem AT port")
            
            # Check current USB net mode
            print("\n=== Checking current USB net mode ===")
            send_at_command(ser, 'AT+QCFG="usbnet"')
            
            # Set to ECM mode (mode 1 = ECM)
            print("\n=== Setting USB net mode to ECM ===")
            response = send_at_command(ser, 'AT+QCFG="usbnet",1')
            
            if 'OK' in response:
                print("\n✓ Successfully configured ECM mode")
                print("Modem needs to be reset for changes to take effect")
                
                # Reset modem
                print("\n=== Resetting modem ===")
                send_at_command(ser, 'AT+CFUN=1,1', wait=2)
                print("Modem is resetting... This will take about 15 seconds")
                return True
            else:
                print("\n✗ Failed to configure ECM mode")
                return False
                
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Configuring Quectel EG25 modem for ECM mode...")
    if configure_ecm_mode():
        print("\nConfiguration complete!")
        print("Wait 15 seconds for modem to restart, then the usb0 interface should be available")
    else:
        print("\nConfiguration failed!")
