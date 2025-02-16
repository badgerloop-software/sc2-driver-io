import can
import struct
import time

# Create a CAN bus connection
bus = can.interface.Bus(channel="can0", bustype="socketcan")

"""
Message structure: 
.arbitration_id: id of the CAN message
.data: the body content of the CAN message
.timestamp: the timestamp of the CAN message
"""

output_can_messages_types = [
    {"schematic_name": "ACC_IN", "data_type": "float", "id": "0x20A"},
    {"schematic_name": "MCU_ACC", "data_type": "float", "id": "0x200"},
    {"schematic_name": "MCU_RGN_BRK", "data_type": "float", "id": "0x201"},
    {"schematic_name": "MCU_DIR", "data_type": "boolean", "id": "0x207", "bit_offset": 0},
    {"schematic_name": "LV_12V_TELEM", "data_type": "float", "id": "0x202"},
    {"schematic_name": "LV_5V_TELEM", "data_type": "float", "id": "0x203"},
    {"schematic_name": "I_OUT_5V_TELEM", "data_type": "float", "id": "0x204"},
    {"schematic_name": "I_IN_TELEM", "data_type": "float", "id": "0x205"},
    {"schematic_name": "MC_SPEED_SIG", "data_type": "boolean", "id": "0x207", "bit_offset": 0}
    {"schematic_name": "MCU_ECO", "data_type": "boolean", "id": "0x207", "bit_offset": 1},
    {"schematic_name": "MCU_MC_ON", "data_type": "boolean", "id": "0x209", "bit_offset": 2},
    {"schematic_name": "PRK_BRK_TELEM", "data_type": "boolean", "id": "0x207","bit_offset": 3},
    {"schematic_name": "BRK_PRES_TELEM", "data_type": "float", "id": "0x206"}
]

def extract_bit(byte_value, bit_position):
    """Extracts a boolean value from a specific bit position in a byte."""
    return bool((byte_value >> bit_position) & 1)

class MyListener(can.Listener):
    def on_message_receieved(self, message):
        message_data = {
            "id": hex(message.arbitration_id),
            "data": list(message.data),
            "timestamp": message.timestamp
        }
        #loop through output_can_messages_types dictionary and add data types + schematic name to the message_data
        for can_messages_type in output_can_messages_types:
          if message_data["id"] == can_messages_type["id"]:
            message_data["data_type"] = can_messages_type["data_type"]
            message_data["schematic_name"] = can_messages_type["schematic_name"]
            if can_messages_type["bit_offset"] != None:
                message_data["bit_offset"] = can_messages_type['bit_offset']
        assert message_data["data_type"] != None #assert error if id not found.
        #handle different data types
        if message_data["data_type"] == "float":
            byte_array = bytes(message_data["data"]) 
            float_value = struct.unpack("<f", byte_array)[0]
            print(f"New Message: ID={message_data['id']},Name={message_data['schematic_name']} Value={float_value}, Time Stamp={message_data['timestamp']}")
        elif message_data["data_type"] == "boolean":
            messages_list = []
            if len(message_data["data"]) > 0:
                #get first byte
                byte = message_data["data"][0]
            #not done yet use extract bit data

#set up listener
listener = MyListener()

#A Notifier runs in the background and listens for messages. When a new message arrives, it calls on_message in MyListener.
notifier = can.Notifier(bus, [listener])

#create an infinite loop to keep listening to messages.
try:
    print("Listening for CAN messages... Press Ctrl+C to stop.")
    while True:
        time.sleep(1)
        # Infinite loop to keep listening
except KeyboardInterrupt:
    print("Stopping CAN receiver.")
    notifier.stop()
    bus.shutdown()
except AssertionError:
    print('CAN ID not found')
