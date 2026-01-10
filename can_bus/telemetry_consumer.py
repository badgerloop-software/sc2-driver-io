#!/usr/bin/env python3
"""
Telemetry Consumer - Forwards CAN data to C++ telemetry system
Receives parsed CAN messages from CANReader and sends to Unix socket bridge
"""

import logging
from typing import Optional
from can_bus.can_reader import CANMessage
from core.ipc.telemetry_bridge import TelemetryBridge

logger = logging.getLogger(__name__)


class TelemetryConsumer:
    """
    Consumer that forwards CAN data to C++ telemetry system.
    Converts CANMessage format to packed binary for Unix socket.
    """
    
    def __init__(self):
        """Initialize telemetry bridge connection"""
        self.bridge = TelemetryBridge()
        self.messages_sent = 0
        self.messages_failed = 0
        
        logger.info("Telemetry consumer initialized")
    
    def consume(self, msg: CANMessage) -> None:
        """
        Callback for CAN reader - sends message to C++ telemetry.
        
        Args:
            msg: Parsed CAN message from CANReader
        """
        try:
            # Convert timestamp to microseconds
            timestamp_us = int(msg.timestamp * 1_000_000)
            
            # Send to C++ telemetry system
            success = self.bridge.send(msg.can_id, msg.raw_data, timestamp_us)
            
            if success:
                self.messages_sent += 1
                if self.messages_sent % 1000 == 0:
                    logger.debug(f"Sent {self.messages_sent} messages to telemetry")
            else:
                self.messages_failed += 1
                if self.messages_failed % 100 == 0:
                    logger.warning(f"Failed to send {self.messages_failed} messages")
                    
        except Exception as e:
            self.messages_failed += 1
            logger.error(f"Error in telemetry consumer: {e}")
    
    def get_stats(self) -> dict:
        """Get consumer statistics"""
        return {
            'sent': self.messages_sent,
            'failed': self.messages_failed,
            'success_rate': (
                self.messages_sent / (self.messages_sent + self.messages_failed)
                if (self.messages_sent + self.messages_failed) > 0
                else 0.0
            )
        }
    
    def close(self):
        """Clean shutdown"""
        self.bridge.close()
        logger.info(f"Telemetry consumer closed - Stats: {self.get_stats()}")


if __name__ == "__main__":
    # Test consumer
    logging.basicConfig(level=logging.INFO)
    
    import time
    consumer = TelemetryConsumer()
    
    # Create test message
    test_msg = CANMessage(
        can_id=0x100,
        signal_name="test_signal",
        value=123.45,
        timestamp=time.time(),
        raw_data=b'\x01\x02\x03\x04'
    )
    
    consumer.consume(test_msg)
    print(f"Stats: {consumer.get_stats()}")
    
    consumer.close()
