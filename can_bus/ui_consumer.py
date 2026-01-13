#!/usr/bin/env python3
"""
UI Consumer - Updates shared memory for dashboard display
Aggregates CAN messages into telemetry snapshot for zero-copy UI access
"""

import logging
import time
from typing import Optional
from can_bus.can_reader import CANMessage

try:
    from core.ipc.shared_data import SharedTelemetryWriter, TelemetrySnapshot
    SHARED_MEMORY_AVAILABLE = True
except ImportError:
    SHARED_MEMORY_AVAILABLE = False
    logging.warning("Shared memory not available, UI consumer disabled")

logger = logging.getLogger(__name__)


class UIConsumer:
    """
    Consumes CAN messages and updates shared memory for UI display.
    Maintains a TelemetrySnapshot that's periodically written to shared memory.
    """
    
    def __init__(self, update_rate_hz: float = 10.0):
        """
        Args:
            update_rate_hz: How often to update shared memory (default 10Hz for UI)
        """
        if not SHARED_MEMORY_AVAILABLE:
            raise ImportError("Shared memory module not available")
        
        self.writer = SharedTelemetryWriter()
        self.snapshot = TelemetrySnapshot()
        
        self.update_interval = 1.0 / update_rate_hz
        self.last_update_time = 0.0
        
        self.messages_received = 0
        self.updates_written = 0
        
        logger.info(f"UI Consumer initialized with {update_rate_hz}Hz update rate")
    
    def consume(self, message: CANMessage) -> None:
        """
        Process CAN message and update snapshot.
        Called by CAN reader for each message.
        """
        self.messages_received += 1
        
        # Map CAN signals to snapshot fields
        signal_map = {
            'speed': 'speed',
            'soc': 'soc',
            'pack_voltage': 'pack_voltage',
            'pack_current': 'pack_current',
            'motor_temp': 'motor_temp',
            'pack_temp': 'pack_temp',
            'lap_count': 'lap_count',
            'current_section': 'current_section',
            'section_time': 'section_time',
            'headlights': 'headlights',
            'l_turn_led_en': 'l_turn_led_en',
            'r_turn_led_en': 'r_turn_led_en',
            'hazards': 'hazards',
            'park_brake': 'park_brake',
        }
        
        # Update snapshot if this signal is one we track
        if message.signal_name in signal_map:
            field_name = signal_map[message.signal_name]
            setattr(self.snapshot, field_name, message.value)
            self.snapshot.last_update_us = int(message.timestamp * 1_000_000)
        
        # Write to shared memory at configured rate
        current_time = time.time()
        if current_time - self.last_update_time >= self.update_interval:
            self._write_snapshot()
            self.last_update_time = current_time
    
    def _write_snapshot(self) -> None:
        """Write current snapshot to shared memory"""
        try:
            self.writer.update(self.snapshot)
            self.updates_written += 1
        except Exception as e:
            logger.error(f"Failed to write to shared memory: {e}")
    
    def get_stats(self) -> dict:
        """Return consumer statistics"""
        return {
            'messages_received': self.messages_received,
            'updates_written': self.updates_written,
            'update_rate_hz': 1.0 / self.update_interval if self.update_interval > 0 else 0
        }
    
    def close(self) -> None:
        """Clean up resources"""
        # Write final snapshot
        self._write_snapshot()
        logger.info(f"UI Consumer closed. Stats: {self.get_stats()}")
