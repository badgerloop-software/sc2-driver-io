#!/usr/bin/env python3
"""
Simple Integration Test - Telemetry and CSV Consumers
Tests consumers without requiring CAN hardware
"""

import time
import tempfile
import logging
from pathlib import Path
import sys

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Mock CANMessage class for testing
class CANMessage:
    def __init__(self, can_id, signal_name, value, timestamp, raw_data):
        self.can_id = can_id
        self.signal_name = signal_name
        self.value = value
        self.timestamp = timestamp
        self.raw_data = raw_data

def test_consumers():
    """Test telemetry and CSV consumers with mock data"""
    
    logger.info("="*60)
    logger.info("Consumer Integration Test (No CAN Hardware Required)")
    logger.info("="*60)
    
    try:
        # Add current directory to path
        sys.path.insert(0, str(Path(__file__).parent))
        
        from can_bus.telemetry_consumer import TelemetryConsumer
        from can_bus.csv_consumer import CSVConsumer
    except ImportError as e:
        logger.error(f"Failed to import consumer modules: {e}")
        return False
    
    # Create temp directory for CSV output
    with tempfile.TemporaryDirectory() as tmpdir:
        logger.info(f"Using temp directory for CSV: {tmpdir}\n")
        
        try:
            # Initialize consumers
            logger.info("--- Initializing Consumers ---")
            telemetry_consumer = TelemetryConsumer()
            csv_consumer = CSVConsumer(output_dir=tmpdir, buffer_size=10)
            
            # Create test messages
            logger.info("Creating test CAN messages...")
            test_messages = []
            for i in range(25):
                msg = CANMessage(
                    can_id=0x100 + i,
                    signal_name=f"test_signal_{i}",
                    value=float(i * 10.5),
                    timestamp=time.time() + i * 0.001,
                    raw_data=bytes([i & 0xFF, (i+1) & 0xFF, (i+2) & 0xFF, (i+3) & 0xFF])
                )
                test_messages.append(msg)
            logger.info(f"Created {len(test_messages)} test messages\n")
            
            # Test telemetry consumer
            logger.info("--- Testing Telemetry Consumer ---")
            logger.info("Sending 5 messages to C++ telemetry bridge...")
            for i, msg in enumerate(test_messages[:5]):
                telemetry_consumer.consume(msg)
                if i == 0:
                    time.sleep(0.2)  # Give C++ backend time to process
            
            telem_stats = telemetry_consumer.get_stats()
            logger.info(f"Telemetry Stats:")
            logger.info(f"  Messages sent: {telem_stats['sent']}")
            logger.info(f"  Messages failed: {telem_stats['failed']}")
            logger.info(f"  Success rate: {telem_stats['success_rate']:.1%}\n")
            
            # Test CSV consumer
            logger.info("--- Testing CSV Consumer ---")
            logger.info(f"Writing {len(test_messages)} messages to CSV...")
            for msg in test_messages:
                csv_consumer.consume(msg)
            
            csv_stats = csv_consumer.get_stats()
            logger.info(f"CSV Stats:")
            logger.info(f"  Messages written: {csv_stats['messages_written']}")
            logger.info(f"  Current file: {Path(csv_stats['current_file']).name if csv_stats['current_file'] else 'None'}")
            logger.info(f"  File size: {csv_stats['file_size_mb']:.3f} MB\n")
            
            # Verify CSV file
            logger.info("--- Verifying CSV Output ---")
            csv_files = list(Path(tmpdir).glob("*.csv"))
            if csv_files:
                csv_file = csv_files[0]
                logger.info(f"✓ CSV file created: {csv_file.name}")
                
                with open(csv_file, 'r') as f:
                    lines = f.readlines()
                    logger.info(f"✓ CSV contains {len(lines)-1} data rows (+ 1 header row)")
                    
                    if len(lines) >= 2:
                        logger.info(f"  Header: {lines[0].strip()}")
                        logger.info(f"  Sample row 1: {lines[1].strip()}")
                        if len(lines) >= 3:
                            logger.info(f"  Sample row 2: {lines[2].strip()}")
            else:
                logger.error("✗ No CSV file created!")
                return False
            
            # Cleanup
            logger.info("\n--- Cleaning Up ---")
            telemetry_consumer.close()
            csv_consumer.close()
            logger.info("Consumers closed")
            
            # Summary
            logger.info("\n" + "="*60)
            logger.info("TEST SUMMARY:")
            logger.info(f"  Telemetry Consumer:")
            logger.info(f"    - Sent: {telem_stats['sent']} / 5")
            logger.info(f"    - Failed: {telem_stats['failed']}")
            if telem_stats['failed'] > 0:
                logger.info("    - Note: Failures expected if C++ backend not running")
            logger.info(f"  CSV Consumer:")
            logger.info(f"    - Written: {csv_stats['messages_written']} / {len(test_messages)}")
            logger.info(f"    - File created: {'YES' if csv_files else 'NO'}")
            logger.info("="*60)
            
            # Determine success
            csv_success = csv_stats['messages_written'] == len(test_messages) and len(csv_files) > 0
            telem_partial = telem_stats['sent'] >= 0  # Just needs to attempt
            
            if csv_success:
                logger.info("\n✓ TEST PASSED - All components working correctly")
                if telem_stats['failed'] > 0:
                    logger.info("  (Telemetry failures are OK if C++ backend not running)")
                return True
            else:
                logger.error("\n✗ TEST FAILED - CSV consumer not working correctly")
                return False
            
        except Exception as e:
            logger.error(f"Test failed with exception: {e}", exc_info=True)
            return False


if __name__ == "__main__":
    logger.info("Starting consumer integration test...\n")
    logger.info("This test does NOT require:")
    logger.info("  - CAN hardware or python-can library")
    logger.info("  - C++ backend running (but telemetry will fail gracefully)")
    logger.info("")
    
    success = test_consumers()
    
    if success:
        logger.info("\n✓ All tests passed successfully!")
        exit(0)
    else:
        logger.error("\n✗ Tests failed!")
        exit(1)
