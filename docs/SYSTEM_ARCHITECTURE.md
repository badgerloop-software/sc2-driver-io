# SC2 Driver IO - Architecture Documentation

## System Overview

The SC2 Driver IO system follows a **single-reader, fan-out** architecture:

```
CAN Bus → CANReader → ┬→ TelemetryConsumer → Unix Socket → C++ Backend
                       ├→ CSVConsumer → USB Drive
                       └→ LapCounter (future)
```

### Components

#### 1. CAN Reader (`can_bus/can_reader.py`)
- Single thread reads from CAN bus interface
- Distributes messages to registered consumers
- Prevents data races and missed messages
- Each consumer runs in dedicated thread with its own queue

#### 2. Telemetry Consumer (`can_bus/telemetry_consumer.py`)
- Forwards CAN data to C++ telemetry system
- Uses Unix domain socket (`/tmp/sc2_can_bridge.sock`)
- High priority, 2000 message queue

#### 3. CSV Consumer (`can_bus/csv_consumer.py`)
- Logs CAN data to CSV files
- Buffered writes for performance
- Automatic file rotation
- Lower priority, 5000 message queue

#### 4. C++ Telemetry Backend
- Receives CAN data via Unix socket
- Distributes to: UDP (chase car), TCP (dashboard), Serial (RFD900)
- Real-time performance for telemetry transmission

#### 5. Coordinator (`services/coordinator.py`)
- System orchestration
- Starts/stops all components
- Status monitoring
- Graceful shutdown handling

## Data Flow

1. CAN messages arrive at hardware interface (can0)
2. CANReader receives and parses messages
3. Messages distributed to all registered consumers via queues
4. TelemetryConsumer sends to C++ via Unix socket
5. CSVConsumer writes to disk
6. C++ telemetry system broadcasts to radio/TCP/UDP

## Benefits of This Architecture

- **No data races**: Single reader eliminates concurrent access issues
- **Performance**: Consumer queues prevent blocking
- **Reliability**: Buffer overflow only affects slow consumers
- **Maintainability**: Clear separation of concerns
- **Testability**: Components can be tested independently

## Requirements

### Python Dependencies
```bash
pip install -r requirements.txt
```

### C++ Backend
The C++ backend must be compiled and running:
```bash
cd build
cmake ..
make
./sc2-driver-io &
```

### CAN Interface
Requires SocketCAN interface (Linux):
```bash
sudo ip link set can0 up type can bitrate 500000
```

## Testing

### Test Consumers (No Hardware)
```bash
python3 test_consumers.py
```

### Test CAN Bridge (C++ Backend Required)
```bash
./build/sc2-driver-io &
python3 test_can_bridge.py
```

### Full System Test (CAN Hardware Required)
```bash
python3 services/coordinator.py
```

## Configuration

CAN channel and CSV output directory can be configured in coordinator:
```python
system = DriverIOSystem(
    can_channel="can0",           # CAN interface
    csv_output_dir="/media/usb/can_logs"  # USB drive mount
)
```

## Qt Removal Status

✓ All Qt dependencies removed from C++ codebase
✓ Replaced with standard C++20 and POSIX APIs  
✓ Unix domain sockets for IPC (replaces Qt signals/slots)
✓ Project compiles and runs without Qt framework

## Next Steps

1. Integrate lap counter as CAN reader consumer
2. Add signal parsing for structured CAN data
3. Implement dashboard integration
4. Add real-time priority scheduling
5. Performance tuning and optimization
