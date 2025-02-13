#!/usr/bin/env python3
import can

def transmit_can_message(channel="can0", bustype="socketcan"):
    """
    Initializes the CAN bus, prompts the user for message parameters,
    and transmits the CAN message.
    """
    # Initialize the CAN bus interface
    bus = can.interface.Bus(channel=channel, bustype=bustype)

    # Prompt for the arbitration ID (CAN ID)
    arb_id_input = input("Enter arbitration id (e.g. 0x123): ").strip()
    try:
        # Accept input as hex if it starts with 0x, otherwise assume hex too
        if arb_id_input.lower().startswith("0x"):
            arbitration_id = int(arb_id_input, 16)
        else:
            arbitration_id = int(arb_id_input, 16)
    except ValueError:
        print("Invalid arbitration id input.")
        bus.shutdown()
        return

    # Prompt for data bytes input (as hex values)
    data_input = input("Enter data bytes as hex values separated by spaces (e.g. '11 22 33 44'): ").strip()
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
        print("Invalid data byte input.")
        bus.shutdown()
        return

    # Prompt for whether the CAN ID is extended or standard
    extended_input = input("Is this an extended CAN ID? (y/n): ").strip().lower()
    is_extended_id = extended_input.startswith("y")

    # Create the CAN message
    msg = can.Message(
        arbitration_id=arbitration_id,
        data=data_bytes,
        is_extended_id=is_extended_id
    )

    # Attempt to send the message
    try:
        bus.send(msg)
        print("Message sent successfully!")
    except can.CanError as e:
        print(f"Message failed to send: {e}")

    # Cleanly shutdown the bus connection
    bus.shutdown()

if __name__ == "__main__":
    transmit_can_message()
