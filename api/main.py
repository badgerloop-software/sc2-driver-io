import asyncio
import websockets
import can
import json
from read_can_messages import MyListener
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# why websockets? websockets allow the server to push updates to client in real
# time as supposed to HTTP requests, which require a client to repeatedly poll
# the server for new data

# Store active WebSocket connections (driver dashboard is a client )
clients = set()

# Setup CAN Bus Interface
bus = can.interface.Bus(channel="can0", bustype="socketcan")


class WebSocketsListener(MyListener):
    def __init__(self, loop, send_callback):
        """
        param loop: Reference to the asyncio event loop.
        param send_callback: function that broadcasts messages to connected WebSocket clients.
        """
        self.loop = loop
        self.send_callback = send_callback

    def on_message_received(self, message):
        message_data = {
            "id": message.arbitration_id,
            "data": message.data,  # bytes object
            "timestamp": message.timestamp,
        }
        # Parse the message using parse_data, if cannot parse (data/canID is invalid), parsed is None
        parsed = self.parse_data(message_data)
        if parsed:
            # Convert the parsed data into JSON.
            json_data = json.dumps(parsed.__dict__)
            # Schedule the send_callback coroutine on the event loop.
            asyncio.run_coroutine_threadsafe(self.send_callback(json_data), self.loop)


async def handle_connection(websocket, path):
    clients.add(websocket)  # Add client to the set of active connections

    try:
        async for message in websocket:
            print(f"Received from client: {message}")  # Log incoming messages
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")
    finally:
        clients.remove(websocket)  # Remove client when disconnected


async def send_to_clients(message: str):

    # broad cast message to engineering dashboard
    if clients:
        # Use asyncio.wait to ensure all clients receive the message concurrently
        await asyncio.wait([client.send(message) for client in clients])


async def start_server():
    server = await websockets.serve(handle_connection, "0.0.0.0", 8765)
    loop = asyncio.get_running_loop()
    # Create the WebsocketsListener, passing the loop and send_to_clients callback.
    ws_listener = WebSocketsListener(loop, send_to_clients)
    notifier = can.Notifier(bus, [ws_listener])
    await asyncio.Future()  # Run indefinitely.


if __name__ == "__main__":
    asyncio.run(start_server())
