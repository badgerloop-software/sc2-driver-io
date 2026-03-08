import os
import csv
from pathlib import Path
from datetime import datetime
from can_bus.can_reader import CANMessage

class CSVConsumer:
    def __init__(self, output_dir='/mnt/usb/can_logs', buffer_size=1):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.messages_written = 0
        # Format: Day-Month-Year_Hour-Min-Sec-AM/PM (e.g., 07-03-2026_11-30-05-PM)
        timestamp = datetime.now().strftime("%d-%m-%Y_%I-%M-%S-%p")
        self.current_path = self.output_dir / f'can_log_{timestamp}.csv'
        self.file = open(self.current_path, 'w', newline='')
        self.writer = csv.writer(self.file)
        self.writer.writerow(['timestamp', 'can_id', 'signal_name', 'value', 'raw_data_hex'])
        self.file.flush()
        os.fsync(self.file.fileno())
        print(f"INIT: Started log at {self.current_path}")
    
    def consume(self, msg: CANMessage):
        try:
            self.writer.writerow([msg.timestamp, f'0x{msg.can_id:03X}', msg.signal_name, msg.value, msg.raw_data.hex()])
            self.file.flush()
            os.fsync(self.file.fileno())
            self.messages_written += 1
            if self.messages_written % 100 == 0:
                print(f"LOGGED: {self.messages_written} messages")
        except Exception as e:
            print(f'CSV Error: {e}')

    def close(self):
        if hasattr(self, 'file'):
            self.file.close()
