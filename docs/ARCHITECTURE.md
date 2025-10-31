# SC2 Driver IO Architecture

## Data Flow Pipeline (3 Hz CAN Message Rate)

```
┌─────────────────────────────────────────────────────────────────┐
│                   THREAD 0: CAN RX + PROCESSING                 │
│                         (CRITICAL PATH)                         │
│                                                                 │
│  1. Receive CAN byte array from firmware (SocketCAN)           │
│  2. Get GPS (lat/lon) from EG25-G LTE modem GNSS               │
│  3. Feed GPS to lap_counter.update_position(lat, lon)          │
│  4. Get LapData struct: {lap_count, current_section, duration} │
│  5. Inject lap data into byte array (7 bytes appended)         │
│  6. Queue modified byte array for parallel processing          │
│                                                                 │
│  Target: < 50ms processing time per message                    │
│  Rate: 3 messages/second = 333ms period (plenty of headroom)   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                   [processed_data_queue]
                              ↓
        ┌─────────────────────┼─────────────────────┐
        ↓                     ↓                     ↓
┌───────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  THREAD 1:    │   │   THREAD 2:      │   │   THREAD 3:      │
│  LTE TX       │   │   Radio TX       │   │   CAN TX         │
│               │   │   (RFD900A)      │   │   (Publish back) │
│ Cloud SQL     │   │                  │   │                  │
│ Upload via    │   │ Chase car comm.  │   │ Lap counter data │
│ EG25-G LTE    │   │ UDP telemetry    │   │ + future NN      │
│ (150 Mbps)    │   │ (250 Kbps max)   │   │ outputs to bus   │
└───────────────┘   └──────────────────┘   └──────────────────┘
        ↓                     ↓                     ↓
        └─────────────────────┴─────────────────────┘
                              ↓
        ┌─────────────────────┼─────────────────────┐
        ↓                     ↓                     ↓
┌───────────────┐   ┌──────────────────┐   ┌──────────────────┐
│  THREAD 4:    │   │   THREAD 5:      │   │   THREAD 6:      │
│  CSV Logger   │   │   NN Buffer      │   │   Dashboard      │
│               │   │   (FUTURE)       │   │   Update         │
│ Batch writes  │   │                  │   │                  │
│ every 1 sec   │   │ Accumulate until │   │ Textual GUI      │
│ (30-50 msgs)  │   │ threshold, then  │   │ or JSON file     │
│ to USB drive  │   │ inference        │   │ refresh @ 1Hz    │
└───────────────┘   └──────────────────┘   └──────────────────┘

                ┌──────────────────────────┐
                │   THREAD 7: System Mgmt  │
                │   - Health monitoring    │
                │   - Performance stats    │
                │   - Error recovery       │
                └──────────────────────────┘
```

## Thread Architecture & Priorities

| Thread ID | Name | Priority | Function | Target Latency |
|-----------|------|----------|----------|----------------|
| 0 | CAN-RX-PROC | **HIGH** | CAN RX + GPS + Lap Counter | < 50ms |
| 1 | LTE-TX | Medium | Cloud SQL upload via LTE | Best effort |
| 2 | RADIO-TX | Medium | Chase car telemetry (UDP) | Best effort |
| 3 | CAN-TX | Medium | Publish lap data back to CAN | < 100ms |
| 4 | CSV-LOG | **LOW** | Batch CSV writes to USB | 1 sec batches |
| 5 | NN-BUF | Low | Accumulate data for NN | N/A (future) |
| 6 | DASHBOARD | Low | Update GUI/JSON @ 1Hz | 1 sec |
| 7 | SYS-MGR | Low | Health monitoring | 10 sec |

## Data Structures

### Processed Data Package
```python
processed_data = {
    'byte_array': bytes,           # Modified firmware data with lap counter injected
    'lap_data': {                  # Lap counter output
        'lap_count': uint16,       # [2 bytes] 0-9999
        'current_section': uint8,  # [1 byte] 0-255
        'lap_duration': uint32     # [4 bytes] milliseconds, 0-600000
    },
    'timestamp': float,            # Unix timestamp
    'gps': {
        'lat': float,              # Latitude from EG25-G GNSS
        'lon': float               # Longitude from EG25-G GNSS
    }
}
```

### Lap Counter Byte Array Injection Format
```
Original firmware byte array: [N bytes from CAN message]
+
Lap counter data: [7 bytes]
  - bytes 0-1: lap_count (uint16, little-endian)
  - byte 2: current_section (uint8)
  - bytes 3-6: lap_duration (uint32, little-endian)
=
Modified byte array: [N+7 bytes] → sent to LTE, Radio, CAN TX, CSV
```

### Future: Neural Network Output
```python
nn_output = {
    'optimized_target_power': float  # [4 bytes] kW, 0-10
}
# Will be injected into byte array (4 additional bytes)
# Total modified array: [N + 7 + 4 = N+11 bytes]
```

## Queue Configurations

| Queue Name | Max Size | Purpose | Overflow Behavior |
|------------|----------|---------|-------------------|
| `processed_data_queue` | 100 | Main pipeline output | Drop oldest |
| `lte_tx_queue` | 200 | LTE transmission buffer | Drop oldest |
| `radio_tx_queue` | 200 | Radio transmission buffer | Drop oldest |
| `can_tx_queue` | 50 | CAN bus retransmission | Drop oldest |
| `csv_queue` | 500 | CSV write buffer | Drop oldest |
| `dashboard_queue` | 10 | GUI update buffer | Keep latest |

## Performance Targets

### Critical Path (Thread 0)
- **Target processing time**: < 50ms per message
- **Message rate**: 3 Hz (333ms period)
- **Headroom**: 6.6x safety margin
- **Breakdown**:
  - CAN RX: ~2ms
  - GPS read from LTE modem: ~5-10ms
  - Lap counter computation: ~5-15ms
  - Byte array modification: ~1ms
  - Queue operations: ~1ms
  - **Total**: ~15-30ms typical

### Parallel Processing (Threads 1-6)
- **LTE transmission**: Fire-and-forget with retry queue
- **Radio transmission**: Fire-and-forget with retry queue
- **CAN TX**: Best effort, < 100ms target
- **CSV writes**: Batched every 1 second (30-50 messages)
- **NN buffer**: Accumulate until 1000 samples (~5 minutes @ 3Hz)
- **Dashboard**: 1Hz refresh rate

### System Monitoring (Thread 7)
- **Health checks**: Every 1 second
- **Performance stats**: Every 10 seconds
- **Metrics tracked**:
  - Message processing rate (target: 3 Hz)
  - Queue depths (alert if > 80% full)
  - Thread liveness (critical threads must stay alive)
  - Processing latency (alert if > 50ms on Thread 0)

## Integration Points

### External Modules Required

1. **can_snooper/** - Existing CAN communication module
   - SocketCAN interface to `can0`
   - Message parsing with sc1-data-format
   - WebSocket API for debugging

2. **lap_counter/** - GPS-based lap counting (in development)
   - Input: `update_position(lat: float, lon: float)`
   - Output: `{lap_count, current_section, lap_duration}`
   - Performance requirement: < 15ms computation time

3. **data_logger/** - CSV logging to USB drive
   - Batch write interface: `write_batch(List[processed_data])`
   - USB drive mounting and failure recovery
   - File rotation and cleanup

4. **lte_modem/** - EG25-G GPS interface (to be created)
   - AT command interface: `AT+QGPSLOC?`
   - NMEA parsing for lat/lon extraction
   - Fallback to external GPS module if GNSS unavailable

5. **telemetry/** - Existing C++ backend integration
   - DTI (Data Transmission Interface) for LTE/Radio
   - SQL transmission for cloud data
   - UDP transmission for chase car

6. **neural_network/** - Future: PyTorch inference (next sprint)
   - Model interface for power optimization
   - CAN publisher for optimized outputs
   - Buffer management and inference triggering

### sc1-data-format Integration

#### Additions Required:
```json
{
  "lap_count": [2, "uint16", "", 0, 9999, "Software;Lap Counter"],
  "current_section": [1, "uint8", "", 0, 255, "Software;Lap Counter"],
  "lap_duration": [4, "uint32", "ms", 0, 600000, "Software;Lap Counter"],
  "optimized_target_power": [4, "float", "kW", 0, 10, "Race Strategy;Model Outputs"]
}
```

#### CAN Message IDs:
- `0x400`: Lap counter data (lap_count, current_section)
- `0x401`: Lap timing (lap_duration)
- `0x402`: Race strategy outputs (future: optimized_target_power)

## Error Handling & Recovery

### Critical Path Failures
- **CAN RX timeout**: Continue loop, log warning
- **GPS unavailable**: Use cached position or skip lap counter update
- **Lap counter error**: Use previous values, continue pipeline
- **Queue overflow**: Drop oldest message, log warning

### Transmission Failures
- **LTE failure**: Buffer in queue, retry with exponential backoff
- **Radio failure**: Buffer in queue, retry with exponential backoff
- **CAN TX failure**: Log error, continue (non-critical)

### I/O Failures
- **CSV write error**: Buffer in memory, retry next batch
- **USB drive unmounted**: Pause CSV logging, alert system
- **Disk full**: Rotate/delete old files, resume logging

### Thread Failures
- **Critical thread crash**: Log fatal error, attempt restart
- **Non-critical thread crash**: Log warning, system continues
- **Deadlock detection**: Watchdog timer restarts hung threads

## Deployment Configuration

### Raspberry Pi 4 Resource Allocation
- **CPU Core 0**: CAN RX + GPS + Lap Counter (priority -10)
- **CPU Core 1**: LTE/Radio transmission threads
- **CPU Core 2**: CSV logging + NN buffer (priority +10)
- **CPU Core 3**: Dashboard + system management

### Hardware Interfaces
- **CAN bus**: SocketCAN via Waveshare RS485 CAN HAT
- **GPS**: EG25-G LTE modem GNSS (AT+QGPSLOC)
- **LTE**: EG25-G Mini PCIe module (150 Mbps downlink)
- **Radio**: RFD900A (250 Kbps max, 902-928 MHz)
- **USB Drive**: Mount at `/media/usb0` for CSV logging

### System Services (systemd)
- `sc2-driver-io.service`: Main application
- `textual-dashboard.service`: Optional GUI frontend
- `can-interface.service`: SocketCAN setup
- `usb-automount.service`: USB drive management

## Future Enhancements (Next Sprint)

1. **Neural Network Integration**
   - PyTorch model inference for power optimization
   - Buffer management and inference triggering
   - CAN publication of optimized outputs

2. **Cloud Infrastructure**
   - Google Cloud migration for file sync server
   - BigQuery integration for telemetry analytics
   - Mobile app backend deployment

3. **Advanced Analytics**
   - Real-time lap time prediction
   - Battery optimization recommendations
   - Race strategy dashboard

4. **Reliability Improvements**
   - Watchdog timer for thread health
   - Automatic failover for GPS sources
   - Enhanced error recovery and logging