#!/usr/bin/env python3
"""
SC2 Driver IO - Main Application Coordinator
Multi-threaded coordinator for Solar Car 2 driver IO system

Architecture:
- Single CAN reader with fan-out to multiple consumers
- Consumers: Telemetry (C++ bridge), CSV Logger, Lap Counter
- C++ telemetry system receives data via Unix socket
- Real-time priority for CAN reception
"""

import threading
import time
import queue
import signal
import sys
import os
import logging
import json
import subprocess
from typing import Optional, Dict, Any
from pathlib import Path

# CAN bus and consumer imports
try:
    from can_bus.can_reader import CANReader
    from can_bus.telemetry_consumer import TelemetryConsumer
    from can_bus.csv_consumer import CSVConsumer
    from can_bus.ui_consumer import UIConsumer
    from can_bus.lap_counter_consumer import LapCounterConsumer
    CAN_AVAILABLE = True
except ImportError as e:
    print(f"WARNING: CAN modules not available: {e}")
    CAN_AVAILABLE = False

# Lap counter import (legacy - now using lap_counter_consumer)
try:
    from lap_counter.lap_counter import LapCounter
    LAP_COUNTER_AVAILABLE = True
except ImportError:
    print("WARNING: Lap counter not available")
    LAP_COUNTER_AVAILABLE = False

# Shared memory import for UI
try:
    from core.ipc.shared_data import SharedTelemetryWriter, TelemetrySnapshot
    SHARED_MEMORY_AVAILABLE = True
except ImportError:
    print("WARNING: Shared memory module not available")
    SHARED_MEMORY_AVAILABLE = False

# Custom log handler for dashboard integration
class DashboardLogHandler(logging.Handler):
    """Custom log handler that writes to shared file for dashboard"""
    
    def __init__(self, log_file_path):
        super().__init__()
        self.log_file_path = Path(log_file_path)
        self.messages = []
        self.max_messages = 100
    
    def emit(self, record):
        try:
            log_entry = {
                'timestamp': record.created,
                'level': record.levelname,
                'message': self.format(record)
            }
            
            # Keep only last max_messages
            self.messages.append(log_entry)
            if len(self.messages) > self.max_messages:
                self.messages = self.messages[-self.max_messages:]
            
            # Write to file atomically
            with open(self.log_file_path, 'w') as f:
                json.dump({'messages': self.messages}, f)
        except Exception:
            pass

# Configure logging
log_file = Path(__file__).parent / 'dashboard_logs.json'
dashboard_handler = DashboardLogHandler(log_file)
dashboard_handler.setLevel(logging.DEBUG)
dashboard_handler.setFormatter(logging.Formatter('%(name)s - %(message)s'))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[dashboard_handler]
)
logger = logging.getLogger(__name__)

class DriverIOSystem:
    """Main driver IO system coordinator with CAN fan-out architecture"""
    
    def __init__(self, can_channel: str = "can0", csv_output_dir: str = "/media/usb/can_logs"):
        self.running = False
        self.threads = {}
        self.dashboard_process = None
        
        # Initialize CAN reader with fan-out architecture
        self.can_reader = None
        self.telemetry_consumer = None
        self.csv_consumer = None
        self.ui_consumer = None
        self.lap_counter_consumer = None
        self.lap_counter = None  # Legacy, if needed
        self.shared_memory = None
        
        # Track latest telemetry values for shared memory
        self.current_telemetry = TelemetrySnapshot() if SHARED_MEMORY_AVAILABLE else None
        
        if CAN_AVAILABLE:
            try:
                # Create single CAN reader
                self.can_reader = CANReader(channel=can_channel, bustype="socketcan")
                
                # Create consumers
                self.telemetry_consumer = TelemetryConsumer()
                self.csv_consumer = CSVConsumer(output_dir=csv_output_dir)
                
                # Create UI consumer if shared memory is available
                if SHARED_MEMORY_AVAILABLE:
                    try:
                        self.ui_consumer = UIConsumer(update_rate_hz=10.0)
                        logger.info("UI consumer initialized")
                    except Exception as e:
                        logger.warning(f"Failed to create UI consumer: {e}")
                
                # Create lap counter consumer
                if LAP_COUNTER_AVAILABLE:
                    try:
                        self.lap_counter_consumer = LapCounterConsumer(
                            line_start=(40.1106, -88.2073),  # TODO: Load from config
                            line_end=(40.1108, -88.2073),
                            channel=can_channel
                        )
                        logger.info("Lap counter consumer initialized")
                    except Exception as e:
                        logger.warning(f"Failed to create lap counter consumer: {e}")
                
                # Register consumers with CAN reader
                self.can_reader.register_consumer(
                    "telemetry",
                    self.telemetry_consumer.consume,
                    queue_size=2000  # High priority, large buffer
                )
                
                self.can_reader.register_consumer(
                    "csv_logger",
                    self.csv_consumer.consume,
                    queue_size=5000  # Lower priority, larger buffer
                )
                
                # Register UI consumer if available
                if self.ui_consumer:
                    self.can_reader.register_consumer(
                        "ui_display",
                        self.ui_consumer.consume,
                        queue_size=1000  # UI doesn't need huge buffer
                    )
                
                # Register lap counter consumer if available
                if self.lap_counter_consumer:
                    self.can_reader.register_consumer(
                        "lap_counter",
                        self.lap_counter_consumer.consume,
                        queue_size=500,  # GPS updates are infrequent
                        filter_ids=[0x210, 0x211]  # Only GPS CAN IDs (adjust based on format.json)
                    )
                
                logger.info("CAN reader initialized with all consumers")
                
            except Exception as e:
                logger.error(f"Failed to initialize CAN system: {e}")
                self.can_reader = None
        
        # Initialize lap counter if available
        if LAP_COUNTER_AVAILABLE:
            try:
                self.lap_counter = LapCounter()
                logger.info("Lap counter initialized")
            except Exception as e:
                logger.error(f"Failed to initialize lap counter: {e}")
        
        # Initialize shared memory for UI if available
        if SHARED_MEMORY_AVAILABLE:
            try:
                self.shared_memory = SharedTelemetryWriter()
                logger.info("Shared memory initialized for UI communication")
            except Exception as e:
                logger.error(f"Failed to initialize shared memory: {e}")
        
        # Setup signal handlers for clean shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.shutdown()
    
    def status_monitoring_thread(self):
        """Monitor system status and log statistics"""
        logger.info("Status monitoring thread started")
        
        last_stats_time = time.time()
        stats_interval = 10.0  # 10 second intervals
        
        while self.running:
            try:
                current_time = time.time()
                
                if current_time - last_stats_time >= stats_interval:
                    # Get CAN reader stats
                    if self.can_reader:
                        can_stats = self.can_reader.get_stats()
                        logger.info(f"CAN Reader Stats: {can_stats}")
                    
                    # Get consumer stats
                    if self.telemetry_consumer:
                        telem_stats = self.telemetry_consumer.get_stats()
                        logger.info(f"Telemetry Consumer: {telem_stats}")
                    
                    if self.csv_consumer:
                        csv_stats = self.csv_consumer.get_stats()
                        logger.info(f"CSV Consumer: {csv_stats}")
                    
                    if self.ui_consumer:
                        ui_stats = self.ui_consumer.get_stats()
                        logger.info(f"UI Consumer: {ui_stats}")
                    
                    if self.lap_counter_consumer:
                        lap_stats = self.lap_counter_consumer.get_stats()
                        logger.info(f"Lap Counter: {lap_stats}")
                    
                    last_stats_time = current_time
                
                time.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Status monitoring error: {e}")
                time.sleep(1.0)
        
        logger.info("Status monitoring thread stopped")
        """Perform system health checks"""
        # Check queue sizes
        if self.can_message_queue.qsize() > 800:
            logger.warning("CAN message queue getting full")
        
        if self.telemetry_queue.qsize() > 150:
            logger.warning("Telemetry queue getting full")
        
        # Check thread health
        for name, thread in self.threads.items():
            if not thread.is_alive():
                logger.error(f"Thread {name} is not alive!")
    
    def _process_telemetry_queue(self):
        """Process telemetry data and coordinate with C++ backend"""
        try:
            while True:
                try:
                    data_type, data = self.telemetry_queue.get_nowait()
                    
                    # TODO: Integration with existing C++ telemetry system
                    # This is where we'd call into the preserved C++ backend
                    logger.debug(f"Processing telemetry: {data_type}")
                    
                except queue.Empty:
                    break
        except Exception as e:
            logger.error(f"Telemetry processing error: {e}")
    
    def start(self, with_dashboard: bool = False):
        """Start all system components"""
        logger.info("Starting Driver IO System...")
        
        # Start C++ telemetry backend
        self._start_cpp_backend()
        
        # Launch the textual dashboard if requested
        if with_dashboard:
            dashboard_script = Path(__file__).parent.parent / 'textual_frontend' / 'textual_dashboard.py'
            if dashboard_script.exists():
                logger.info("Launching Textual Dashboard...")
                try:
                    self.dashboard_process = subprocess.Popen(
                        [sys.executable, str(dashboard_script)],
                        cwd=str(dashboard_script.parent)
                    )
                    logger.info("Dashboard launched successfully")
                    time.sleep(1)  # Give dashboard time to start
                except Exception as e:
                    logger.error(f"Failed to launch dashboard: {e}")
            else:
                logger.warning("Dashboard script not found, running without UI")
        
        self.running = True
        self.start_time = time.time()
        
        # Start CAN reader (runs in its own threads with consumers)
        if self.can_reader:
            self.can_reader.start()
            logger.info("CAN reader and consumers started")
        
        # Create and start monitoring thread
        self.threads['status_monitor'] = threading.Thread(
            target=self.status_monitoring_thread,
            name="STATUS-MON",
            daemon=True
        )
        
        # Start threads
        for thread in self.threads.values():
            thread.start()
        
        logger.info("All threads started successfully")
        logger.info("Driver IO System is running...")
    
    def _start_cpp_backend(self):
        """Start the C++ telemetry backend if not already running"""
        try:
            # Check if C++ backend socket exists
            import socket
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            try:
                sock.sendto(b'', '/tmp/sc2_can_bridge.sock')
                logger.info("C++ telemetry backend already running")
                sock.close()
                return
            except:
                sock.close()
            
            # Start C++ backend
            cpp_binary = Path(__file__).parent.parent / "build" / "sc2-driver-io"
            if cpp_binary.exists():
                logger.info("Starting C++ telemetry backend...")
                self.cpp_backend_process = subprocess.Popen(
                    [str(cpp_binary)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                time.sleep(2)  # Give it time to initialize
                logger.info("C++ telemetry backend started")
            else:
                logger.warning(f"C++ backend not found at {cpp_binary}")
                logger.warning("Telemetry will not be sent to C++ system")
                
        except Exception as e:
            logger.error(f"Failed to start C++ backend: {e}")
    
    def shutdown(self):
        """Shutdown all system components"""
        logger.info("Shutting down Driver IO System...")
        
        self.running = False
        
        # Stop CAN reader
        if self.can_reader:
            logger.info("Stopping CAN reader...")
            self.can_reader.stop()
        
        # Close consumers
        if self.telemetry_consumer:
            self.telemetry_consumer.close()
        if self.csv_consumer:
            self.csv_consumer.close()
        if self.ui_consumer:
            self.ui_consumer.close()
        if self.lap_counter_consumer:
            self.lap_counter_consumer.close()
        
        # Terminate dashboard process
        if self.dashboard_process:
            logger.info("Shutting down dashboard...")
            try:
                self.dashboard_process.terminate()
                self.dashboard_process.wait(timeout=5)
            except Exception as e:
                logger.warning(f"Error shutting down dashboard: {e}")
                try:
                    self.dashboard_process.kill()
                except:
                    pass
        
        # Terminate C++ backend
        if hasattr(self, 'cpp_backend_process') and self.cpp_backend_process:
            logger.info("Shutting down C++ telemetry backend...")
            try:
                self.cpp_backend_process.terminate()
                self.cpp_backend_process.wait(timeout=5)
            except:
                try:
                    self.cpp_backend_process.kill()
                except:
                    pass
        
        # Wait for threads to finish
        for name, thread in self.threads.items():
            logger.info(f"Waiting for {name} thread to stop...")
            thread.join(timeout=5.0)
            if thread.is_alive():
                logger.warning(f"{name} thread did not stop gracefully")
        
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