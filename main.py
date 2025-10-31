#!/usr/bin/env python3
"""
SC2 Driver IO - Main Application
Multi-threaded coordinator for Solar Car 2 driver IO system

DATA FLOW ARCHITECTURE (3 messages/second from CAN):
┌─────────────┐
│  CAN Bus    │ → Byte Array (raw firmware data)
└──────┬──────┘
       ↓
┌──────────────────────────────────────────────────────────┐
│  Thread 0: CAN Reception & GPS Integration (CRITICAL)    │
│  - Receive CAN message (byte array)                      │
│  - Parse GPS data from LTE modem (EG25-G GNSS)          │
│  - Extract lat/lon and feed to lap counter               │
│  - Get LapData struct back (lap_count, section, duration)│
│  - Modify byte array with lap counter data               │
│  - Queue for transmission & logging                      │
│  Duration: ~10-20ms per message (target < 333ms for 3Hz) │
└──────────────────────────────────────────────────────────┘
       ↓ (byte array + lap data)
       ├────────────────┬─────────────────┬──────────────┐
       ↓                ↓                 ↓              ↓
┌─────────────┐  ┌──────────┐  ┌─────────────┐  ┌──────────────┐
│ Thread 1:   │  │Thread 2: │  │Thread 3:    │  │ Thread 4:    │
│ LTE Upload  │  │Radio TX  │  │CSV Logger   │  │NN Buffer     │
│ (Cloud SQL) │  │(RFD900A) │  │(Async Write)│  │(Future: NN)  │
└─────────────┘  └──────────┘  └─────────────┘  └──────────────┘
       ↓                ↓                              ↓
┌─────────────────────────────────────────────────────────┐
│ Thread 5: CAN Transmission (send modified byte array)   │
│ - Publish lap counter data back to CAN bus              │
│ - Future: Publish NN optimized power distribution       │
└─────────────────────────────────────────────────────────┘

Threading Architecture:
- Thread 0: CAN RX + GPS + Lap Counter (CRITICAL PATH - high priority)
- Thread 1: LTE Transmission (parallel, non-blocking)
- Thread 2: Radio Transmission (parallel, non-blocking)
- Thread 3: CSV Logging (buffered, async I/O)
- Thread 4: Neural Network Buffer (future: inference when buffer full)
- Thread 5: CAN TX (publish lap data + NN outputs back to bus)
- Thread 6: Frontend Update (dashboard refresh at 1Hz)

Performance Targets:
- CAN processing latency: < 50ms (critical path)
- CSV write: Async batch writes every 1 second (30-50 messages)
- LTE/Radio: Fire-and-forget with retry queues
- NN buffer: Accumulate until threshold (e.g., 1000 samples)
- Dashboard refresh: 1Hz (low priority)

External Module Integration:
- can_snooper/: CAN communication module (SocketCAN interface)
- lap_counter/: GPS-based lap counting (returns LapData struct)
- data_logger/: Buffered CSV logging to USB drive
- lte_modem/: EG25-G GPS interface for lat/lon extraction
- telemetry/: Integration with existing C++ backend (LTE/Radio)
"""

import threading
import time
import queue
import signal
import sys
import os
import logging
import subprocess
import re
from typing import Optional, Dict, Any

# External module imports (to be implemented separately)
try:
    # These modules will be created in separate folders
    from lap_counter import LapCounter
    from data_logger import CSVDataLogger
    from can_interface import CANInterface
    # Note: Integration with existing C++ telemetry system TBD
    EXTERNAL_MODULES_AVAILABLE = True
except ImportError:
    print("WARNING: External modules not available, running in skeleton mode")
    EXTERNAL_MODULES_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('driver_io.log', encoding='utf-8')  # File output for dashboard with UTF-8
    ]
)
logger = logging.getLogger(__name__)

class DriverIOSystem:
    """Main driver IO system coordinator
    
    Optimized for 3 messages/second CAN throughput with parallel processing
    """
    
    def __init__(self):
        self.running = False
        self.threads = {}
        
        # Initialize external modules (if available)
        if EXTERNAL_MODULES_AVAILABLE:
            self.can_interface = CANInterface()
            self.lap_counter = LapCounter()
            self.csv_logger = CSVDataLogger()
            # TODO: Add LTE modem interface for GPS
            # self.lte_modem = LTEModem()
        else:
            # Placeholder objects for skeleton mode
            self.can_interface = None
            self.lap_counter = None
            self.csv_logger = None
        
        # Inter-thread communication queues (optimized sizes)
        # Single processed data queue (after lap counter modification)
        self.processed_data_queue = queue.Queue(maxsize=100)  # Holds modified byte arrays
        
        # Separate queues for parallel transmission
        self.lte_tx_queue = queue.Queue(maxsize=200)  # LTE transmission
        self.radio_tx_queue = queue.Queue(maxsize=200)  # Radio transmission
        self.can_tx_queue = queue.Queue(maxsize=50)  # CAN bus retransmission
        
        # CSV logging queue (batched writes)
        self.csv_queue = queue.Queue(maxsize=500)  # Buffer for CSV writes
        
        # Neural network buffer (future use)
        self.nn_buffer = []  # Accumulate data for NN inference
        self.nn_buffer_lock = threading.Lock()
        self.nn_buffer_threshold = 1000  # Trigger NN inference at 1000 samples
        
        # Dashboard update queue (low priority, 1Hz)
        self.dashboard_queue = queue.Queue(maxsize=10)
        
        # Performance metrics
        self.message_count = 0
        self.message_count_lock = threading.Lock()
        
        # Setup signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.shutdown()
    
    def can_reception_and_processing_thread(self):
        """
        Thread 0: CAN RX + GPS + Lap Counter (CRITICAL PATH)
        
        Workflow (per your specification):
        1. Receive CAN message (byte array from firmware)
        2. Get GPS data from LTE modem (lat/lon)
        3. Feed GPS to lap counter → get LapData struct
        4. Modify byte array with lap counter data
        5. Queue modified byte array for parallel transmission & logging
        
        Target: < 50ms processing time per message (3 messages/second = 333ms period)
        """
        logger.info("CAN reception and processing thread started")
        
        # Set high priority for real-time processing (Linux only)
        try:
            os.nice(-10)  # Higher priority
        except:
            pass
        
        while self.running:
            try:
                start_time = time.time()
                
                # STEP 1: Receive CAN message (byte array from firmware)
                if self.can_interface:
                    byte_array = self.can_interface.receive_message(timeout=0.01)
                    
                    if not byte_array:
                        continue  # No message, continue loop
                else:
                    # Skeleton mode - simulate CAN byte array
                    byte_array = self._simulate_can_byte_array()
                    time.sleep(0.33)  # Simulate 3Hz rate
                
                # STEP 2: Get GPS data from LTE modem
                # TODO: Replace with actual EG25-G modem GPS interface
                lat, lon = self._get_gps_from_lte_modem()
                
                # STEP 3: Feed to lap counter, get LapData struct back
                lap_data = None
                if self.lap_counter and lat and lon:
                    # Lap counter returns: {lap_count, current_section, lap_duration}
                    lap_data = self.lap_counter.update_position(lat, lon)
                else:
                    # Skeleton mode simulation
                    lap_data = self._simulate_lap_data()
                
                # STEP 4: Modify byte array with lap counter data
                # TODO: Use sc1-data-format to properly encode into byte array
                modified_byte_array = self._inject_lap_data_into_byte_array(
                    byte_array, lap_data
                )
                
                # Package data for downstream threads
                processed_data = {
                    'byte_array': modified_byte_array,
                    'lap_data': lap_data,
                    'timestamp': time.time(),
                    'gps': {'lat': lat, 'lon': lon}
                }
                
                # STEP 5: Queue for parallel processing (non-blocking)
                # All downstream threads consume from processed_data_queue
                try:
                    self.processed_data_queue.put_nowait(processed_data)
                    
                    # Update message counter
                    with self.message_count_lock:
                        self.message_count += 1
                    
                except queue.Full:
                    logger.warning("Processed data queue full, dropping message")
                
                # Performance tracking
                processing_time = (time.time() - start_time) * 1000  # ms
                if processing_time > 50:
                    logger.warning(f"CAN processing took {processing_time:.1f}ms (target < 50ms)")
                
            except Exception as e:
                logger.error(f"CAN reception/processing thread error: {e}")
                time.sleep(0.1)
        
        logger.info("CAN reception and processing thread stopped")
    
    def lte_transmission_thread(self):
        """
        Thread 1: LTE transmission (cloud SQL upload)
        Parallel, non-blocking, with retry queue
        """
        logger.info("LTE transmission thread started")
        
        while self.running:
            try:
                # Get processed data from queue
                processed_data = self.processed_data_queue.get(timeout=1.0)
                
                # Send byte array over LTE to cloud
                # TODO: Integration with existing telemetry system (SQL transmission)
                byte_array = processed_data['byte_array']
                
                if self.can_interface:  # Replace with actual LTE interface
                    # Call existing C++ telemetry system via DTI interface
                    # self.telemetry_backend.send_sql(byte_array)
                    pass
                else:
                    logger.debug(f"Simulating LTE upload of {len(byte_array)} bytes")
                
                # Re-queue for other transmission paths
                try:
                    self.radio_tx_queue.put_nowait(processed_data)
                    self.can_tx_queue.put_nowait(processed_data)
                    self.csv_queue.put_nowait(processed_data)
                    self.dashboard_queue.put_nowait(processed_data)
                except queue.Full:
                    logger.warning("Downstream queue full")
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"LTE transmission thread error: {e}")
                time.sleep(0.1)
        
        logger.info("LTE transmission thread stopped")
    
    def radio_transmission_thread(self):
        """
        Thread 2: Radio transmission (RFD900A to chase car)
        Parallel, non-blocking, with retry queue
        """
        logger.info("Radio transmission thread started")
        
        while self.running:
            try:
                # Get processed data from radio queue
                processed_data = self.radio_tx_queue.get(timeout=1.0)
                
                # Send byte array over RFD900A radio (250 Kbps max)
                # TODO: Integration with existing telemetry system (UDP transmission)
                byte_array = processed_data['byte_array']
                
                if self.can_interface:  # Replace with actual radio interface
                    # Call existing C++ telemetry system via DTI interface
                    # self.telemetry_backend.send_udp(byte_array)
                    pass
                else:
                    logger.debug(f"Simulating radio TX of {len(byte_array)} bytes")
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Radio transmission thread error: {e}")
                time.sleep(0.1)
        
        logger.info("Radio transmission thread stopped")
    
    def can_transmission_thread(self):
        """
        Thread 3: CAN transmission (send modified byte array back to bus)
        Publishes lap counter data + future NN outputs back to CAN
        """
        logger.info("CAN transmission thread started")
        
        while self.running:
            try:
                # Get processed data from CAN TX queue
                processed_data = self.can_tx_queue.get(timeout=1.0)
                
                byte_array = processed_data['byte_array']
                lap_data = processed_data['lap_data']
                
                # Send modified byte array back to CAN bus
                if self.can_interface:
                    # Publish lap counter data
                    # CAN IDs: 0x400 (lap_count, current_section)
                    #          0x401 (lap_duration)
                    self.can_interface.send_lap_counter_data(lap_data)
                    
                    # Future: Send NN optimized power distribution
                    # self.can_interface.send_nn_output(nn_output)
                else:
                    logger.debug("Simulating CAN TX with lap data")
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"CAN transmission thread error: {e}")
                time.sleep(0.1)
        
        logger.info("CAN transmission thread stopped")
    
    def csv_logging_thread(self):
        """
        Thread 4: CSV data logging with async batch writes
        Low priority, I/O heavy operations
        
        Strategy: Accumulate messages for 1 second, then batch write to CSV
        This prevents I/O bottlenecks on the critical path
        """
        logger.info("CSV logging thread started")
        
        # Set lower priority for I/O operations (Linux only)
        try:
            os.nice(10)  # Lower priority
        except:
            pass
        
        batch_buffer = []
        last_write = time.time()
        batch_interval = 1.0  # Write every 1 second (30-50 messages at 3Hz)
        
        while self.running:
            try:
                # Accumulate messages into batch buffer
                try:
                    processed_data = self.csv_queue.get(timeout=0.1)
                    batch_buffer.append(processed_data)
                except queue.Empty:
                    pass
                
                current_time = time.time()
                
                # Batch write when interval elapsed or buffer getting large
                if (current_time - last_write >= batch_interval) or (len(batch_buffer) >= 100):
                    if batch_buffer:
                        if self.csv_logger:
                            # Call external CSV logger with batch
                            self.csv_logger.write_batch(batch_buffer)
                        else:
                            # Skeleton mode
                            logger.debug(f"Simulating CSV batch write of {len(batch_buffer)} messages")
                        
                        # Clear buffer and update timestamp
                        batch_buffer = []
                        last_write = current_time
                
            except Exception as e:
                logger.error(f"CSV logging thread error: {e}")
                time.sleep(0.1)
        
        # Write remaining buffer on shutdown
        if batch_buffer and self.csv_logger:
            try:
                self.csv_logger.write_batch(batch_buffer)
            except Exception as e:
                logger.error(f"Failed to write final CSV batch: {e}")
        
        logger.info("CSV logging thread stopped")
    
    def neural_network_buffer_thread(self):
        """
        Thread 5: Neural Network buffer accumulation (FUTURE)
        
        Strategy: Accumulate data points until threshold reached,
        then trigger NN inference for optimized power distribution
        
        Output: optimized_target_power (to be added to byte array)
        """
        logger.info("Neural network buffer thread started")
        
        while self.running:
            try:
                # Accumulate data into NN buffer
                # NOTE: This consumes from processed_data_queue separately
                # In future, may need dedicated queue to avoid race conditions
                
                # For now, just track buffer size
                with self.nn_buffer_lock:
                    buffer_size = len(self.nn_buffer)
                
                if buffer_size >= self.nn_buffer_threshold:
                    logger.info(f"NN buffer threshold reached ({buffer_size} samples)")
                    
                    # TODO: Trigger NN inference
                    # nn_output = self.neural_network.infer(self.nn_buffer)
                    # optimized_target_power = nn_output['target_power']
                    
                    # Clear buffer after inference
                    with self.nn_buffer_lock:
                        self.nn_buffer = []
                    
                    logger.info("NN inference complete, buffer cleared")
                
                time.sleep(1.0)  # Check buffer every second
                
            except Exception as e:
                logger.error(f"Neural network buffer thread error: {e}")
                time.sleep(1.0)
        
        logger.info("Neural network buffer thread stopped")
    
    def dashboard_update_thread(self):
        """
        Thread 6: Frontend dashboard update (LOW PRIORITY)
        
        Strategy: Update dashboard at 1Hz with latest lap counter values
        and race strategy outputs via JSON file for Textual frontend
        """
        logger.info("Dashboard update thread started")
        
        last_update = time.time()
        update_interval = 1.0  # 1Hz refresh rate
        
        # Dashboard state for diagnostics
        self.dashboard_state = {
            'system_status': 'STARTING',
            'errors': [],
            'warnings': []
        }
        
        while self.running:
            try:
                current_time = time.time()
                
                if current_time - last_update >= update_interval:
                    # Get latest data from dashboard queue (drain queue, keep most recent)
                    latest_data = None
                    try:
                        while True:
                            latest_data = self.dashboard_queue.get_nowait()
                    except queue.Empty:
                        pass
                    
                    if latest_data:
                        # Update telemetry_data.json for Textual frontend
                        self._update_telemetry_json(latest_data)
                        
                        lap_data = latest_data.get('lap_data', {})
                        logger.debug(f"Dashboard update: Lap {lap_data.get('lap_count', 0)}, "
                                   f"Section {lap_data.get('current_section', 0)}")
                    
                    # Always write system health status for diagnostics
                    self._update_system_health_json()
                    
                    last_update = current_time
                
                time.sleep(0.1)  # Prevent busy waiting
                
            except Exception as e:
                logger.error(f"Dashboard update thread error: {e}")
                self.dashboard_state['errors'].append(str(e))
                time.sleep(1.0)
        
        logger.info("Dashboard update thread stopped")
    
    def _update_telemetry_json(self, data: dict):
        """Write telemetry data to JSON file for Textual dashboard"""
        import json
        
        try:
            lap_data = data.get('lap_data', {})
            gps = data.get('gps', {})
            
            # Calculate lap time in human-readable format
            lap_duration_ms = lap_data.get('lap_duration', 0)
            lap_minutes = lap_duration_ms // 60000
            lap_seconds = (lap_duration_ms % 60000) / 1000.0
            
            # Build telemetry JSON matching Textual dashboard format
            telemetry = {
                # Lap counter data (NEW)
                'lap_count': lap_data.get('lap_count', 0),
                'current_section': lap_data.get('current_section', 0),
                'lap_duration_ms': lap_duration_ms,
                'lap_time_formatted': f"{int(lap_minutes)}:{lap_seconds:05.2f}",
                
                # GPS data
                'gps_latitude': gps.get('lat', 0.0),
                'gps_longitude': gps.get('lon', 0.0),
                
                # Simulated vehicle data (replace with actual CAN data)
                'speed': 45.0,  # TODO: Extract from CAN byte array
                'battery_soc': 85.0,
                'pack_voltage': 380.0,
                'pack_current': 25.0,
                
                # Network status (NEW)
                'lte_signal': self.dashboard_state.get('lte_signal', {
                    'connected': False, 'bars': 0, 'carrier': 'Unknown'
                }),
                'wifi_status': self.dashboard_state.get('wifi_status', {
                    'connected': False, 'bars': 0, 'ssid': 'Not Connected'
                }),
                
                # System status
                'timestamp': data.get('timestamp', time.time()),
                'system_status': self.dashboard_state['system_status'],
                'message_rate_hz': self._get_current_message_rate(),
                
                # Error/warning indicators for diagnostics
                'errors': self.dashboard_state['errors'][-5:],  # Last 5 errors
                'warnings': self.dashboard_state['warnings'][-5:],  # Last 5 warnings
            }
            
            # Write to telemetry_data.json (Textual dashboard reads this)
            with open('telemetry_data.json', 'w') as f:
                json.dump(telemetry, f, indent=2)
        
        except Exception as e:
            logger.error(f"Failed to write telemetry JSON: {e}")
    
    def _update_system_health_json(self):
        """Write system health status for diagnostic display"""
        import json
        
        try:
            with self.message_count_lock:
                total_messages = self.message_count
            
            uptime = time.time() - getattr(self, 'start_time', time.time())
            
            health = {
                'uptime_seconds': uptime,
                'total_messages': total_messages,
                'message_rate_hz': self._get_current_message_rate(),
                
                # Queue health (for diagnostics)
                'queues': {
                    'processed_data': self.processed_data_queue.qsize(),
                    'lte_tx': self.lte_tx_queue.qsize(),
                    'radio_tx': self.radio_tx_queue.qsize(),
                    'can_tx': self.can_tx_queue.qsize(),
                    'csv': self.csv_queue.qsize(),
                },
                
                # Thread health
                'threads_alive': sum(1 for t in self.threads.values() if t.is_alive()),
                'threads_total': len(self.threads),
                'thread_status': {
                    name: thread.is_alive() 
                    for name, thread in self.threads.items()
                },
                
                # Network status (detailed for diagnostics)
                'network': {
                    'lte': self.dashboard_state.get('lte_signal', {
                        'connected': False, 'bars': 0, 'carrier': 'Unknown', 'signal_dbm': -113
                    }),
                    'wifi': self.dashboard_state.get('wifi_status', {
                        'connected': False, 'bars': 0, 'ssid': 'Not Connected', 'signal_dbm': -100
                    })
                },
                
                # System state
                'system_status': self.dashboard_state['system_status'],
                'recent_errors': self.dashboard_state['errors'][-10:],
                'recent_warnings': self.dashboard_state['warnings'][-10:],
            }
            
            # Write to system_health.json for detailed diagnostics
            with open('system_health.json', 'w') as f:
                json.dump(health, f, indent=2)
        
        except Exception as e:
            logger.error(f"Failed to write system health JSON: {e}")
    
    def _get_current_message_rate(self) -> float:
        """Calculate current message processing rate"""
        with self.message_count_lock:
            total_messages = self.message_count
        
        uptime = time.time() - getattr(self, 'start_time', time.time())
        return round(total_messages / uptime, 2) if uptime > 0 else 0.0
    
    # ============================================================================
    # NETWORK MONITORING FUNCTIONS
    # ============================================================================
    
    def _get_lte_signal_strength(self) -> Dict[str, Any]:
        """Get LTE signal strength and carrier information"""
        try:
            # In skeleton mode, simulate LTE data
            if not EXTERNAL_MODULES_AVAILABLE:
                import random
                # Simulate varying signal strength
                rssi = random.randint(10, 25)
                carriers = ["Verizon", "AT&T", "T-Mobile", "US Cellular"]
                return {
                    'connected': True,
                    'rssi': rssi,
                    'bars': self._rssi_to_bars(rssi),
                    'carrier': random.choice(carriers),
                    'signal_dbm': -113 + (2 * rssi)  # Convert RSSI to approximate dBm
                }
            
            # Real implementation for EG25-G module
            # TODO: Implement when LTE modem module is available
            # signal_response = send_at_command("AT+CSQ")
            # carrier_response = send_at_command("AT+COPS?")
            # return parse_lte_responses(signal_response, carrier_response)
            
            return {
                'connected': False,
                'rssi': 0,
                'bars': 0,
                'carrier': "No Module",
                'signal_dbm': -113
            }
            
        except Exception as e:
            logger.warning(f"Failed to get LTE signal: {e}")
            return {
                'connected': False,
                'rssi': 0,
                'bars': 0,
                'carrier': "Error",
                'signal_dbm': -113
            }
    
    def _get_wifi_status(self) -> Dict[str, Any]:
        """Get current WiFi connection status"""
        try:
            # Check if we're on Linux (Pi) or Windows (development)
            if os.name == 'nt':  # Windows - simulate
                import random
                networks = ["HomeNetwork", "OfficeWiFi", "PublicHotspot", "DevNetwork"]
                connected = random.choice([True, False])
                return {
                    'connected': connected,
                    'ssid': random.choice(networks) if connected else "Not Connected",
                    'signal_dbm': random.randint(-80, -30) if connected else -100,
                    'bars': random.randint(1, 4) if connected else 0
                }
            
            # Linux implementation - use nmcli
            result = subprocess.run(
                ['nmcli', '-t', '-f', 'active,ssid', 'dev', 'wifi'],
                capture_output=True, text=True, timeout=2
            )
            
            # Find active connection
            for line in result.stdout.split('\n'):
                if line.startswith('yes:'):
                    ssid = line.split(':', 1)[1]
                    signal_dbm = self._get_wifi_signal_dbm()
                    return {
                        'connected': True,
                        'ssid': ssid,
                        'signal_dbm': signal_dbm,
                        'bars': self._dbm_to_bars(signal_dbm)
                    }
            
            return {
                'connected': False,
                'ssid': "Not Connected",
                'signal_dbm': -100,
                'bars': 0
            }
            
        except Exception as e:
            logger.warning(f"Failed to get WiFi status: {e}")
            return {
                'connected': False,
                'ssid': "Error",
                'signal_dbm': -100,
                'bars': 0
            }
    
    def _get_wifi_signal_dbm(self) -> int:
        """Get WiFi signal strength in dBm"""
        try:
            result = subprocess.run(
                ['iwconfig'],
                capture_output=True, text=True, timeout=2
            )
            
            # Parse signal level from iwconfig output
            signal_match = re.search(r'Signal level=(-?\d+)', result.stdout)
            if signal_match:
                return int(signal_match.group(1))
            
            return -70  # Default moderate signal
            
        except Exception:
            return -70  # Default if iwconfig fails
    
    def _rssi_to_bars(self, rssi: int) -> int:
        """Convert LTE RSSI (0-31) to signal bars (0-4)"""
        if rssi == 99 or rssi == 0:
            return 0  # No signal
        elif rssi >= 20:
            return 4  # Excellent (>= -93 dBm)
        elif rssi >= 15:
            return 3  # Good (-103 to -93 dBm)
        elif rssi >= 10:
            return 2  # Fair (-103 to -109 dBm)
        elif rssi >= 5:
            return 1  # Poor (-109 to -113 dBm)
        else:
            return 0  # Very poor (< -113 dBm)
    
    def _dbm_to_bars(self, dbm: int) -> int:
        """Convert WiFi signal strength (dBm) to bars (0-4)"""
        if dbm >= -50:
            return 4  # Excellent
        elif dbm >= -60:
            return 3  # Good
        elif dbm >= -70:
            return 2  # Fair
        elif dbm >= -80:
            return 1  # Poor
        else:
            return 0  # Very poor or disconnected
    
    def _update_network_status(self):
        """Update network status information for dashboard"""
        try:
            # Get LTE and WiFi status
            lte_status = self._get_lte_signal_strength()
            wifi_status = self._get_wifi_status()
            
            # Update dashboard state with network info
            self.dashboard_state.update({
                'lte_signal': lte_status,
                'wifi_status': wifi_status
            })
            
            # Log network status occasionally
            logger.debug(f"Network status - LTE: {lte_status['bars']} bars ({lte_status['carrier']}), "
                        f"WiFi: {wifi_status['bars']} bars ({wifi_status['ssid']})")
            
        except Exception as e:
            logger.warning(f"Failed to update network status: {e}")

    def system_management_thread(self):
        """
        Thread 7: System management and health monitoring
        Variable priority, low frequency monitoring
        """
        logger.info("System management thread started")
        
        last_stats_update = time.time()
        last_network_update = time.time()
        stats_interval = 10.0  # 10 second intervals
        network_interval = 10.0  # 10 second intervals for network status
        
        while self.running:
            try:
                current_time = time.time()
                
                # Performance monitoring
                if current_time - last_stats_update >= stats_interval:
                    self._log_performance_stats()
                    last_stats_update = current_time
                
                # Network status monitoring
                if current_time - last_network_update >= network_interval:
                    self._update_network_status()
                    last_network_update = current_time
                
                # System health checks
                self._perform_health_checks()
                
                time.sleep(1.0)  # Low frequency management tasks
                
            except Exception as e:
                logger.error(f"System management thread error: {e}")
                time.sleep(1.0)
        
        logger.info("System management thread stopped")
    
    # ============================================================================
    # HELPER METHODS FOR CAN PROCESSING PIPELINE
    # ============================================================================
    
    def _simulate_can_byte_array(self) -> bytes:
        """Skeleton mode: simulate CAN byte array from firmware"""
        import struct
        import random
        
        # Simulate firmware byte array (example structure)
        # In reality, this comes from sc1-data-format binary structure
        speed = random.uniform(0, 120)  # km/h
        voltage = random.uniform(350, 400)  # V
        current = random.uniform(0, 50)  # A
        
        # Pack into byte array (example: 12 bytes)
        byte_array = struct.pack('<fff', speed, voltage, current)
        return byte_array
    
    def _get_gps_from_lte_modem(self) -> tuple:
        """Get GPS coordinates from EG25-G LTE modem
        
        Returns:
            tuple: (latitude, longitude) or (None, None) if unavailable
        """
        # TODO: Implement actual EG25-G GNSS interface
        # Command: AT+QGPSLOC? to get GPS location
        # Parse NMEA format: +QGPSLOC: <UTC>,<latitude>,<longitude>,...
        
        # Skeleton mode: simulate GPS coordinates (example: ASC race track)
        import random
        lat = 43.0731 + random.uniform(-0.001, 0.001)  # Madison, WI area
        lon = -89.4012 + random.uniform(-0.001, 0.001)
        
        return (lat, lon)
    
    def _simulate_lap_data(self) -> dict:
        """Skeleton mode: simulate lap counter output"""
        import random
        
        return {
            'lap_count': random.randint(1, 5),
            'current_section': random.randint(1, 10),
            'lap_duration': random.randint(60000, 300000)  # ms (1-5 minutes)
        }
    
    def _inject_lap_data_into_byte_array(self, byte_array: bytes, lap_data: dict) -> bytes:
        """Modify byte array with lap counter data
        
        Args:
            byte_array: Original byte array from firmware
            lap_data: Dict with lap_count, current_section, lap_duration
        
        Returns:
            Modified byte array with lap data injected
        """
        import struct
        
        if not lap_data:
            return byte_array
        
        # TODO: Use sc1-data-format to properly encode lap counter signals
        # For now, append lap data to end of byte array
        
        # Format from your specification:
        # "lap_count": [2, "uint16", "", 0, 9999, "Software;Lap Counter"]
        # "current_section": [1, "uint8", "", 0, 255, "Software;Lap Counter"]
        # "lap_duration": [4, "uint32", "ms", 0, 600000, "Software;Lap Counter"]
        
        lap_count = lap_data.get('lap_count', 0)
        current_section = lap_data.get('current_section', 0)
        lap_duration = lap_data.get('lap_duration', 0)
        
        # Pack lap data: uint16 (2 bytes) + uint8 (1 byte) + uint32 (4 bytes) = 7 bytes
        lap_bytes = struct.pack('<HBI', lap_count, current_section, lap_duration)
        
        # Append to original byte array
        modified_byte_array = byte_array + lap_bytes
        
        return modified_byte_array
    
    def _log_performance_stats(self):
        """Log system performance statistics"""
        with self.message_count_lock:
            total_messages = self.message_count
        
        uptime = time.time() - getattr(self, 'start_time', time.time())
        message_rate = total_messages / uptime if uptime > 0 else 0
        
        stats = {
            'uptime_sec': round(uptime, 1),
            'total_messages': total_messages,
            'message_rate_hz': round(message_rate, 2),
            'processed_queue': self.processed_data_queue.qsize(),
            'lte_queue': self.lte_tx_queue.qsize(),
            'radio_queue': self.radio_tx_queue.qsize(),
            'can_tx_queue': self.can_tx_queue.qsize(),
            'csv_queue': self.csv_queue.qsize(),
            'nn_buffer_size': len(self.nn_buffer) if hasattr(self, 'nn_buffer') else 0,
            'threads_alive': sum(1 for t in self.threads.values() if t.is_alive())
        }
        logger.info(f"Performance Stats: {stats}")
    
    def _perform_health_checks(self):
        """Perform system health checks"""
        # Check queue sizes for bottlenecks
        if self.processed_data_queue.qsize() > 80:
            logger.warning(f"Processed data queue getting full: {self.processed_data_queue.qsize()}/100")
            self.dashboard_state['warnings'].append(f"Processed queue at {self.processed_data_queue.qsize()}/100")
        
        if self.csv_queue.qsize() > 400:
            logger.warning(f"CSV queue getting full: {self.csv_queue.qsize()}/500")
            self.dashboard_state['warnings'].append(f"CSV queue at {self.csv_queue.qsize()}/500")
        
        # Check thread health
        critical_threads = ['can_reception', 'lte_tx', 'radio_tx', 'can_tx']
        dead_threads = []
        for name in critical_threads:
            thread = self.threads.get(name)
            if thread and not thread.is_alive():
                logger.error(f"CRITICAL: Thread {name} is not alive!")
                self.dashboard_state['errors'].append(f"Thread {name} crashed")
                dead_threads.append(name)
        
        # Check message processing rate
        with self.message_count_lock:
            current_count = self.message_count
        
        expected_rate = 3.0  # 3 messages/second
        uptime = time.time() - getattr(self, 'start_time', time.time())
        actual_rate = current_count / uptime if uptime > 0 else 0
        
        if actual_rate < expected_rate * 0.5 and uptime > 10:
            logger.warning(f"Message processing rate low: {actual_rate:.2f} Hz (expected {expected_rate} Hz)")
            self.dashboard_state['warnings'].append(f"Low message rate: {actual_rate:.2f} Hz")
        
        # Update system status based on health checks
        if dead_threads or actual_rate < 0.5:
            self.dashboard_state['system_status'] = 'ERROR'
        elif self.dashboard_state['warnings']:
            self.dashboard_state['system_status'] = 'WARNING'
        else:
            self.dashboard_state['system_status'] = 'RUNNING'
    
    def start(self):
        """Start all system threads"""
        logger.info("Starting Driver IO System...")
        
        self.running = True
        self.start_time = time.time()
        
        # Initialize dashboard state
        self.dashboard_state = {
            'system_status': 'STARTING',
            'errors': [],
            'warnings': [],
            'lte_signal': {'connected': False, 'bars': 0, 'carrier': 'Starting...'},
            'wifi_status': {'connected': False, 'bars': 0, 'ssid': 'Starting...'}
        }
        
        # Create and start threads (in priority order)
        self.threads['can_reception'] = threading.Thread(
            target=self.can_reception_and_processing_thread,
            name="CAN-RX-PROC",
            daemon=True
        )
        
        self.threads['lte_tx'] = threading.Thread(
            target=self.lte_transmission_thread,
            name="LTE-TX",
            daemon=True
        )
        
        self.threads['radio_tx'] = threading.Thread(
            target=self.radio_transmission_thread,
            name="RADIO-TX",
            daemon=True
        )
        
        self.threads['can_tx'] = threading.Thread(
            target=self.can_transmission_thread,
            name="CAN-TX",
            daemon=True
        )
        
        self.threads['csv_logging'] = threading.Thread(
            target=self.csv_logging_thread,
            name="CSV-LOG",
            daemon=True
        )
        
        self.threads['nn_buffer'] = threading.Thread(
            target=self.neural_network_buffer_thread,
            name="NN-BUF",
            daemon=True
        )
        
        self.threads['dashboard'] = threading.Thread(
            target=self.dashboard_update_thread,
            name="DASHBOARD",
            daemon=True
        )
        
        self.threads['system_management'] = threading.Thread(
            target=self.system_management_thread,
            name="SYS-MGR",
            daemon=True
        )
        
        # Start all threads
        for thread in self.threads.values():
            thread.start()
        
        logger.info("All threads started successfully")
        logger.info("Driver IO System is running...")
        logger.info("Expected CAN message rate: 3 Hz")
        logger.info("Pipeline: CAN RX -> GPS -> Lap Counter -> Modify Array -> [LTE|Radio|CAN TX|CSV|NN Buffer|Dashboard]")
    
    def shutdown(self):
        """Shutdown all system components"""
        logger.info("Shutting down Driver IO System...")
        
        self.running = False
        
        # Wait for threads to finish
        for name, thread in self.threads.items():
            logger.info(f"Waiting for {name} thread to stop...")
            thread.join(timeout=5.0)
            if thread.is_alive():
                logger.warning(f"{name} thread did not stop gracefully")
        
        # Cleanup external modules
        if self.can_interface:
            self.can_interface.shutdown()
        if self.csv_logger:
            self.csv_logger.shutdown()
        
        logger.info("Driver IO System shutdown complete")

def main():
    """Main entry point"""
    logger.info("SC2 Driver IO System Starting...")
    
    # Create and start the system
    system = DriverIOSystem()
    
    try:
        system.start()
        
        # Keep main thread alive
        while system.running:
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        system.shutdown()
        logger.info("SC2 Driver IO System stopped")

if __name__ == "__main__":
    main()