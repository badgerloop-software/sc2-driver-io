import can
import struct
import json
from typing import List
from can_bus.data_classes import SignalInfo, ParsedData

def preprocess_data_format(format_data):
    processed = {}
    for key, s in format_data.items():
        try:
            can_id = int(s[-2], base=16)
            offset = s[-1]
            signal_info = SignalInfo(
                name=key,
                bytes=s[0],
                type=s[1],
                units=s[2],
                nominal_min=s[3],
                nominal_max=s[4],
                subsystem=s[5]
            )
            processed.setdefault(can_id, {})[offset] = signal_info
        except: continue
    return processed

json_path = "/home/sunpi/sc2-driver-io/sc-data-format/format.json"
with open(json_path, "r") as f:
    signal_definitions = preprocess_data_format(json.load(f))

class MyListener(can.Listener):
    def on_message_received(self, msg):
        return self.parse_data({'id': msg.arbitration_id, 'data': msg.data, 'timestamp': msg.timestamp})

    def parse_data(self, message_data) -> List[ParsedData]:
        can_id = message_data["id"]
        if can_id not in signal_definitions: return []
        signals = signal_definitions[can_id]
        byte_array = bytes(message_data["data"])
        parsed_results = []
        for offset, info in signals.items():
            try:
                byte_idx = offset // 8
                bit_idx = offset % 8
                val = None
                
                if info.type == "float":
                    if info.bytes == 2:
                        fmt, size = '<e', 2
                    elif info.bytes == 8:
                        fmt, size = '<d', 8
                    else:
                        fmt, size = '<f', 4
                    if byte_idx + size <= len(byte_array):
                        val = struct.unpack(fmt, byte_array[byte_idx:byte_idx+size])[0]
                elif info.type in ["bool", "boolean"]:
                    if byte_idx < len(byte_array):
                        val = bool((byte_array[byte_idx] >> bit_idx) & 1)
                elif info.type.startswith("int") or info.type.startswith("uint"):
                    if info.bytes == 1:
                        val = byte_array[byte_idx]
                    elif info.bytes == 2:
                        val = struct.unpack('<h' if info.type.startswith("int") else '<H', byte_array[byte_idx:byte_idx+2])[0]
                    elif info.bytes == 4:
                        val = struct.unpack('<i' if info.type.startswith("int") else '<I', byte_array[byte_idx:byte_idx+4])[0]
                    elif info.bytes == 8:
                        val = struct.unpack('<q' if info.type.startswith("int") else '<Q', byte_array[byte_idx:byte_idx+8])[0]
                
                if val is not None:
                    parsed_results.append(ParsedData(can_id, info.name, float(val), message_data["timestamp"]))
            except: continue
        return parsed_results
