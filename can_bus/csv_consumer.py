#!/usr/bin/env python3
"""
CSV Consumer - Logs CAN data to CSV files
Buffered writing for performance, rotates files by size or time
"""

import csv
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, TextIO
from can_bus.can_reader import CANMessage

logger = logging.getLogger(__name__)


class CSVConsumer:
    """
    Consumer that logs CAN messages to CSV files.
    Features:
    - Buffered writes for performance
    - Automatic file rotation by size or time
    - Configurable output directory
    """
    
    def __init__(
        self,
        output_dir: str = "/media/usb/can_logs",
        max_file_size_mb: int = 100,
        buffer_size: int = 1000,
        flush_interval_s: float = 5.0
    ):
        """
        Initialize CSV logger
        
        Args:
            output_dir: Directory for CSV files
            max_file_size_mb: Max file size before rotation
            buffer_size: Number of messages to buffer before flush
            flush_interval_s: Max time between flushes
        """
        self.output_dir = Path(output_dir)
        self.max_file_size = max_file_size_mb * 1024 * 1024
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval_s
        
        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Current file state
        self.current_file: Optional[TextIO] = None
        self.current_writer: Optional[csv.writer] = None
        self.current_path: Optional[Path] = None
        self.messages_buffered = 0
        self.messages_written = 0
        self.last_flush_time = datetime.now()
        
        # Open initial file
        self._rotate_file()
        
        logger.info(f"CSV consumer initialized - Output: {self.output_dir}")
    
    def consume(self, msg: CANMessage) -> None:
        """
        Callback for CAN reader - writes message to CSV.
        
        Args:
            msg: Parsed CAN message from CANReader
        """
        try:
            # Check if rotation needed
            if self._should_rotate():
                self._rotate_file()
            
            # Write row
            self.current_writer.writerow([
                msg.timestamp,
                f"0x{msg.can_id:03X}",
                msg.signal_name,
                msg.value,
                msg.raw_data.hex()
            ])
            
            self.messages_buffered += 1
            self.messages_written += 1
            
            # Flush if buffer full or interval elapsed
            if (self.messages_buffered >= self.buffer_size or
                (datetime.now() - self.last_flush_time).total_seconds() >= self.flush_interval):
                self._flush()
                
        except Exception as e:
            logger.error(f"Error writing to CSV: {e}")
    
    def _should_rotate(self) -> bool:
        """Check if file should be rotated"""
        if self.current_path is None:
            return True
            
        try:
            file_size = self.current_path.stat().st_size
            return file_size >= self.max_file_size
        except FileNotFoundError:
            return True
    
    def _rotate_file(self) -> None:
        """Close current file and open new one"""
        # Close existing file
        if self.current_file:
            self._flush()
            self.current_file.close()
            logger.info(f"Rotated CSV file - {self.messages_written} total messages")
        
        # Create new filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_path = self.output_dir / f"can_log_{timestamp}.csv"
        
        # Open new file and create writer
        self.current_file = open(self.current_path, 'w', newline='')
        self.current_writer = csv.writer(self.current_file)
        
        # Write header
        self.current_writer.writerow([
            'timestamp',
            'can_id',
            'signal_name',
            'value',
            'raw_data_hex'
        ])
        
        self.messages_buffered = 0
        logger.info(f"Created new CSV file: {self.current_path}")
    
    def _flush(self) -> None:
        """Flush buffered data to disk"""
        if self.current_file:
            self.current_file.flush()
            self.messages_buffered = 0
            self.last_flush_time = datetime.now()
    
    def get_stats(self) -> dict:
        """Get consumer statistics"""
        return {
            'messages_written': self.messages_written,
            'current_file': str(self.current_path) if self.current_path else None,
            'messages_buffered': self.messages_buffered,
            'file_size_mb': (
                self.current_path.stat().st_size / (1024 * 1024)
                if self.current_path and self.current_path.exists()
                else 0.0
            )
        }
    
    def close(self):
        """Clean shutdown"""
        if self.current_file:
            self._flush()
            self.current_file.close()
            logger.info(f"CSV consumer closed - Stats: {self.get_stats()}")


if __name__ == "__main__":
    # Test consumer
    logging.basicConfig(level=logging.INFO)
    
    import time
    import tempfile
    
    # Use temp directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        consumer = CSVConsumer(output_dir=tmpdir, buffer_size=10)
        
        # Write test messages
        for i in range(25):
            test_msg = CANMessage(
                can_id=0x100 + i,
                signal_name=f"test_signal_{i}",
                value=float(i),
                timestamp=time.time(),
                raw_data=bytes([i, i+1, i+2, i+3])
            )
            consumer.consume(test_msg)
        
        print(f"Stats: {consumer.get_stats()}")
        consumer.close()
