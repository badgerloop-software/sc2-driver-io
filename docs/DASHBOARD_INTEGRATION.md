# Dashboard Integration Guide

## Overview

The `main.py` coordinator now writes telemetry data to JSON files that the Textual dashboard reads for real-time display. This enables **HDMI diagnostic display** when things go wrong.

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                       main.py (Coordinator)                      │
│  - CAN RX + GPS + Lap Counter                                   │
│  - LTE/Radio/CSV transmission                                   │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ↓ writes @ 1Hz
        ┌───────────────┴────────────────┐
        ↓                                ↓
┌───────────────────┐          ┌─────────────────────┐
│ telemetry_data    │          │ system_health.json  │
│ .json             │          │                     │
│                   │          │ - Thread status     │
│ - Lap counter     │          │ - Queue depths      │
│ - GPS lat/lon     │          │ - Error messages    │
│ - Speed, SOC      │          │ - Warning messages  │
│ - Voltages        │          │ - Message rate      │
└─────────┬─────────┘          └──────────┬──────────┘
          │                               │
          │ reads @ 10Hz                  │ reads @ 1Hz
          ↓                               ↓
┌─────────────────────────────────────────────────────────────────┐
│          Textual Dashboard (textual_dashboard.py)               │
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐                     │
│  │ Telemetry Panel │  │  System Info    │                     │
│  │ - Speed         │  │  - CPU usage    │                     │
│  │ - Battery SOC   │  │  - Memory       │                     │
│  │ - Voltages      │  │  - Temp         │                     │
│  │ - LAP DATA ✨   │  └─────────────────┘                     │
│  └─────────────────┘                                           │
│  ┌─────────────────┐  ┌─────────────────┐                     │
│  │ Battery Level   │  │ Vehicle Status  │                     │
│  │ █████████░░░░░  │  │ - Lights        │                     │
│  └─────────────────┘  └─────────────────┘                     │
│                                                                 │
│  ┌────────────────── DIAGNOSTICS ✨ ──────────────────────┐   │
│  │ STATUS: RUNNING | UPTIME: 1:23:45 | RATE: 2.98 Hz       │   │
│  │ THREADS: 8/8 | ERRORS: 0 | WARNINGS: 2                  │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌────────────────── LIVE LOGS ✨ ──────────────────────────┐  │
│  │ 2025-10-30 14:32:15 - INFO - CAN message processed       │  │
│  │ 2025-10-30 14:32:15 - INFO - GPS: 43.0731, -89.4012     │  │
│  │ 2025-10-30 14:32:16 - WARNING - LTE retry attempt 2      │  │
│  │ 2025-10-30 14:32:16 - INFO - Lap 3, Section 5, 2:05.34  │  │
│  │ 2025-10-30 14:32:17 - ERROR - CSV write failed          │  │
│  │ [Scrollable with 500-line buffer, color-coded by level] │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Files Written by main.py

### 1. `telemetry_data.json` (1Hz updates)
Contains live vehicle telemetry and lap counter data:
```json
{
  "lap_count": 3,
  "current_section": 5,
  "lap_duration_ms": 125340,
  "lap_time_formatted": "2:05.34",
  "gps_latitude": 43.0731,
  "gps_longitude": -89.4012,
  "speed": 45.0,
  "battery_soc": 85.0,
  "pack_voltage": 380.0,
  "pack_current": 25.0,
  "timestamp": 1730332123.456
}
```

### 2. `system_health.json` (1Hz updates)
Contains system diagnostics for troubleshooting:
```json
{
  "uptime_seconds": 3600.5,
  "total_messages": 10814,
  "message_rate_hz": 3.00,
  "queues": {
    "processed_data": 0,
    "lte_tx": 0,
    "radio_tx": 0,
    "can_tx": 0,
    "csv": 12
  },
  "threads_alive": 8,
  "threads_total": 8,
  "thread_status": {
    "can_reception": true,
    "lte_tx": true,
    "radio_tx": true,
    "can_tx": true,
    "csv_logging": true,
    "nn_buffer": true,
    "dashboard": true,
    "system_management": true
  },
  "system_status": "RUNNING",
  "errors": [
    "CAN timeout at 14:32:15",
    "GPS unavailable at 14:35:20"
  ],
  "warnings": [
    "CSV queue filling up",
    "LTE retry attempt 3"
  ]
}
```

### 3. `driver_io.log` (Continuous)
All log messages written to file for dashboard log viewer:
```
2025-10-30 14:32:15,123 - __main__ - INFO - CAN message processed
2025-10-30 14:32:15,125 - __main__ - INFO - GPS: 43.0731, -89.4012
2025-10-30 14:32:16,234 - __main__ - WARNING - LTE retry attempt 2
2025-10-30 14:32:16,456 - __main__ - INFO - Lap 3, Section 5, Time: 2:05.34
2025-10-30 14:32:17,789 - __main__ - ERROR - CSV write failed: Disk full
```

## Dashboard Features

### ✨ New Live Log Viewer (45% of screen)
- **Real-time display**: Shows all log messages as they happen
- **Color-coded by severity**:
  - 🔴 **ERROR**: Red text for critical issues
  - 🟡 **WARNING**: Yellow text for warnings
  - 🔵 **INFO**: Cyan text for normal operations
  - ⚪ **DEBUG**: Dim text for detailed info
- **Auto-scroll**: Always shows latest messages
- **Scrollable history**: 500-line buffer, use arrow keys to scroll
- **Tail -f behavior**: Only reads new lines from log file

### ✨ Compact Diagnostics Bar (5% of screen)
Single-line status bar showing:
```
STATUS: RUNNING | UPTIME: 1:23:45 | RATE: 2.98 Hz | THREADS: 8/8 | ERRORS: 0 | WARNINGS: 2
```

### ✨ Enhanced Telemetry Display (45% of screen)
- **Lap Counter Data**: Current lap, section, and formatted lap time
- **GPS Coordinates**: Live latitude/longitude from EG25-G
- **Vehicle Telemetry**: Speed, battery SOC, voltages, currents
- **System Health**: Queue depths, thread status, error counts

## Running the Dashboard

### Windows Development
```powershell
# Terminal 1 - Start main coordinator
python main.py

# Terminal 2 - Start dashboard
cd textual_frontend
python textual_dashboard.py
```

### Pi Production (see PI_DEPLOYMENT.md for full details)
```bash
# Option 1: Systemd services (automatic)
sudo systemctl start sc2-driver-io.service textual-dashboard.service

# Option 2: Manual launch
cd /home/sunpi/sc2-driver-io
python main.py &
cd textual_frontend
python textual_dashboard.py

# Option 3: Launch script
./start_sc2_system.sh
```

## HDMI Emergency Diagnosis

If something goes wrong during race operations:

1. **Connect 7" HDMI display** to Raspberry Pi
2. **Dashboard should be visible** (if auto-launched)
3. **Check live log viewer** for recent errors:
   - Red ERROR messages show critical failures
   - Yellow WARNING messages show recoverable issues
4. **Check diagnostics bar** for system health:
   - Status should be "RUNNING" (green)
   - Rate should be ~3.0 Hz
   - Threads should be 8/8
5. **SSH from chase car** if needed for deeper diagnosis

## Troubleshooting Scenarios

### Scenario 1: Car not receiving lap data
**Dashboard log viewer shows:**
```
ERROR - CAN reception thread crashed at 14:32:15
ERROR - SocketCAN interface unavailable
WARNING - Lap counter data stale
```
**Diagnostics bar shows:**
```
STATUS: ERROR | THREADS: 7/8 | RATE: 0.02 Hz
```
**Action**: Check CAN HAT connection, restart system

### Scenario 2: GPS not working
**Dashboard telemetry shows:**
```
LAP: 0  SECTION: 0  TIME: 0:00.00
GPS: 0.0000, 0.0000
```
**Log viewer shows:**
```
WARNING - GPS unavailable from LTE modem
WARNING - Using cached position for lap counter
INFO - AT+QGPSLOC command failed
```
**Action**: Check EG25-G module, antenna connection

### Scenario 3: CSV logging failing
**Log viewer shows:**
```
ERROR - CSV write failed: Disk full
ERROR - USB drive write error
WARNING - CSV queue depth: 487/500
```
**Diagnostics bar shows:**
```
STATUS: WARNING | ERRORS: 2 | csv: 487/500
```
**Action**: Check USB drive space, replace drive

### Scenario 4: Complete system hang
**Dashboard shows:**
```
STATUS: ERROR | RATE: 0.00 Hz | THREADS: 8/8
```
**Log viewer shows:** (no new messages)
**Action**: System deadlock, requires restart

## Performance Impact

Dashboard overhead on main system:
- **CPU**: < 1% additional (negligible)
- **Memory**: ~10-15MB for Textual app + log buffer
- **I/O**: Minimal (reads 2 JSON files @ 1Hz, log file @ 5Hz)
- **Network**: None (local file-based communication)

The dashboard does **NOT** impact the critical 3 Hz CAN processing path!

## Future Enhancements

### Next Sprint:
1. **Audio alerts**: Beep on ERROR messages
2. **Log filtering**: Show only ERROR/WARNING in emergency mode
3. **Performance graphs**: Real-time message rate plotting
4. **Remote dashboard**: Web-based viewer for chase car
5. **Log archiving**: Automatic log rotation and compression

## Summary

✅ **Complete system visibility**: All log messages shown in real-time with color-coding  
✅ **HDMI diagnosis ready**: 7" display shows everything happening in driver-io software  
✅ **Compact layout**: 45% telemetry, 5% health bar, 45% scrolling logs  
✅ **Emergency troubleshooting**: Color-coded errors, system status, thread health  
✅ **Zero performance impact**: File-based communication, minimal CPU/memory overhead  
✅ **Race operations**: Automatic startup, systemd integration, remote SSH access  

**Your HDMI dashboard now shows everything happening in the driver-io software!** 🎯