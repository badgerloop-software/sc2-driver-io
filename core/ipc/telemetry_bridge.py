#!/usr/bin/env python3
"""
Telemetry Bridge - Python to C++ Communication
Sends CAN data to C++ telemetry system via Unix domain socket
"""

import socket
import struct
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class TelemetryBridge:
    """Sends CAN data to C++ telemetry system via Unix socket"""
    
    SOCKET_PATH = "/tmp/sc2_can_bridge.sock"
    MSG_FORMAT = "<IQB8s"  # can_id(4), timestamp_us(8), data_len(1), data[8]
    
    def __init__(self):
        """Initialize Unix domain socket connection"""
        try:
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            self.connected = True
            logger.info(f"Telemetry bridge initialized: {self.SOCKET_PATH}")
        except Exception as e:
            logger.error(f"Failed to create socket: {e}")
            self.connected = False
    
    def send(self, can_id: int, data: bytes, timestamp_us: int) -> bool:
        """
        Send CAN message to C++ telemetry system
        
        Args:
            can_id: CAN message ID
            data: CAN data bytes (up to 8 bytes)
            timestamp_us: Timestamp in microseconds
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not self.connected:
            return False
            
        try:
            # Pad data to 8 bytes
            padded_data = data.ljust(8, b'\x00')[:8]
            
            # Pack message
            packed = struct.pack(
                self.MSG_FORMAT,
                can_id,
                timestamp_us,
                len(data),
                padded_data
            )
            
            # Send to C++ telemetry
            self.socket.sendto(packed, self.SOCKET_PATH)
            return True
            
        except FileNotFoundError:
            if self.connected:
                logger.warning("C++ telemetry not running (socket not found)")
                self.connected = False
            return False
        except Exception as e:
            logger.error(f"Error sending to telemetry: {e}")
            return False
    
    def close(self):
        """Close the socket"""
        try:
            self.socket.close()
            logger.info("Telemetry bridge closed")
        except Exception as e:
            logger.error(f"Error closing socket: {e}")


if __name__ == "__main__":
    # Test the bridge
    logging.basicConfig(level=logging.INFO)
    
    bridge = TelemetryBridge()
    
    # Send test message
    import time
    test_data = b'\x01\x02\x03\x04'
    timestamp = int(time.time() * 1_000_000)
    
    success = bridge.send(0x123, test_data, timestamp)
    print(f"Send {'succeeded' if success else 'failed'}")
    
    bridge.close()
