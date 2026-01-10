#!/usr/bin/env python3
"""
Shared Memory IPC for Telemetry Data
Zero-copy communication between coordinator and UI
"""

import mmap
import struct
import os
import time
from dataclasses import dataclass
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class TelemetrySnapshot:
    """All telemetry values for UI display"""
    # Core telemetry
    speed: float = 0.0
    soc: float = 0.0
    pack_voltage: float = 0.0
    pack_current: float = 0.0
    motor_temp: float = 0.0
    pack_temp: float = 0.0
    
    # Lap counter data
    lap_count: int = 0
    current_section: int = 0
    section_time: float = 0.0
    
    # Status flags
    headlights: bool = False
    l_turn_led_en: bool = False
    r_turn_led_en: bool = False
    hazards: bool = False
    park_brake: bool = False
    
    # Timestamps
    last_update_us: int = 0


# Struct format: 6 floats + 3 ints + 5 bools + 1 long = 52 bytes
SNAPSHOT_FORMAT = "<6f3i5?Q"
SNAPSHOT_SIZE = struct.calcsize(SNAPSHOT_FORMAT)
SHM_PATH = "/tmp/sc2_telemetry_shm"


class SharedTelemetryWriter:
    """Writes telemetry data to shared memory (CAN reader side)"""
    
    def __init__(self):
        try:
            # Create or open shared memory file
            self.fd = os.open(SHM_PATH, os.O_RDWR | os.O_CREAT, 0o666)
            os.ftruncate(self.fd, SNAPSHOT_SIZE)
            self.mm = mmap.mmap(self.fd, SNAPSHOT_SIZE)
            logger.info(f"Shared memory writer initialized: {SHM_PATH}")
        except Exception as e:
            logger.error(f"Failed to initialize shared memory writer: {e}")
            raise
        
    def update(self, snapshot: TelemetrySnapshot) -> None:
        """Write new telemetry snapshot"""
        try:
            packed = struct.pack(
                SNAPSHOT_FORMAT,
                snapshot.speed, snapshot.soc, snapshot.pack_voltage,
                snapshot.pack_current, snapshot.motor_temp, snapshot.pack_temp,
                snapshot.lap_count, snapshot.current_section, 
                int(snapshot.section_time * 1000),  # Convert to ms
                snapshot.headlights, snapshot.l_turn_led_en, snapshot.r_turn_led_en,
                snapshot.hazards, snapshot.park_brake,
                snapshot.last_update_us
            )
            self.mm.seek(0)
            self.mm.write(packed)
        except Exception as e:
            logger.error(f"Failed to write to shared memory: {e}")
    
    def close(self):
        """Clean up resources"""
        try:
            self.mm.close()
            os.close(self.fd)
        except Exception as e:
            logger.error(f"Error closing shared memory: {e}")


class SharedTelemetryReader:
    """Reads telemetry data from shared memory (UI side)"""
    
    def __init__(self, timeout_seconds: float = 10.0):
        """
        Initialize reader, waiting for shared memory file to exist
        
        Args:
            timeout_seconds: How long to wait for shared memory file
        """
        start_time = time.time()
        while not os.path.exists(SHM_PATH):
            if time.time() - start_time > timeout_seconds:
                raise TimeoutError(f"Shared memory file not found after {timeout_seconds}s")
            time.sleep(0.1)
        
        try:
            self.fd = os.open(SHM_PATH, os.O_RDONLY)
            self.mm = mmap.mmap(self.fd, SNAPSHOT_SIZE, prot=mmap.PROT_READ)
            logger.info(f"Shared memory reader initialized: {SHM_PATH}")
        except Exception as e:
            logger.error(f"Failed to initialize shared memory reader: {e}")
            raise
        
    def read(self) -> TelemetrySnapshot:
        """Read current telemetry snapshot"""
        try:
            self.mm.seek(0)
            data = self.mm.read(SNAPSHOT_SIZE)
            values = struct.unpack(SNAPSHOT_FORMAT, data)
            
            return TelemetrySnapshot(
                speed=values[0], soc=values[1], pack_voltage=values[2],
                pack_current=values[3], motor_temp=values[4], pack_temp=values[5],
                lap_count=values[6], current_section=values[7], 
                section_time=values[8] / 1000.0,  # Convert from ms
                headlights=values[9], l_turn_led_en=values[10], r_turn_led_en=values[11],
                hazards=values[12], park_brake=values[13],
                last_update_us=values[14]
            )
        except Exception as e:
            logger.error(f"Failed to read from shared memory: {e}")
            return TelemetrySnapshot()  # Return default values
    
    def close(self):
        """Clean up resources"""
        try:
            self.mm.close()
            os.close(self.fd)
        except Exception as e:
            logger.error(f"Error closing shared memory: {e}")


if __name__ == "__main__":
    # Test the shared memory system
    logging.basicConfig(level=logging.INFO)
    
    # Writer test
    writer = SharedTelemetryWriter()
    snapshot = TelemetrySnapshot(
        speed=45.5,
        soc=85.2,
        lap_count=3,
        headlights=True,
        last_update_us=int(time.time() * 1_000_000)
    )
    writer.update(snapshot)
    print(f"Wrote: {snapshot}")
    
    # Reader test
    time.sleep(0.1)
    reader = SharedTelemetryReader()
    read_snapshot = reader.read()
    print(f"Read: {read_snapshot}")
    
    writer.close()
    reader.close()
