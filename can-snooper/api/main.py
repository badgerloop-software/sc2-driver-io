import asyncio
import websockets
import can
import json
from can_utils.read_can_messages import MyListener
from can_utils.csv_writer import CSVWriter
import logging
import os

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
    def __init__(self, loop, send_to_clients, csv_writer: CSVWriter = None):
        """
        param loop: Reference to the asyncio event loop.
        param send_to_clients: function that broadcasts messages to connected WebSocket clients.
        param csv_writer: Optional CSV writer for logging data to file.
        """
        self.loop = loop
        self.send_to_clients = send_to_clients
        self.csv_writer = csv_writer

    def on_message_received(self, message):
        message_data = {
            "id": message.arbitration_id,
            "data": message.data,  # bytes object
            "timestamp": message.timestamp,
        }
        # Parse the message using parse_data, if cannot parse (data/canID is invalid), parsed is None
        parsed = self.parse_data(message_data)
        if parsed:
            # Write to CSV if csv_writer is available
            if self.csv_writer:
                self.csv_writer.write_parsed_data(
                    can_id=parsed.can_id,
                    signal_name=parsed.signal_name,
                    value=parsed.value,
                    timestamp=parsed.timestamp
                )

            # Convert the parsed data into JSON.
            json_data = json.dumps(parsed.__dict__)
            # Send callback
            self.loop.create_task(self.send_to_clients(json_data))


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


async def start_server():
    server = await websockets.serve(handle_connection, "0.0.0.0", 8765)
    loop = asyncio.get_running_loop()

    # Initialize CSV writer
    csv_file_path = os.path.join(os.path.dirname(__file__), "..", "can_data.csv")
    csv_writer = CSVWriter(csv_file_path)
    logging.info(f"CSV logging enabled: {csv_file_path}")

    # Create the WebsocketsListener, passing the loop, send_to_clients callback, and CSV writer.
    ws_listener = WebSocketsListener(loop, send_to_clients, csv_writer)
    notifier = can.Notifier(bus, [ws_listener])

    try:
        await asyncio.Future()  # Run indefinitely.
    except asyncio.CancelledError:
        logging.info("Server shutting down...")
        csv_writer.close()
        notifier.stop()
        bus.shutdown()
        raise


if __name__ == "__main__":
    asyncio.run(start_server())
