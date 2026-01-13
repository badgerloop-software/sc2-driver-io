#!/usr/bin/env python3
"""
Lap Counter Consumer - Integrates lap counting with CAN bus
Receives GPS data from CAN, counts laps, and publishes lap data back to CAN
"""

import logging
import time
from typing import Optional
from can_bus.can_reader import CANMessage

try:
    from lap_counter.lap_counter import LapCounter, Point
    LAP_COUNTER_AVAILABLE = True
except ImportError:
    LAP_COUNTER_AVAILABLE = False
    logging.warning("Lap counter module not available")

try:
    from can_bus.can_writer import send_can_message
    CAN_WRITER_AVAILABLE = True
except ImportError:
    CAN_WRITER_AVAILABLE = False
    logging.warning("CAN writer not available")

logger = logging.getLogger(__name__)


class LapCounterConsumer:
    """
    Consumes GPS CAN messages, tracks lap counts, and publishes lap data back to CAN.
    
    CAN IDs used:
    - Input: GPS signals (latitude, longitude from format.json)
    - Output: 0x400 (lap count, section), 0x401 (lap times)
    """
    
    def __init__(
        self,
        line_start: tuple[float, float] = (40.1106, -88.2073),  # Example UIUC coordinates
        line_end: tuple[float, float] = (40.1108, -88.2073),
        tolerance_m: float = 20.0,
        min_move_m: float = 5.0,
        min_distance_between_counts_m: float = 100.0,
        channel: str = "can0"
    ):
        """
        Args:
            line_start: (lat, lon) tuple for finish line start
            line_end: (lat, lon) tuple for finish line end
            tolerance_m: Distance tolerance for GPS error (meters)
            min_move_m: Minimum movement to consider (meters)
            min_distance_between_counts_m: Min distance between lap counts
            channel: CAN channel for sending messages
        """
        if not LAP_COUNTER_AVAILABLE:
            raise ImportError("Lap counter module not available")
        
        # Reference point (average of line endpoints for coordinate conversion)
        self.ref_lat = (line_start[0] + line_end[0]) / 2
        self.ref_lon = (line_start[1] + line_end[1]) / 2
        
        # Convert finish line to local XY coordinates
        from lap_counter.lap_counter import ll_to_xy
        start_x, start_y = ll_to_xy(line_start[0], line_start[1], self.ref_lat, self.ref_lon)
        end_x, end_y = ll_to_xy(line_end[0], line_end[1], self.ref_lat, self.ref_lon)
        
        # Create lap counter
        self.lap_counter = LapCounter(
            Point(start_x, start_y),
            Point(end_x, end_y),
            tolerance_m=tolerance_m,
            min_move_m=min_move_m,
            min_distance_between_counts_m=min_distance_between_counts_m
        )
        
        # Track current GPS position
        self.current_lat: Optional[float] = None
        self.current_lon: Optional[float] = None
        
        # CAN output
        self.can_channel = channel
        self.last_lap_count = 0
        
        # Statistics
        self.gps_updates = 0
        self.laps_counted = 0
        self.messages_sent = 0
        
        logger.info(f"Lap Counter Consumer initialized")
        logger.info(f"Finish line: {line_start} to {line_end}")
        logger.info(f"Tolerance: {tolerance_m}m, Min move: {min_move_m}m")
    
    def consume(self, message: CANMessage) -> None:
        """
        Process CAN messages looking for GPS data.
        When GPS position is updated, check for lap crossings.
        """
        # Update GPS coordinates from CAN messages
        if message.signal_name == 'gps_latitude':
            self.current_lat = float(message.value)
        elif message.signal_name == 'gps_longitude':
            self.current_lon = float(message.value)
        else:
            return  # Not a GPS message we care about
        
        # If we have both coordinates, process
        if self.current_lat is not None and self.current_lon is not None:
            self._process_gps_update()
    
    def _process_gps_update(self) -> None:
        """Process GPS update and check for lap crossing"""
        from lap_counter.lap_counter import ll_to_xy
        
        # Convert to local XY
        x, y = ll_to_xy(self.current_lat, self.current_lon, self.ref_lat, self.ref_lon)
        
        # Update lap counter
        crossed = self.lap_counter.update(x, y)
        self.gps_updates += 1
        
        if crossed:
            self.laps_counted += 1
            lap_count = self.lap_counter.lap_count
            
            logger.info(f"LAP {lap_count} COMPLETED!")
            logger.info(f"Position: ({self.current_lat:.6f}, {self.current_lon:.6f})")
            logger.info(f"Total distance: {self.lap_counter.total_distance:.2f}m")
            
            # Publish lap data to CAN bus
            self._publish_lap_data()
    
    def _publish_lap_data(self) -> None:
        """Publish lap count and timing data to CAN bus"""
        if not CAN_WRITER_AVAILABLE:
            logger.warning("CAN writer not available, cannot publish lap data")
            return
        
        try:
            lap_count = self.lap_counter.lap_count
            total_distance = int(self.lap_counter.total_distance)
            timestamp_ms = int(time.time() * 1000)
            
            # Message 1 (CAN ID 0x400): Lap count and flags
            # Format: lap_count(4 bytes) + section(1) + flags(1) + reserved(2)
            import struct
            msg1_data = struct.pack("<IBBxx", lap_count, 0, 0x01)  # section=0, flags=valid
            
            send_can_message(
                can_id=0x400,
                data=list(msg1_data),
                channel=self.can_channel
            )
            
            # Message 2 (CAN ID 0x401): Distance and timestamp
            # Format: total_distance(4 bytes) + timestamp_ms(4 bytes)
            msg2_data = struct.pack("<II", total_distance, timestamp_ms & 0xFFFFFFFF)
            
            send_can_message(
                can_id=0x401,
                data=list(msg2_data),
                channel=self.can_channel
            )
            
            self.messages_sent += 2
            logger.info(f"Published lap data to CAN: lap={lap_count}, distance={total_distance}m")
            
        except Exception as e:
            logger.error(f"Failed to publish lap data to CAN: {e}")
    
    def get_stats(self) -> dict:
        """Return consumer statistics"""
        return {
            'gps_updates': self.gps_updates,
            'laps_counted': self.laps_counted,
            'messages_sent': self.messages_sent,
            'current_lap': self.lap_counter.lap_count,
            'total_distance_m': round(self.lap_counter.total_distance, 2)
        }
    
    def close(self) -> None:
        """Clean up resources"""
        logger.info(f"Lap Counter Consumer closed. Stats: {self.get_stats()}")
