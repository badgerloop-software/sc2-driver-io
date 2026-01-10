#!/usr/bin/env python3
"""
CAN Bus Reader - Single reader with fan-out architecture
Distributes CAN messages to multiple registered consumers
"""

from dataclasses import dataclass
from typing import Callable, List, Dict, Any, Optional
import can
import threading
import queue
import logging
import time

logger = logging.getLogger(__name__)


@dataclass
class CANMessage:
    """Standardized CAN message format for all consumers"""
    can_id: int
    signal_name: str
    value: float | bool
    timestamp: float
    raw_data: bytes


class CANReader:
    """
    Single CAN reader that distributes messages to registered consumers.
    Runs in dedicated thread with real-time priority.
    
    This prevents data races and missed messages that occur when multiple
    processes try to read from the same CAN bus interface.
    """
    
    def __init__(self, channel: str = "can0", bustype: str = "socketcan"):
        self.bus = can.interface.Bus(channel=channel, bustype=bustype)
        self._consumers: Dict[str, Dict[str, Any]] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        # Import signal parser
        try:
            from can_bus.signal_parser import preprocess_data_format, signal_definitions
            self.signal_definitions = signal_definitions
        except ImportError:
            logger.warning("Signal parser not available, raw messages only")
            self.signal_definitions = {}
        
    def register_consumer(
        self, 
        name: str, 
        callback: Callable[[CANMessage], None],
        queue_size: int = 1000,
        filter_ids: Optional[List[int]] = None
    ) -> None:
        """
        Register a consumer to receive CAN messages.
        
        Args:
            name: Unique consumer identifier (e.g., "csv_logger", "lap_counter")
            callback: Function called with each CANMessage
            queue_size: Max queued messages before dropping
            filter_ids: Optional list of CAN IDs this consumer cares about
        """
        self._consumers[name] = {
            'callback': callback,
            'filter_ids': set(filter_ids) if filter_ids else None,
            'queue': queue.Queue(maxsize=queue_size),
            'dropped': 0,
            'thread': None
        }
        
        # Start consumer thread
        consumer_thread = threading.Thread(
            target=self._consumer_loop,
            args=(name,),
            daemon=True
        )
        consumer_thread.start()
        self._consumers[name]['thread'] = consumer_thread
        
        logger.info(f"Registered consumer: {name}")
    
    def start(self) -> None:
        """Start the CAN reader thread"""
        if self._running:
            logger.warning("CAN reader already running")
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        logger.info("CAN reader started")
    
    def stop(self) -> None:
        """Stop the CAN reader"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        self.bus.shutdown()
        logger.info("CAN reader stopped")
        
    def _read_loop(self) -> None:
        """Main read loop - distributes messages to all consumers"""
        while self._running:
            try:
                msg = self.bus.recv(timeout=0.01)  # 10ms timeout
                if msg is None:
                    continue
                    
                parsed = self._parse_message(msg)
                if parsed is None:
                    continue
                    
                # Fan out to all registered consumers
                for name, consumer in self._consumers.items():
                    # Apply filter if specified
                    if consumer['filter_ids'] and parsed.can_id not in consumer['filter_ids']:
                        continue
                        
                    try:
                        consumer['queue'].put_nowait(parsed)
                    except queue.Full:
                        consumer['dropped'] += 1
                        if consumer['dropped'] % 100 == 0:
                            logger.warning(f"Consumer {name} dropped {consumer['dropped']} messages")
                            
            except Exception as e:
                logger.error(f"Error in CAN read loop: {e}")
                time.sleep(0.1)
    
    def _consumer_loop(self, name: str) -> None:
        """Process queued messages for a specific consumer"""
        consumer = self._consumers[name]
        callback = consumer['callback']
        msg_queue = consumer['queue']
        
        while self._running:
            try:
                msg = msg_queue.get(timeout=0.1)
                callback(msg)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in consumer {name}: {e}")
    
    def _parse_message(self, msg: can.Message) -> Optional[CANMessage]:
        """Parse CAN message using signal definitions"""
        # Convert to format expected by signal parser
        message_data = {
            'id': msg.arbitration_id,
            'data': msg.data,
            'timestamp': msg.timestamp
        }
        
        # For now, return basic parsed message
        # Full signal parsing integration coming from signal_parser.py
        return CANMessage(
            can_id=msg.arbitration_id,
            signal_name=f"CAN_ID_0x{msg.arbitration_id:03X}",
            value=float(msg.data[0]) if len(msg.data) > 0 else 0.0,
            timestamp=msg.timestamp,
            raw_data=bytes(msg.data)
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for all consumers"""
        stats = {}
        for name, consumer in self._consumers.items():
            stats[name] = {
                'queue_size': consumer['queue'].qsize(),
                'dropped': consumer['dropped']
            }
        return stats


if __name__ == "__main__":
    # Test the CAN reader
    logging.basicConfig(level=logging.INFO)
    
    def test_callback(msg: CANMessage):
        print(f"Received: CAN ID 0x{msg.can_id:03X}, Value: {msg.value}")
    
    reader = CANReader("can0")
    reader.register_consumer("test", test_callback)
    reader.start()
    
    try:
        while True:
            time.sleep(1)
            print(reader.get_stats())
    except KeyboardInterrupt:
        reader.stop()
