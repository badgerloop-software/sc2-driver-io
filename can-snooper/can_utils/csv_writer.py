import csv
import logging
import os
from datetime import datetime
from typing import Optional
from dataclasses import dataclass


@dataclass
class CSVWriter:
    """Handles writing CAN data to CSV files."""

    file_path: str
    fieldnames: list = None

    def __post_init__(self):
        """Initialize CSV file with headers if it doesn't exist or is empty."""
        if self.fieldnames is None:
            self.fieldnames = ["timestamp", "can_id", "signal_name", "value"]

        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)

        # Check if file exists and has content to determine if we need to write headers
        file_exists = os.path.exists(self.file_path)
        file_is_empty = not file_exists or os.path.getsize(self.file_path) == 0

        try:
            # Open file in append mode
            self.file = open(self.file_path, "a", newline="", encoding="utf-8")
            self.writer = csv.DictWriter(self.file, fieldnames=self.fieldnames)

            # Write headers if file is new or empty
            if file_is_empty:
                self.writer.writeheader()
                self.file.flush()  # Ensure headers are written immediately
                logging.info(f"Created new CSV file with headers: {self.file_path}")
            else:
                logging.info(f"Appending to existing CSV file: {self.file_path}")

        except Exception as e:
            logging.error(f"Failed to open CSV file {self.file_path}: {e}")
            raise

    def write_row(self, data: dict) -> bool:
        """Write a single row of data to the CSV file.

        Args:
            data: Dictionary containing the data to write

        Returns:
            bool: True if write was successful, False otherwise
        """
        try:
            self.writer.writerow(data)
            self.file.flush()  # Ensure data is written immediately
            return True
        except Exception as e:
            logging.error(f"Failed to write to CSV: {e}")
            return False

    def write_parsed_data(
        self, can_id: int, signal_name: str, value: float, timestamp: float
    ) -> bool:
        """Write parsed CAN data to CSV.

        Args:
            can_id: CAN message ID
            signal_name: Name of the parsed signal
            value: Parsed value (float or bool)
            timestamp: Message timestamp

        Returns:
            bool: True if write was successful, False otherwise
        """
        row_data = {
            "timestamp": timestamp,
            "can_id": can_id,
            "signal_name": signal_name,
            "value": value,
        }
        return self.write_row(row_data)

    def close(self):
        """Close the CSV file."""
        try:
            if hasattr(self, "file") and not self.file.closed:
                self.file.close()
                logging.info(f"Closed CSV file: {self.file_path}")
        except Exception as e:
            logging.error(f"Error closing CSV file: {e}")

    def __del__(self):
        """Ensure file is closed when object is destroyed."""
        self.close()
