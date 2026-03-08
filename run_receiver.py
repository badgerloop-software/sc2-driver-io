#!/usr/bin/env python3
import time
import logging
import sys
import os
from can_bus.can_reader import CANReader
from can_bus.csv_consumer import CSVConsumer

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Receiver")

def main():
    logger.info("Starting Receiver Application")
    
    try:
        reader = CANReader(channel='can0')
        # Explicitly set output dir
        out_dir = '/mnt/usb/can_logs'
        if not os.path.exists(out_dir):
            logger.error(f"Output directory {out_dir} does not exist!")
            
        consumer = CSVConsumer(output_dir=out_dir, buffer_size=1)
        reader.register_consumer("csv_logger", consumer.consume)
        
        reader.start()
        logger.info(f"Receiver is running. Logging to {out_dir}")
        
        # Monitor for a bit
        for _ in range(30):
            time.sleep(1)
            stats = reader.get_stats()
            if stats.get('csv_logger', {}).get('queue', 0) > 0:
                logger.debug(f"Stats: {stats}")
            
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
    finally:
        if 'reader' in locals():
            reader.stop()
        if 'consumer' in locals():
            consumer.close()
        logger.info("Shutdown complete")

if __name__ == "__main__":
    main()
