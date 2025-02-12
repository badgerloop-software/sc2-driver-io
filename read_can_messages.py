import can

## link to docs https://www.waveshare.com/wiki/RS485_CAN_HAT#Install_Library

# Create a CAN bus connection
bus = can.interface.Bus(channel="can0", bustype="socketcan")

"""
Message structure: 
.arbitration_id: id of the CAN message
.data: the body content of the CAN message
.timestamp: the timestamp of the CAN message
"""
can_messages = []
class MyListener(can.Listener):
    def on_message(self, message):
      message = {
            "id": hex(message.arbitration_id),
            "data": list(message.data),
            "timestamp": message.timestamp
      }
      print(f"New Message: ID={message_data['id']}, Data={message_data['data']}")

#set up listener
listener = MyListener()

#A Notifier runs in the background and listens for messages. When a new message arrives, it calls on_message in MyListener.
notifier = can.Notifier(bus, [listener])

#create an infinite loop to keep listening to messages.
try:
    print("Listening for CAN messages... Press Ctrl+C to stop.")
    while True:
        pass  # Infinite loop to keep listening
except KeyboardInterrupt:
    print("Stopping CAN receiver.")
    notifier.stop()
    bus.shutdown()

"""
CAN Messages
MCU_ACC	      0x200
MCU_RGN_BRK	      0x201	
MCU_DIR	      0x207	
LV_12V_TELEM      0x202
LV_5V_TELEM	      0x203
I_OUT_5V_TELEM	0x204
I_IN_TELEM	      0x205
MC_SPEED_SIG	0x207
MCU_ECO	      0x207
MCU_MC_ON	      0x209
PRK_BRK_TELEM	0x207
BRK_PRES_TELEM	0x206
"""