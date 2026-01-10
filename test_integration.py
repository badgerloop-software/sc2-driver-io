#!/usr/bin/env python3
"""
Integration Test - Full CAN Pipeline
Tests: CAN Reader → Consumers → Telemetry Bridge → C++ Backend
"""

import time
import tempfile
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_can_pipeline():
    """Test the complete CAN data pipeline"""
    
    logger.info("="*60)
    logger.info("CAN Pipeline Integration Test")
    logger.info("="*60)
    
    try:
        from can_bus.can_reader import CANReader, CANMessage
        from can_bus.telemetry_consumer import TelemetryConsumer
        from can_bus.csv_consumer import CSVConsumer
    except ImportError as e:
        logger.error(f"Failed to import CAN modules: {e}")
        logger.error("Make sure you're running from the sc2-driver-io directory")
        return False
    
    # Create temp directory for CSV output
    with tempfile.TemporaryDirectory() as tmpdir:
        logger.info(f"Using temp directory for CSV: {tmpdir}")
        
        try:
            # Initialize consumers
            logger.info("Initializing consumers...")
            telemetry_consumer = TelemetryConsumer()
            csv_consumer = CSVConsumer(output_dir=tmpdir, buffer_size=10)
            
            # Create test messages
            logger.info("Creating test CAN messages...")
            test_messages = []
            for i in range(20):
                msg = CANMessage(
                    can_id=0x100 + i,
                    signal_name=f"test_signal_{i}",
                    value=float(i * 10),
                    timestamp=time.time(),
                    raw_data=bytes([i, i+1, i+2, i+3])
                )
                test_messages.append(msg)
            
            # Test telemetry consumer
            logger.info("\n--- Testing Telemetry Consumer ---")
            for i, msg in enumerate(test_messages[:5]):
                telemetry_consumer.consume(msg)
                if i == 0:
                    time.sleep(0.5)  # Give C++ backend time to process
            
            telem_stats = telemetry_consumer.get_stats()
            logger.info(f"Telemetry stats: {telem_stats}")
            
            # Test CSV consumer
            logger.info("\n--- Testing CSV Consumer ---")
            for msg in test_messages:
                csv_consumer.consume(msg)
            
            csv_stats = csv_consumer.get_stats()
            logger.info(f"CSV stats: {csv_stats}")
            
            # Check CSV file
            csv_files = list(Path(tmpdir).glob("*.csv"))
            if csv_files:
                logger.info(f"✓ CSV file created: {csv_files[0].name}")
                with open(csv_files[0], 'r') as f:
                    lines = f.readlines()
                    logger.info(f"✓ CSV contains {len(lines)-1} data rows (+ 1 header)")
                    if len(lines) > 1:
                        logger.info(f"  Sample row: {lines[1].strip()}")
            else:
                logger.error("✗ No CSV file created")
            
            # Cleanup
            logger.info("\n--- Cleaning up ---")
            telemetry_consumer.close()
            csv_consumer.close()
            
            logger.info("\n" + "="*60)
            logger.info("Test Summary:")
            logger.info(f"  Telemetry sent: {telem_stats['sent']} / {len(test_messages[:5])}")
            logger.info(f"  CSV written: {csv_stats['messages_written']} / {len(test_messages)}")
            logger.info(f"  CSV file size: {csv_stats['file_size_mb']:.3f} MB")
            logger.info("="*60)
            
            # Determine success
            success = (
                telem_stats['sent'] >= 1 and  # At least some messages sent
                csv_stats['messages_written'] == len(test_messages)  # All messages logged
            )
            
            if success:
                logger.info("✓ TEST PASSED")
            else:
                logger.warning("✗ TEST PARTIAL - Some components may not be running")
            
            return success
            
        except Exception as e:
            logger.error(f"Test failed with exception: {e}", exc_info=True)
            return False


if __name__ == "__main__":
    logger.info("Starting integration test...")
    logger.info("NOTE: C++ backend should be running at /tmp/sc2_can_bridge.sock")
    logger.info("      (some tests will pass even if C++ backend is not running)\n")
    
    success = test_can_pipeline()
    
    if success:
        logger.info("\n✓ Integration test completed successfully")
        exit(0)
    else:
        logger.warning("\n⚠ Integration test completed with warnings")
        exit(1)
