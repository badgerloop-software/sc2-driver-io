import asyncio
import websockets
import can
import json

# why websockets? websockets allow the server to push updates to client in real
# time as supposed to HTTP requests, which require a client to repeatedly poll
# the server for new data

# Store active WebSocket connections (driver dashboard is a client )
clients = set()

# Setup CAN Bus Interface
bus = can.interface.Bus(channel="can0", bustype="socketcan")

# Load CAN data format from a JSON file
with open("sc1-data-format/format.json", "r") as file:
    data_format = json.load(file)


def preprocess_data_format(data):
    """
    preprocess data here
    """
    return data  # Just return the loaded JSON for now


async def handle_connection(websocket, path):

    print("Client connected")
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


async def read_can_messages():

    # reads CAN Hat messages and sends them to driver dashboard
    while True:
        message = bus.recv(timeout=0.1)  # Use timeout to prevent blocking execution
        if message:
            # Convert CAN message into a dictionary format
            data = {
                "id": message.arbitration_id,
                "data": message.data.hex(),  # Convert binary data to hexadecimal string
                "timestamp": message.timestamp,
            }
            print(f"Received CAN message: {data}")
            await send_to_clients(json.dumps(data))  # Broadcast message in JSON format
        await asyncio.sleep(0.01)  # Small delay to avoid excessive CPU usage


async def start_server():

    # start websocket server and CAN HAT Listener

    server = await websockets.serve(handle_connection, "0.0.0.0", 8765)
    print("WebSocket server started on ws://0.0.0.0:8765")  # change this

    # Run both the WebSocket server and CAN message reader concurrently
    await asyncio.gather(read_can_messages())


# Run the WebSocket server and CAN listener
asyncio.run(start_server())
