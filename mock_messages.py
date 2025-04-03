import asyncio
import websockets
import json
import random
import time
import logging
import can
from can_utils.read_can_messages import MyListener

# --- Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# --- Connected Clients Set ---
clients = set()

# --- WebSocket Handler ---


async def handle_connection(websocket):
    clients.add(websocket)
    logging.info("Client connected")

    try:
        async for message in websocket:
            logging.info(f"Received from client: {message}")
    except websockets.exceptions.ConnectionClosed:
        logging.info("Client disconnected")
    finally:
        clients.remove(websocket)


# --- Broadcast Helper ---
async def send_to_clients(message: str):
    if clients:
        await asyncio.wait(
            [asyncio.create_task(client.send(message)) for client in clients]
        )


class MockListener:
    def __init__(self, loop, send_callback):
        self.loop = loop
        self.send_callback = send_callback
        self.parser = MyListener()

    def start_sending(self):
        async def fake_loop():
            while True:
                # Create a fake can.Message
                msg = can.Message(
                    arbitration_id=random.choice([0x200, 0x208]),
                    data=[random.randint(0, 255) for _ in range(8)],
                    is_extended_id=False,
                )
                msg.timestamp = time.time()  # add fake timestamp manually

                # Simulate message_data format like real listener expects
                message_data = {
                    "id": msg.arbitration_id,
                    "data": list(msg.data),
                    "timestamp": msg.timestamp,
                }
                parsed_data = self.parser.parse_data(message_data)
                if parsed_data:
                    json_data = json.dumps(parsed_data.__dict__)
                    logging.info(f"Broadcasting from CAN message: {json_data}")
                    await self.send_callback(json_data)
                await asyncio.sleep(2)

        asyncio.create_task(fake_loop())


# --- Start Server ---


async def start_server():
    await websockets.serve(handle_connection, "0.0.0.0", 8765)
    loop = asyncio.get_running_loop()
    mock_listener = MockListener(loop, send_to_clients)
    mock_listener.start_sending()
    logging.info("WebSocket server running on ws://localhost:8765")
    await asyncio.Future()  # run forever


# --- Main Entry Point ---

if __name__ == "__main__":
    try:
        asyncio.run(start_server())
    except KeyboardInterrupt:
        print("Server stopped by user.")
