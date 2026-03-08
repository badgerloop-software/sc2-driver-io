#!/usr/bin/env python3
import can
import threading
import queue
import logging
import time
from dataclasses import dataclass
from typing import Callable, List, Dict, Any, Optional, Union

logger = logging.getLogger(__name__)

@dataclass
class CANMessage:
    can_id: int
    signal_name: str
    value: Union[float, bool]
    timestamp: float
    raw_data: bytes

class CANReader:
    def __init__(self, channel: str = 'can0', bustype: str = 'socketcan'):
        self.bus = can.interface.Bus(channel=channel, bustype=bustype)
        self._consumers: Dict[str, Dict[str, Any]] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        
        try:
            from can_bus.signal_parser import signal_definitions, MyListener
            self.signal_definitions = signal_definitions
            self.parser = MyListener()
            logger.info("Signal parser initialized with %d IDs", len(self.signal_definitions))
        except Exception as e:
            logger.warning("Signal parser error: %s", e)
            self.signal_definitions = {}
            self.parser = None
        
    def register_consumer(self, name: str, callback: Callable[[CANMessage], None], queue_size: int = 1000, filter_ids: Optional[List[int]] = None):
        self._consumers[name] = {
            'callback': callback,
            'filter_ids': set(filter_ids) if filter_ids else None,
            'queue': queue.Queue(maxsize=queue_size),
            'dropped': 0,
            'thread': None
        }
        logger.info(f"Registered consumer: {name}")
    
    def start(self):
        if self._running:
            return
        self._running = True
        
        # Start consumer threads
        for name in self._consumers:
            t = threading.Thread(target=self._consumer_loop, args=(name,), daemon=True)
            t.start()
            self._consumers[name]['thread'] = t
            
        # Start reader thread
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        logger.info("CAN reader and consumers started")
    
    def stop(self):
        self._running = False
        if self._thread: 
            self._thread.join(timeout=5.0)
        self.bus.shutdown()
        logger.info("CAN reader stopped")
        
    def _read_loop(self):
        while self._running:
            try:
                msg = self.bus.recv(timeout=0.1)
                if msg:
                    parsed_msgs = self._parse_message(msg)
                    for p in parsed_msgs:
                        for name, consumer in self._consumers.items():
                            if not consumer['filter_ids'] or p.can_id in consumer['filter_ids']:
                                try:
                                    consumer['queue'].put_nowait(p)
                                except queue.Full:
                                    consumer['dropped'] += 1
            except Exception as e:
                logger.error(f"Read error: {e}")
                time.sleep(0.1)
    
    def _consumer_loop(self, name: str):
        consumer = self._consumers[name]
        callback = consumer['callback']
        msg_queue = consumer['queue']
        while self._running:
            try:
                msg = msg_queue.get(timeout=0.1)
                callback(msg)
            except queue.Empty: continue
            except Exception as e: logger.error(f"Consumer {name} error: {e}")
    
    def _parse_message(self, msg: can.Message) -> List[CANMessage]:
        if not self.parser or msg.arbitration_id not in self.signal_definitions:
            return [CANMessage(msg.arbitration_id, f"RAW_0x{msg.arbitration_id:03X}", 0.0, msg.timestamp, bytes(msg.data))]
        
        parsed_results = self.parser.parse_data({'id': msg.arbitration_id, 'data': msg.data, 'timestamp': msg.timestamp})
        return [CANMessage(p.can_id, p.signal_name, p.value, p.timestamp, bytes(msg.data)) for p in parsed_results]

    def get_stats(self) -> Dict[str, Any]:
        return {name: {'queue': c['queue'].qsize(), 'dropped': c['dropped']} for name, c in self._consumers.items()}
