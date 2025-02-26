#!/usr/bin/env python3
import can
import argparse
import logging

# Allow user to input CAN channel
parser = argparse.ArgumentParser(description="Specify the CAN channel.")
# Define a positional argument for channel
parser.add_argument("channel", type=str, help="CAN channel (e.g., can0, vcan0)")
args = parser.parse_args()
# add logging
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def transmit_can_message(channel, bustype="socketcan"):
    """
    Initializes the CAN bus, prompts the user for message parameters,
    and transmits the CAN message.
    """
    # Initialize the CAN bus interface
    bus = can.interface.Bus(channel=channel, bustype=bustype)

    # Prompt for the arbitration ID (CAN ID), this gets the arbitration id from the user and validates it
    arb_id_input = input("Enter 3-digit hex message ID (e.g. 0x123): ").strip()
    try:
        # Accept input as hex if it starts with 0x, otherwise assume hex too
        arbitration_id = int(arb_id_input, 16)
    except ValueError:
        logging.error("Invalid message ID input.")
        bus.shutdown()
        return

    # Prompt for data bytes input (as hex values) accepts users inputs as data.
    data_input = input(
        "Enter data bytes as hex values separated by spaces (e.g. '11 22 33 44'): "
    ).strip()
    try:
        data_bytes = []
        for byte_str in data_input.split():
            # Convert each input to an integer (assumed hex)
            data_byte = int(byte_str, 16)
            if not (0 <= data_byte <= 255):
                print(f"Byte out of range (0-255): {data_byte}")
                bus.shutdown()
                return
            data_bytes.append(data_byte)
    except ValueError:
        logging.error("Invalid data byte input.")
        bus.shutdown()
        return

    # Create the CAN message
    msg = can.Message(
        arbitration_id=arbitration_id, data=data_bytes, is_extended_id=False
    )

    # Send message using bus.send()
    try:
        bus.send(msg)
        print(
            f"Message sent successfully!\n Message Details: ID={msg.arbitration_id}, Data={msg.data}"
        )
    except can.CanError as e:
        print(f"Message failed to send: {e}")

    # Cleanly shutdown the bus connection
    bus.shutdown()


if __name__ == "__main__":
    transmit_can_message(args.channel)
