import can
import struct
import time
import logging
from send_messages import transmit_can_message
import argparse

"""
Message structure: 
.arbitration_id: id of the CAN message
.data: the body content of the CAN message
.timestamp: the timestamp of the CAN message
"""

logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

signal_definitions = {
    "0x20A": {"default": {"name": "ACC_IN", "data_type": "float"}},
    "0x200": {"default": {"name": "MCU_ACC", "data_type": "float"}},
    "0x201": {"default": {"name": "MCU_RGN_BRK", "data_type": "float"}},
    "0x207": {
        0: {"name": "MCU_DIR", "data_type": "boolean"},
        1: {"name": "MCU_ECO", "data_type": "boolean"},
        3: {"name": "PRK_BRK_TELEM", "data_type": "boolean"},
    },
    "0x202": {"default": {"name": "LV_12V_TELEM", "data_type": "float"}},
    "0x203": {"default": {"name": "LV_5V_TELEM", "data_type": "float"}},
    "0x204": {"default": {"name": "I_OUT_5V_TELEM", "data_type": "float"}},
    "0x205": {"default": {"name": "I_IN_TELEM", "data_type": "float"}},
    "0x209": {2: {"name": "MCU_MC_ON", "data_type": "boolean"}},
    "0x206": {"default": {"name": "BRK_PRES_TELEM", "data_type": "float"}},
}


class MyListener(can.Listener):
    def on_message_received(self, message):
        message_data = {
            "id": hex(message.arbitration_id),
            "data": list(message.data),
            "timestamp": message.timestamp,
        }

        # loop through signal definitions to find can_id
        can_id = hex(message.arbitration_id).lower()
        if can_id not in signal_definitions:
            logging.error(f"CAN ID {can_id} not found in signal definitions.")
            return
        signals = signal_definitions[can_id]

        # handle floats
        if "default" in signals:
            signal = signals["default"]
            if signal["data_type"] == "float":
                # Convert message.data to a bytes object if it's not already one.
                byte_array = bytes(message.data)
                if len(byte_array) < 4:
                    logging.error(
                        f"Insufficient data for float signal in CAN ID {can_id}."
                    )
                    return
                else:
                    # Unpack the first 4 bytes as a little-endian float.
                    float_value = struct.unpack("<f", byte_array[:4])[0]
                    print(
                        f"New Message: ID={message_data['id']},Name={signal['name']} Value={float_value}, Time Stamp={message_data['timestamp']}"
                    )

        # handle booleans
        else:
            for key in signals:
                signal = signals[key]
                if signal["data_type"] == "boolean":
                    byte_array = bytes(message.data)
                    if not byte_array:
                        logging.error(
                            f"No data available for boolean signal in CAN ID {can_id}."
                        )
                        continue
                    bit_offset = key
                    bool_value = bool((byte_array[0] >> bit_offset) & 1)
                    print(
                        f"New Message: ID={message_data['id']},Name={signals[key]['name']} Value={bool_value}, Time Stamp={message_data['timestamp']}"
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
        transmit_can_message(args.channel)
        while True:
            time.sleep(1)
            # Infinite loop to keep listening
    except KeyboardInterrupt:
        print("Stopping CAN receiver.")
        notifier.stop()
        bus.shutdown()
