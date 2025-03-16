import can
import struct
import time
import logging
from send_messages import transmit_can_message
import argparse
from typing import List, Dict, Any
import json
from dataclasses import SignalInfo, ParsedData

"""
Message structure: 
.arbitration_id: id of the CAN message
.data: the body content of the CAN message
.timestamp: the timestamp of the CAN message
"""


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def preprocess_data_format(format: Dict[str, List[Any]]) -> Dict[str, Dict[int, Any]]:
    """
    Parse data format and return in a more friendly format for  CAN consumption:
    <CAN ID>: {
        <offset>: {
            <category 1>: ...
            ...
        }
        ...
    },
    ...
    """
    processed = {}
    for key, s in format.items():
        # Get the arbitration ID and offset
        can_id = int(s[-2], base=16)
        offset = s[-1]
        # Drop the ID and offset
        s = s[:-2]
        # Add/Update the message data in the processed data format
        p = processed.setdefault(can_id, {})
        num_bytes = s[0]
        data_type = s[1]
        units = s[2]
        nominal_min = s[3]
        nominal_max = s[4]
        subsystem = s[5]
        signal_info = SignalInfo(
            key, num_bytes, data_type, units, nominal_min, nominal_max, subsystem
        )
        p[offset] = signal_info

    return processed


with open("sc1-data-format/format.json", "r") as file:
    data = json.load(file)

signal_definitions = preprocess_data_format(data)


class MyListener(can.Listener):
    def on_message_received(self, message):
        message_data = {
            "id": message.arbitration_id,
            "data": list(message.data),
            "timestamp": message.timestamp,
        }
        self.parse_data(message_data)

    def parse_data(self, message_data):
        # loop through signal definitions to find can_id
        can_id = message_data["id"]
        if can_id not in signal_definitions:
            logging.error(f"CAN ID {can_id:0x} not found in signal definitions.")
            return None
        signals = signal_definitions[can_id]
        byte_array = bytes(message_data["data"])

        for offset, signals_info in signals.items():
            logging.debug(
                f"Processing signal at offset {offset} for CAN ID {can_id:0x}"
            )
            data_type = signals_info.type
            signal_name = signals_info.name
            if data_type == "float":
                if len(byte_array) < 4:
                    logging.error(
                        f"Insufficient data for float signal in CAN ID {can_id:0x}."
                    )
                    return
                else:
                    # Unpack the first 4 bytes as a little-endian float.
                    float_value = struct.unpack("<f", byte_array[:4])[0]
                    logging.debug(
                        f"New Message: ID={can_id:0x},Name={signal_name} Value={float_value}, Time Stamp={message_data['timestamp']}"
                    )
                    return ParsedData(
                        can_id, signal_name, float_value, message_data["timestamp"]
                    )

            elif data_type == "boolean":
                bool_value = bool((byte_array[0] >> offset) & 1)
                logging.debug(
                    f"New Message: ID={can_id:0x},Name={signal_name} Value={bool_value}, Time Stamp={message_data['timestamp']}"
                )
                return ParsedData(
                    can_id, signal_name, bool_value, message_data["timestamp"]
                )


if __name__ == "__main__":
    # Create a CAN bus connection
    bus = can.interface.Bus(channel="can0", bustype="socketcan")

    # set up listener
    listener = MyListener()

    # A Notifier runs in the background and listens for messages. When a new message arrives, it calls on_message in MyListener.
    notifier = can.Notifier(bus, [listener])

    try:
        # create an infinite loop to keep listening to messages.
        print("Listening for CAN messages... Press Ctrl+C to stop.")
        parser = argparse.ArgumentParser(description="Specify the CAN channel.")
        # Define a positional argument for channel
        parser.add_argument("channel", type=str, help="CAN channel (e.g., can0, vcan0)")
        args = parser.parse_args()
        transmit_can_message()
        while True:
            time.sleep(1)
            # Infinite loop to keep listening
    except KeyboardInterrupt:
        print("Stopping CAN receiver.")
        notifier.stop()
        bus.shutdown()
