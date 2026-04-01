# SC2 Driver IO - Architecture Review & Recommendations

**Date:** January 8, 2026  
**Reviewer:** Architecture Analysis (Opus)  
**Sprint Duration:** 8 weeks  
**Goal:** Modernize solar car driver IO system with clear data flow pipeline  
**Last status refresh:** April 1, 2026

> **How to read this document:** The **Executive Summary** and most sections that follow capture the **January 2026** review and recommendations. For **current implementation status** on the vehicle repo, read **[Status snapshot — April 1, 2026](#status-snapshot--april-1-2026)** first, then use the rest as historical design context.

---

## Status snapshot — April 1, 2026

This section records where **`badgerloop-software/sc2-driver-io`** (branch `shobhin/driverIO`) actually stands relative to the review below.

### Shipped or materially changed

- **InfluxDB cloud path (C++):** The [`sc2-telemetry-tester`](https://github.com/badgerloop-software/sc2-telemetry-tester) branch [`tester--cpp`](https://github.com/badgerloop-software/sc2-telemetry-tester/tree/tester--cpp) was merged with **`--allow-unrelated-histories`** so upstream commit authorship is preserved. New top-level **`cpp/`** tree includes `TelemetryRecord`, `InfluxWriter` (v2 Line Protocol over HTTP via **libcurl**), `CsvParser`, standalone binary **`sc2_telemetry_tester`**, and **`sc2_telemetry_tests`**. Configuration via **`.env`** / **`.env.example`** (`INFLUX_URL`, `INFLUX_TOKEN`, `INFLUX_ORG`, `INFLUX_BUCKET`). Details: [`cpp/README_CPP.md`](../cpp/README_CPP.md).
- **Legacy cloud stack removed from tree:** Node/Supabase tester (`src/*.js`, `package.json`, `sql/create_tables.sql`) and duplicate **`data/data_format.json`** were dropped. Canonical signal definitions remain the **`sc-data-format`** submodule (`sc-data-format/format.json`).
- **Build system:** Root **`CMakeLists.txt`** requires **CMake ≥ 3.15**, **`find_package(CURL REQUIRED)`**, and **`add_subdirectory(cpp)`** so one configure step builds **`sc2-driver-io`** plus the Influx tester targets. Raspberry Pi OS needs **`libcurl4-openssl-dev`**.
- **Supabase C++ client removed earlier:** **`telemetry/sql.cpp`** is gone. **`backendprocesses.h`** was slimmed to stop including **`telemetry/sql.cpp`**, **`tcp.cpp`**, and **`udp.cpp`** (those files are not part of the include graph for the main binary anymore). **`BackendProcesses` is still only declared**—there is **no in-tree implementation**; any future multi-channel DTI orchestration must add a `.cpp` or remove the type.
- **Operations:** Optional **`services/systemd/sc2-influx-tester.service`** runs CSV replay/stream mode against Influx for **bench / lab** validation (not a substitute for live CAN).

### Gaps (still true or newly visible)

- **Live CAN → Influx:** Production path is **not** wired. The merged code proves **CSV → `TelemetryRecord` → Influx**; **`can_bridge` / `DataUnpacker`** do not yet populate **`TelemetryRecord`** or call **`InfluxWriter::writeBatch`** on a timer.
- **Format path naming:** **`data_processor/dataUnpacker.cpp`** still opens paths like **`sc1-data-format/format.json`** in places; the repo submodule is **`sc-data-format`**. Align paths and verify on-target (build cwd, systemd `WorkingDirectory`).
- **Diagrams in §2 below** still show **`sql.cpp` → LTE** as the cloud path; mentally substitute the **`cpp/InfluxWriter`** pipeline + note that legacy **`sql.cpp`** is removed until/unless replaced.
- **Fleet / tooling:** Some Pis have had **DNS resolution failures for `github.com`** until resolver or **`/etc/hosts`** workarounds; fix **systemd-resolved / network** rather than relying on static host entries long term.

### Recommended next work (priority)

1. **Implement live cloud upload:** From the unpacked byte buffer (or per-signal map), fill **`TelemetryRecord`** (or emit Line Protocol fields) and **`InfluxWriter::writeBatch`** ~1 Hz (see upstream README “Porting to Raspberry Pi”).
2. **`BackendProcesses`:** Either implement constructors / **`threadProcedure`** for the intended DTI list or delete the abstraction to avoid a false sense of completeness.
3. **Re-audit Qt:** Run a repo-wide check for Qt includes/macros; if clean, update §6–§7 of this document so it matches reality.
4. **Security:** Ensure **`.env`** for Influx is excluded from images/backups where inappropriate; extend **`docs/SECURITY.md`** with token rotation and bucket policy notes.
5. **CI (optional):** Build and run **`sc2_telemetry_tests`** on pull requests.

---

## Executive Summary

After reviewing your codebase, I have both **good news and critical concerns**. Your foundation is solid—the telemetry system, lap counter algorithm, and CAN utilities are well-designed. However, I've identified several architectural inconsistencies that will cause problems if not addressed early in the sprint.

### Key Findings:
1. ✅ **Telemetry system (C++)** - Well-architected DTI pattern, preserve as-is
2. ✅ **Lap counter algorithm** - Robust implementation, keep in Python
3. ✅ **CAN utilities** - Clean signal parsing with format JSON integration (submodule is **`sc-data-format`**; some code paths may still reference legacy `sc1-data-format` paths—see April 2026 status)
4. ⚠️ **Qt dependencies (Jan 2026 finding)** - Original review flagged Qt in `Serial.cpp`, `DataUnpacker.cpp`, `dataFetcher.cpp`; headless/Qt removal has progressed—**re-audit** before treating this as current
5. ⚠️ **Two main entry points (resolved)** - `main.cpp` and `services/coordinator.py` (coordinator replaces `main.py`)
6. ❌ **Ethernet-based data fetcher** - `dataFetcher.cpp` uses TCP server, needs CAN replacement (or confirm deprecated)
7. ❌ **IPC strategy unclear** - JSON files for UI, but no defined strategy for CAN→C++ bridge (Unix socket / shared memory direction exists in code—validate under systemd)
8. 🔄 **Cloud upload (April 2026)** - **InfluxDB** path exists in **`cpp/`**; **live CAN → Influx** integration still outstanding

---

## 1. Proposed Directory Structure

```
sc2-driver-io/
├── README.md
├── EVOLUTION_PLAN.md
├── ARCHITECTURE_REVIEW.md          # This document
├── config.json                      # Runtime configuration
│
├── core/                            # NEW: Shared core components
│   ├── ipc/                         # Inter-process communication
│   │   ├── shared_data.py           # Shared memory definitions
│   │   ├── message_queue.py         # Named pipe/Unix socket wrappers
│   │   └── telemetry_bridge.cpp     # C++ side of Python↔C++ bridge
│   └── data_format/                 # Move from sc1-data-format
│       └── format.json              # Or keep as submodule
│
├── can_bus/                         # RENAMED from can_utils (clearer purpose)
│   ├── __init__.py
│   ├── can_reader.py                # Main CAN message ingestion (single reader)
│   ├── can_writer.py                # CAN message transmission
│   ├── signal_parser.py             # Renamed from read_can_messages.py
│   ├── data_classes.py              # Keep existing
│   └── csv_logger.py                # Integrated CSV logging (was csv_writer.py)
│
├── lap_counter/                     # Keep existing location
│   ├── __init__.py
│   ├── lap_counter.py               # Rename from lapscounter.py
│   └── track_definitions.py         # NEW: Track section boundary configs
│
├── telemetry/                       # RENAMED from backend/telemetrylib
│   ├── CMakeLists.txt
│   ├── DTI.h                        # Keep as-is (excellent pattern)
│   ├── telemetry.h/.cpp             # Keep, remove Qt dependencies
│   ├── serial.cpp                   # RFD900A - NEEDS Qt removal
│   ├── (sql.cpp removed — was Supabase; cloud = cpp/InfluxWriter + InfluxDB)
│   ├── udp.cpp                      # Chase car UDP (still in tree)
│   └── can_bridge.cpp               # Receives CAN-related data from Python coordinator
│
├── cpp/                             # MERGED from sc2-telemetry-tester tester--cpp
│   ├── include/                     # TelemetryRecord, InfluxWriter, CsvParser
│   ├── src/                         # libcurl Line Protocol client + tester main
│   └── tests/                       # sc2_telemetry_tests
│
├── data_processor/                  # RENAMED from DataProcessor
│   ├── CMakeLists.txt
│   ├── data_unpacker.h/.cpp         # NEEDS Qt removal
│   └── data_validator.cpp           # NEW: Data validation/sanity checks
│
├── gps/                             # Keep existing
│   ├── gps.h/.cpp                   # May deprecate if using EG25-G GNSS
│   └── eg25g_gnss.cpp               # NEW: EG25-G integrated GPS
│
├── textual_frontend/                # Keep existing location
│   ├── dashboard.py                 # Main dashboard (keep textual_dashboard.py)
│   ├── dashboard.css
│   └── widgets/                     # NEW: Modular widget components
│       ├── telemetry_display.py
│       ├── network_info.py
│       └── system_info.py
│
├── neural_network/                  # NEW: Placeholder for next sprint
│   ├── __init__.py
│   ├── interface.py                 # Data accumulation buffer interface
│   ├── can_publisher.py             # NN output → CAN bus
│   └── README.md                    # Interface spec for Race Strategy team
│
├── services/                        # NEW: System service definitions
│   ├── coordinator.py               # Main Python orchestrator (rename from main.py)
│   ├── systemd/                     # Service unit files
│   │   ├── sc2-telemetry.service
│   │   ├── sc2-coordinator.service
│   │   └── sc2-dashboard.service
│   └── startup_sequence.py          # Dependency-ordered startup
│
├── backend/                         # Keep for file sync only
│   └── file_sync/                   # Keep existing structure
│
├── 3rdparty/                        # Keep existing
│   ├── rapidjson/
│   └── serial/serialib.*            # Use this instead of QSerialPort!
│
├── build/                           # CMake build output
├── CMakeLists.txt                   # Root CMake
└── main.cpp                         # C++ entry point (headless telemetry)
```

### Key Structural Changes:

1. **`can_bus/` replaces `can_utils/`** - Clearer naming, single source of truth for CAN operations
2. **`telemetry/` flattened** - Remove nested `backend/telemetrylib/` structure
3. **`services/` for orchestration** - Separates coordination logic from core functionality
4. **`core/ipc/`** - Central location for all inter-process communication code
5. **`neural_network/`** - Clean integration point for Race Strategy team

---

## 2. Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA FLOW ARCHITECTURE                             │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────────┐
                              │   CAN Bus (can0) │
                              │  Waveshare HAT   │
                              └────────┬─────────┘
                                       │
                                       ▼
                    ┌──────────────────────────────────┐
                    │     can_bus/can_reader.py        │ ◄─── SINGLE READER
                    │   (python-can + SocketCAN)       │      No data races
                    │   Parses via signal_parser.py    │
                    └──────────────────┬───────────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
         ┌──────────┴──────────┐       │       ┌──────────┴──────────┐
         │                     │       │       │                     │
         ▼                     ▼       ▼       ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Path A: CSV    │  │  Path B: Lap    │  │  Path C: C++    │  │  Path D: UI     │
│    Logger       │  │    Counter      │  │   Telemetry     │  │   Display       │
├─────────────────┤  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤
│ csv_logger.py   │  │ lap_counter.py  │  │ can_bridge.cpp  │  │ dashboard.py    │
│ Buffered writes │  │ GPS position    │  │ (Unix Socket)   │  │ (Shared Memory) │
│ to USB drive    │  │ calculations    │  │                 │  │                 │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │                    │
         ▼                    │                    ▼                    │
   ┌───────────┐              │           ┌───────────────┐             │
   │ USB Drive │              │           │  Telemetry    │             │
   │ /mnt/usb  │              │           │   System      │             │
   └───────────┘              │           ├───────────────┤             │
                              │           │ serial.cpp    │──► RFD900A Radio
                              │           │ udp.cpp       │──► Chase Car
                              │           │ cpp/InfluxWriter │──► InfluxDB Cloud (v2 write API)
                              │           └───────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ can_writer.py   │ ◄─── Lap data published back
                    │ send_messages() │      to CAN bus
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   CAN Bus       │ ◄─── Other ECUs can read
                    └─────────────────┘      lap count data


            ┌───────────────────────────────────────────┐
            │         NEURAL NETWORK (FUTURE)           │
            ├───────────────────────────────────────────┤
            │                                           │
            │   ┌─────────────┐     ┌───────────────┐   │
            │   │ Data Buffer │────►│ NN Inference  │   │
            │   │ (N minutes) │     │ (PyTorch)     │   │
            │   └─────────────┘     └───────┬───────┘   │
            │                               │           │
            │                               ▼           │
            │                       ┌───────────────┐   │
            │                       │ can_writer.py │   │
            │                       │ NN decisions  │   │
            │                       └───────────────┘   │
            └───────────────────────────────────────────┘
```

---

## 3. Interface Specifications

### 3.1 CAN Reader → All Consumers (Fan-out Interface)

**Recommendation: Use callback registration pattern**

```python
# can_bus/can_reader.py

from dataclasses import dataclass
from typing import Callable, List, Dict, Any
import can
import threading
import queue

@dataclass
class CANMessage:
    """Standardized CAN message format for all consumers"""
    can_id: int
    signal_name: str
    value: float | bool
    timestamp: float
    raw_data: bytes

class CANReader:
    """
    Single CAN reader that distributes messages to registered consumers.
    Runs in dedicated thread with real-time priority.
    """
    
    def __init__(self, channel: str = "can0"):
        self.bus = can.interface.Bus(channel=channel, bustype="socketcan")
        self._consumers: Dict[str, Callable[[CANMessage], None]] = {}
        self._running = False
        self._thread = None
        
        # Per-consumer queues for async delivery
        self._queues: Dict[str, queue.Queue] = {}
        
    def register_consumer(
        self, 
        name: str, 
        callback: Callable[[CANMessage], None],
        queue_size: int = 1000,
        filter_ids: List[int] = None
    ) -> None:
        """
        Register a consumer to receive CAN messages.
        
        Args:
            name: Unique consumer identifier (e.g., "csv_logger", "lap_counter")
            callback: Function called with each CANMessage
            queue_size: Max queued messages before dropping
            filter_ids: Optional list of CAN IDs this consumer cares about
        """
        self._consumers[name] = {
            'callback': callback,
            'filter_ids': set(filter_ids) if filter_ids else None,
            'queue': queue.Queue(maxsize=queue_size),
            'dropped': 0
        }
    
    def start(self) -> None:
        """Start the CAN reader thread"""
        self._running = True
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()
        
    def _read_loop(self) -> None:
        """Main read loop - distributes messages to all consumers"""
        while self._running:
            msg = self.bus.recv(timeout=0.01)  # 10ms timeout
            if msg is None:
                continue
                
            parsed = self._parse_message(msg)
            if parsed is None:
                continue
                
            # Fan out to all registered consumers
            for name, consumer in self._consumers.items():
                # Apply filter if specified
                if consumer['filter_ids'] and parsed.can_id not in consumer['filter_ids']:
                    continue
                    
                try:
                    consumer['queue'].put_nowait(parsed)
                except queue.Full:
                    consumer['dropped'] += 1
```

### 3.2 CAN → C++ Telemetry Bridge

**Recommendation: Unix Domain Socket (best latency/simplicity balance)**

```cpp
// telemetry/can_bridge.cpp

#include <sys/socket.h>
#include <sys/un.h>
#include <thread>
#include <vector>
#include <cstring>
#include <atomic>

#define SOCKET_PATH "/tmp/sc2_can_bridge.sock"
#define MAX_MSG_SIZE 64

struct CANBridgeMessage {
    uint32_t can_id;
    uint64_t timestamp_us;
    uint8_t data_len;
    uint8_t data[8];
} __attribute__((packed));

class CANBridge {
public:
    CANBridge() : running(false), socket_fd(-1) {}
    
    bool start() {
        // Create Unix domain socket
        socket_fd = socket(AF_UNIX, SOCK_DGRAM, 0);
        if (socket_fd < 0) return false;
        
        struct sockaddr_un addr;
        memset(&addr, 0, sizeof(addr));
        addr.sun_family = AF_UNIX;
        strncpy(addr.sun_path, SOCKET_PATH, sizeof(addr.sun_path) - 1);
        
        unlink(SOCKET_PATH);  // Remove stale socket
        
        if (bind(socket_fd, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
            close(socket_fd);
            return false;
        }
        
        running = true;
        recv_thread = std::thread(&CANBridge::receiveLoop, this);
        return true;
    }
    
    void setDataCallback(std::function<void(const CANBridgeMessage&)> cb) {
        callback = cb;
    }
    
private:
    void receiveLoop() {
        CANBridgeMessage msg;
        while (running) {
            ssize_t n = recv(socket_fd, &msg, sizeof(msg), 0);
            if (n == sizeof(msg) && callback) {
                callback(msg);
            }
        }
    }
    
    std::atomic<bool> running;
    int socket_fd;
    std::thread recv_thread;
    std::function<void(const CANBridgeMessage&)> callback;
};
```

```python
# Python side - sends to C++
# core/ipc/telemetry_bridge.py

import socket
import struct

class TelemetryBridge:
    """Sends CAN data to C++ telemetry system via Unix socket"""
    
    SOCKET_PATH = "/tmp/sc2_can_bridge.sock"
    MSG_FORMAT = "<IQB8s"  # can_id, timestamp_us, data_len, data[8]
    
    def __init__(self):
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        
    def send(self, can_id: int, data: bytes, timestamp_us: int) -> bool:
        """Send CAN message to C++ telemetry"""
        try:
            padded_data = data.ljust(8, b'\x00')[:8]
            packed = struct.pack(
                self.MSG_FORMAT,
                can_id,
                timestamp_us,
                len(data),
                padded_data
            )
            self.socket.sendto(packed, self.SOCKET_PATH)
            return True
        except Exception:
            return False
```

### 3.3 CAN → Textual UI (Shared Memory)

**Recommendation: Shared memory with memory-mapped file for UI**

```python
# core/ipc/shared_data.py

import mmap
import struct
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class TelemetrySnapshot:
    """All telemetry values for UI display"""
    speed: float = 0.0
    soc: float = 0.0
    pack_voltage: float = 0.0
    pack_current: float = 0.0
    motor_temp: float = 0.0
    pack_temp: float = 0.0
    
    # Lap counter data
    lap_count: int = 0
    current_section: int = 0
    section_time: float = 0.0
    
    # Status flags
    headlights: bool = False
    l_turn_led_en: bool = False
    r_turn_led_en: bool = False
    hazards: bool = False
    park_brake: bool = False
    
    # Timestamps
    last_update_us: int = 0

# Struct format: 6 floats + 3 ints + 5 bools + 1 long = 52 bytes
SNAPSHOT_FORMAT = "<6f3i5?Q"
SNAPSHOT_SIZE = struct.calcsize(SNAPSHOT_FORMAT)
SHM_PATH = "/tmp/sc2_telemetry_shm"

class SharedTelemetryWriter:
    """Writes telemetry data to shared memory (CAN reader side)"""
    
    def __init__(self):
        # Create or open shared memory file
        self.fd = os.open(SHM_PATH, os.O_RDWR | os.O_CREAT, 0o666)
        os.ftruncate(self.fd, SNAPSHOT_SIZE)
        self.mm = mmap.mmap(self.fd, SNAPSHOT_SIZE)
        
    def update(self, snapshot: TelemetrySnapshot) -> None:
        """Write new telemetry snapshot"""
        packed = struct.pack(
            SNAPSHOT_FORMAT,
            snapshot.speed, snapshot.soc, snapshot.pack_voltage,
            snapshot.pack_current, snapshot.motor_temp, snapshot.pack_temp,
            snapshot.lap_count, snapshot.current_section, int(snapshot.section_time * 1000),
            snapshot.headlights, snapshot.l_turn_led_en, snapshot.r_turn_led_en,
            snapshot.hazards, snapshot.park_brake,
            snapshot.last_update_us
        )
        self.mm.seek(0)
        self.mm.write(packed)


class SharedTelemetryReader:
    """Reads telemetry data from shared memory (UI side)"""
    
    def __init__(self):
        # Wait for shared memory file to exist
        while not os.path.exists(SHM_PATH):
            time.sleep(0.1)
        self.fd = os.open(SHM_PATH, os.O_RDONLY)
        self.mm = mmap.mmap(self.fd, SNAPSHOT_SIZE, prot=mmap.PROT_READ)
        
    def read(self) -> TelemetrySnapshot:
        """Read current telemetry snapshot"""
        self.mm.seek(0)
        data = self.mm.read(SNAPSHOT_SIZE)
        values = struct.unpack(SNAPSHOT_FORMAT, data)
        
        return TelemetrySnapshot(
            speed=values[0], soc=values[1], pack_voltage=values[2],
            pack_current=values[3], motor_temp=values[4], pack_temp=values[5],
            lap_count=values[6], current_section=values[7], 
            section_time=values[8] / 1000.0,
            headlights=values[9], l_turn_led_en=values[10], r_turn_led_en=values[11],
            hazards=values[12], park_brake=values[13],
            last_update_us=values[14]
        )
```

### 3.4 Lap Counter Output Interface

```python
# lap_counter/lap_counter.py - Updated interface

from dataclasses import dataclass
from typing import Optional
import struct

@dataclass
class LapData:
    """Output from lap counter for CAN transmission and display"""
    lap_count: int
    current_section: int
    section_time_ms: int  # milliseconds
    lap_time_ms: int      # milliseconds
    position_valid: bool
    timestamp_us: int
    
    def to_can_bytes(self) -> bytes:
        """Pack for CAN transmission (CAN ID 0x400, 0x401)"""
        # Message 1 (0x400): lap_count(4) + section(1) + flags(1) + reserved(2)
        msg1 = struct.pack("<IBBxx", self.lap_count, self.current_section, 
                          0x01 if self.position_valid else 0x00)
        
        # Message 2 (0x401): section_time(4) + lap_time(4)
        msg2 = struct.pack("<II", self.section_time_ms, self.lap_time_ms)
        
        return msg1, msg2
    
    @staticmethod
    def get_can_ids() -> list:
        """CAN IDs used by lap counter"""
        return [0x400, 0x401]
```

---

## 4. Threading/Process Model

### Recommended Architecture: Hybrid Multi-Process + Multi-Thread

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PROCESS ARCHITECTURE                                 │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ PROCESS 1: Python Coordinator (services/coordinator.py)                      │
│ Priority: Normal | Cores: 0-1 | Memory: ~50MB                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │ Thread 1        │  │ Thread 2        │  │ Thread 3        │              │
│  │ CAN Reader      │  │ CSV Logger      │  │ Lap Counter     │              │
│  │ Priority: HIGH  │  │ Priority: LOW   │  │ Priority: MED   │              │
│  │ Real-time       │  │ I/O bound       │  │ 10Hz GPS        │              │
│  │ <10ms latency   │  │ Buffered        │  │ updates         │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
│           │                   ▲                    │                         │
│           │                   │                    │                         │
│           └───────────────────┴────────────────────┘                         │
│                    Queues (thread-safe)                                      │
│                                                                              │
│  IPC OUT: Unix Socket ──────────────────────────────► Process 2              │
│  IPC OUT: Shared Memory ────────────────────────────► Process 3              │
│  CAN OUT: can_writer ───────────────────────────────► CAN Bus                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ PROCESS 2: C++ Telemetry (./build/sc2-driver-io)                            │
│ Priority: High (nice -10) | Core: 2 | Memory: ~15MB                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │ Thread 1        │  │ Thread 2        │  │ Thread 3        │              │
│  │ CAN Bridge      │  │ Serial/Radio    │  │ SQL/LTE         │              │
│  │ Unix Socket RX  │  │ RFD900A TX      │  │ EG25-G TX       │              │
│  │ Receives from   │  │                 │  │                 │              │
│  │ Python          │  │                 │  │                 │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
│                                                                              │
│  IPC IN: Unix Socket ◄──────────────────────────────── Process 1             │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ PROCESS 3: Textual UI (textual_frontend/dashboard.py)                       │
│ Priority: Low (nice +5) | Core: 3 | Memory: ~15MB                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Single-threaded async (Textual event loop)                                 │
│  10Hz update rate from shared memory                                        │
│                                                                              │
│  IPC IN: Shared Memory ◄────────────────────────────── Process 1             │
│                                                                              │
│  CRASH ISOLATION: If this dies, Processes 1 & 2 continue unaffected         │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ PROCESS 4 (FUTURE): Neural Network                                          │
│ Priority: Low | Cores: Any | Memory: ~200MB                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  Runs inference every few minutes                                           │
│  IPC IN: Subscribes to CAN data stream via Process 1                        │
│  IPC OUT: Publishes decisions via can_writer                                │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Why This Model?

| Decision | Rationale |
|----------|-----------|
| **Python GIL mitigation** | CAN reader releases GIL during socket operations; CSV logger is I/O-bound (GIL released); Lap counter math is fast (<1ms) |
| **Separate UI process** | Crash isolation; prevents GIL contention; can kill/restart independently |
| **C++ telemetry separate** | Real-time transmission guarantees; no Python GIL interference |
| **Unix socket for C++ bridge** | <1ms latency; simpler than shared memory; bidirectional capable |
| **Shared memory for UI** | Zero-copy for frequent updates; read-only for UI (safe) |

### Thread Priorities (Linux)

```python
# services/coordinator.py

import os

def set_thread_priority(thread_name: str) -> None:
    """Set appropriate priority for each thread"""
    priorities = {
        'can_reader': -10,    # High priority (requires root/CAP_SYS_NICE)
        'csv_logger': 5,      # Low priority (I/O bound)
        'lap_counter': 0,     # Normal priority
    }
    try:
        os.nice(priorities.get(thread_name, 0))
    except PermissionError:
        pass  # Fall back to default priority
```

---

## 5. Critical Issues Found in Current Code

### Issue 1: Qt Dependencies Still Present ❌

**Files requiring Qt removal:**

| File | Qt Usage | Replacement |
|------|----------|-------------|
| [Serial.cpp](backend/telemetrylib/Serial.cpp) | `QSerialPort`, `QTimer`, `QObject` | Use `3rdparty/serial/serialib.cpp` |
| [dataUnpacker.cpp](DataProcessor/dataUnpacker.cpp#L89-L107) | `QThread`, `qDebug`, signals/slots | `std::thread`, `std::cout`, callbacks |
| [dataFetcher.cpp](backend/dataFetcher.cpp) | `QTcpServer`, `QObject` | **DELETE** - replace with CAN bridge |
| [backendProcesses.cpp](backend/backendProcesses.cpp#L42-L57) | `emit`, signals/slots | Callback functions |

**Priority fix for Serial.cpp:**

```cpp
// telemetry/serial.cpp - Qt-free implementation using serialib

#include "DTI.h"
#include "3rdparty/serial/serialib.h"
#include <thread>
#include <atomic>
#include <chrono>

class Serial : public DTI {
public:
    Serial(const std::string& device, int baudRate = 115200) 
        : device_(device), running_(false) {
        
        // Open serial port using serialib
        if (serial_.openDevice(device.c_str(), baudRate) != 1) {
            throw std::runtime_error("Failed to open serial port: " + device);
        }
        
        // Start reconnection monitor thread
        running_ = true;
        monitor_thread_ = std::thread(&Serial::monitorConnection, this);
    }
    
    ~Serial() {
        running_ = false;
        if (monitor_thread_.joinable()) {
            monitor_thread_.join();
        }
        serial_.closeDevice();
    }
    
    void sendData(const std::vector<uint8_t>& bytes, long long timestamp) override {
        // Add framing tags
        std::vector<uint8_t> framed;
        framed.reserve(bytes.size() + 11);
        
        const char* start = "<bsr>";
        const char* end = "</bsr>";
        framed.insert(framed.end(), start, start + 5);
        framed.insert(framed.end(), bytes.begin(), bytes.end());
        framed.insert(framed.end(), end, end + 6);
        
        int result = serial_.writeBytes(framed.data(), framed.size());
        if (result < 0) {
            // Trigger reconnection
            needs_reconnect_ = true;
        }
    }
    
private:
    void monitorConnection() {
        while (running_) {
            if (needs_reconnect_) {
                serial_.closeDevice();
                std::this_thread::sleep_for(std::chrono::seconds(1));
                if (serial_.openDevice(device_.c_str(), 115200) == 1) {
                    needs_reconnect_ = false;
                }
            }
            std::this_thread::sleep_for(std::chrono::seconds(5));
        }
    }
    
    serialib serial_;
    std::string device_;
    std::atomic<bool> running_;
    std::atomic<bool> needs_reconnect_{false};
    std::thread monitor_thread_;
};
```

### Issue 2: Dual Main Entry Points ⚠️

You have both `main.cpp` and `main.py` trying to coordinate the system.

**Current confusion:**
- [main.cpp](main.cpp#L46-L77): Starts `DataUnpacker` which uses ethernet-based `DataFetcher`
- [main.py](main.py#L50-L100): Has its own thread coordination, expects external modules

**Recommendation:** Clear separation of concerns:

```
main.cpp:  ONLY starts C++ telemetry service (receives from Python via socket)
main.py:   Renamed to coordinator.py, orchestrates all Python components
```

### Issue 3: dataFetcher.cpp Uses Ethernet ❌

[dataFetcher.cpp](backend/dataFetcher.cpp) creates a TCP server waiting for ethernet connections. This needs to be **completely replaced** with CAN bus reception.

**Action:** Delete `dataFetcher.cpp` and replace with `can_bridge.cpp` that receives from Python's CAN reader via Unix socket.

### Issue 4: Format.json Missing CAN IDs

Your [sc1-data-format/format.json](sc1-data-format/format.json) has 6-element arrays:

```json
"speed": [4, "float", "mph", 0, 100, "MCC;Motor Controller I/O"]
```

But your [read_can_messages.py](can_utils/read_can_messages.py#L30-L50) expects 8 elements (including CAN ID and offset):

```python
can_id = int(s[-2], base=16)  # Expects hex CAN ID
offset = s[-1]                 # Expects byte offset
```

**This is a critical mismatch!** Either:
1. Update `format.json` to include CAN IDs, OR
2. Maintain a separate CAN mapping file

---

## 6. IPC Mechanism Comparison

| Method | Latency | Complexity | UI Suitability | C++ Bridge | Recommendation |
|--------|---------|------------|----------------|------------|----------------|
| JSON Files | 50-100ms | Low | ⚠️ Okay | ❌ Poor | **Deprecate** |
| Named Pipes | 1-5ms | Medium | ✅ Good | ✅ Good | Alternative |
| Unix Socket | <1ms | Medium | ✅ Good | ✅ **Best** | **Use for C++** |
| Shared Memory | <0.1ms | High | ✅ **Best** | ⚠️ Complex | **Use for UI** |
| ZeroMQ | 1-2ms | Medium | ✅ Good | ✅ Good | Overkill |

**Final recommendation:**
- **CAN → C++ Telemetry:** Unix Domain Socket (datagram mode)
- **CAN → Textual UI:** Memory-mapped shared file
- **Lap Counter → CAN:** Direct `can_writer.py` call

---

## 7. Answers to Your Specific Questions

### Q1: Python vs C++ for Lap Counter?

**Keep it in Python.** Here's why:

1. **Performance is adequate**: Your lap counter runs at 1Hz (GPS rate). Even with Python overhead, processing takes <1ms
2. **Algorithm complexity**: The geometry math in [lapscounter.py](lap_counter/lapscounter.py) is clean and maintainable
3. **Team velocity**: Your team member is developing in Python—switching languages mid-sprint wastes time
4. **No real-time requirements**: Lap counting can tolerate 10-50ms latency without affecting racing

**Exception:** If future requirements need <1ms precision timing, consider C++ rewrite.

### Q2: Single CAN Reader vs Multiple?

**Single reader, multiple consumers.** Never have multiple processes reading the same CAN bus:

```python
# WRONG - causes data races and missed messages
# Process A: can.interface.Bus(channel="can0")  
# Process B: can.interface.Bus(channel="can0")  # BAD!

# CORRECT - single reader with fan-out
reader = CANReader("can0")
reader.register_consumer("csv", csv_callback)
reader.register_consumer("lap", lap_callback)
reader.register_consumer("telemetry", telemetry_callback)
reader.start()
```

### Q3: Textual UI Data Latency

Your current JSON file approach adds 50-100ms. **This is acceptable** for 10Hz UI refresh, but borderline.

**Recommended upgrade path:**
1. **Week 1-2:** Keep JSON files (working solution)
2. **Week 3-4:** Migrate to shared memory (code provided above)
3. **Benefit:** Latency drops to <1ms, ready for any future requirements

### Q4: If UI Crashes, Should It Auto-Restart?

**Yes, with limits.** Use systemd:

```ini
# services/systemd/sc2-dashboard.service

[Unit]
Description=SC2 Textual Dashboard
After=sc2-coordinator.service
BindsTo=sc2-coordinator.service  # If coordinator dies, dashboard stops

[Service]
ExecStart=/usr/bin/python3 /home/sunpi/sc2-driver-io/textual_frontend/dashboard.py
Restart=on-failure
RestartSec=3
StartLimitBurst=5          # Max 5 restarts
StartLimitIntervalSec=60   # Within 60 seconds
Nice=5                     # Low priority

[Install]
WantedBy=multi-user.target
```

### Q5: LTE vs Radio Interference

Looking at your [backendProcesses.cpp](backend/backendProcesses.cpp#L42-L57):

```cpp
obj[0]=new SQL(...);  // LTE
obj[1]=new UDP(...);  // Chase car
obj[2] = new Serial("/dev/ttyS0");  // Radio
```

**Likely causes of interference:**

1. **USB bus contention**: EG25-G and RFD900A may share USB host controller
2. **Thermal throttling**: EG25-G heats up → affects adjacent components
3. **Power supply**: Both modules have high peak current draw

**Debugging steps:**
```bash
# Check USB topology
lsusb -t

# Monitor USB errors
dmesg -w | grep -i usb

# Monitor EG25-G temperature
echo "AT+QTEMP" > /dev/ttyUSB2
```

**Mitigation:** Stagger transmissions:
```cpp
void sendWithDelay(DTI* channel, const std::vector<uint8_t>& data, long long ts) {
    static std::mutex tx_mutex;
    static auto last_tx = std::chrono::steady_clock::now();
    
    std::lock_guard<std::mutex> lock(tx_mutex);
    
    // Wait at least 50ms between transmissions
    auto now = std::chrono::steady_clock::now();
    auto elapsed = std::chrono::duration_cast<std::chrono::milliseconds>(now - last_tx);
    if (elapsed.count() < 50) {
        std::this_thread::sleep_for(std::chrono::milliseconds(50 - elapsed.count()));
    }
    
    channel->sendData(data, ts);
    last_tx = std::chrono::steady_clock::now();
}
```

---

## 8. Startup/Shutdown Sequence

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         STARTUP SEQUENCE                                     │
└─────────────────────────────────────────────────────────────────────────────┘

Boot
  │
  ├──► [1] Hardware Init (systemd)
  │       ├── Load CAN kernel modules: can, can_raw, mcp251x
  │       ├── Configure CAN interface: ip link set can0 up type can bitrate 500000
  │       └── Wait for /dev/ttyS0 (RFD900A), /dev/ttyUSB* (EG25-G)
  │
  ├──► [2] C++ Telemetry (sc2-telemetry.service)
  │       ├── Opens serial port for RFD900A
  │       ├── Initializes SQL/LTE connection
  │       ├── Creates Unix socket: /tmp/sc2_can_bridge.sock
  │       └── Waits for data from Python coordinator
  │
  ├──► [3] Python Coordinator (sc2-coordinator.service)
  │       ├── After: sc2-telemetry.service
  │       ├── Initializes CAN reader
  │       ├── Connects to Unix socket
  │       ├── Creates shared memory: /tmp/sc2_telemetry_shm
  │       ├── Starts CSV logger thread
  │       ├── Starts lap counter thread
  │       └── Begins CAN message processing
  │
  └──► [4] Textual Dashboard (sc2-dashboard.service) [OPTIONAL]
          ├── After: sc2-coordinator.service
          ├── Opens shared memory (read-only)
          └── Starts 10Hz update loop


┌─────────────────────────────────────────────────────────────────────────────┐
│                        SHUTDOWN SEQUENCE                                     │
└─────────────────────────────────────────────────────────────────────────────┘

SIGTERM received
  │
  ├──► [1] Dashboard (if running)
  │       └── Clean exit, close shared memory
  │
  ├──► [2] Python Coordinator
  │       ├── Signal all threads to stop
  │       ├── Flush CSV buffer to disk
  │       ├── Close Unix socket
  │       ├── Wait for threads (5s timeout)
  │       └── Close CAN bus
  │
  └──► [3] C++ Telemetry
          ├── Flush pending transmissions
          ├── Close serial port
          └── Clean exit
```

### Systemd Service Files

```ini
# /etc/systemd/system/sc2-telemetry.service
[Unit]
Description=SC2 C++ Telemetry Service
After=network.target
Wants=can-setup.service

[Service]
Type=simple
ExecStart=/home/sunpi/sc2-driver-io/build/sc2-driver-io
Restart=always
RestartSec=5
Nice=-10
User=root  # Needed for serial port access

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/sc2-coordinator.service
[Unit]
Description=SC2 Python Data Coordinator
After=sc2-telemetry.service can-setup.service
Requires=sc2-telemetry.service

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/sunpi/sc2-driver-io/services/coordinator.py
Restart=always
RestartSec=3
User=sunpi
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

---

## 9. Neural Network Integration Point (Next Sprint)

### Interface Specification for Race Strategy Team

```python
# neural_network/interface.py

from dataclasses import dataclass
from typing import List, Callable
from collections import deque
import threading
import time

@dataclass
class NNInput:
    """Data packet for neural network inference"""
    timestamp: float
    speed: float
    soc: float
    pack_current: float
    pack_voltage: float
    motor_temp: float
    solar_power: float
    # Add more fields as needed by NN model
    
@dataclass  
class NNOutput:
    """Neural network decision output"""
    target_speed: float
    confidence: float
    reasoning_code: int  # Enum for UI display
    
class NNDataBuffer:
    """
    Accumulates CAN data for periodic NN inference.
    
    Usage by Race Strategy team:
        buffer = NNDataBuffer(window_minutes=5, sample_hz=1)
        buffer.set_inference_callback(my_nn_model.infer)
        buffer.start()
        
        # Buffer automatically calls inference every `window_minutes`
        # and publishes results to CAN via callback
    """
    
    def __init__(
        self,
        window_minutes: int = 5,
        sample_hz: float = 1.0,
        output_callback: Callable[[NNOutput], None] = None
    ):
        self.window_minutes = window_minutes
        self.sample_hz = sample_hz
        self.output_callback = output_callback
        
        max_samples = int(window_minutes * 60 * sample_hz)
        self.buffer: deque[NNInput] = deque(maxlen=max_samples)
        
        self._inference_fn: Callable[[List[NNInput]], NNOutput] = None
        self._running = False
        
    def set_inference_callback(self, fn: Callable[[List[NNInput]], NNOutput]) -> None:
        """Set the neural network inference function"""
        self._inference_fn = fn
        
    def add_sample(self, sample: NNInput) -> None:
        """Called by coordinator to add new data point"""
        self.buffer.append(sample)
        
    def start(self) -> None:
        """Start periodic inference"""
        self._running = True
        self._thread = threading.Thread(target=self._inference_loop, daemon=True)
        self._thread.start()
        
    def _inference_loop(self) -> None:
        while self._running:
            time.sleep(self.window_minutes * 60)
            
            if len(self.buffer) < 10:  # Minimum samples required
                continue
                
            if self._inference_fn:
                try:
                    result = self._inference_fn(list(self.buffer))
                    if self.output_callback:
                        self.output_callback(result)
                except Exception as e:
                    # Log error, continue operation
                    pass
```

### CAN Message IDs Reserved for NN

Add to `sc1-data-format/format.json`:

```json
{
  "nn_target_speed": [4, "float", "mph", 0, 100, "Neural Network;Strategy", "0x500", 0],
  "nn_confidence": [4, "float", "%", 0, 100, "Neural Network;Strategy", "0x500", 4],
  "nn_reasoning_code": [1, "uint8", "", 0, 255, "Neural Network;Strategy", "0x501", 0],
  "nn_last_inference_time": [4, "uint32", "s", 0, 4294967295, "Neural Network;Status", "0x501", 1]
}
```

---

## 10. Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Qt removal incomplete** | High | Critical | Audit all `.cpp` files for Qt includes; test build without Qt |
| **CAN bus reliability** | Medium | High | Implement watchdog timer; auto-reconnect on bus errors |
| **USB drive failure mid-race** | Medium | Medium | Buffer to RAM if USB fails; alert via UI and telemetry |
| **Python GIL blocks CAN** | Low | High | Keep CAN reader thread minimal; profile with `py-spy` |
| **LTE/Radio interference** | Medium | High | Stagger transmissions; monitor temperatures; separate USB hubs |
| **Lap counter GPS drift** | Medium | Medium | Already mitigated by tolerance in algorithm |
| **UI crashes frequently** | Low | Low | Process isolation + auto-restart via systemd |
| **8-week timeline slip** | Medium | High | Prioritize core functionality; defer UI polish |

---

## 11. Implementation Priority

### Week 1-2: Foundation
1. ✅ Remove Qt from `Serial.cpp` (use serialib)
2. ✅ Remove Qt from `backendProcesses.cpp/h`
3. ✅ Delete `dataFetcher.cpp`, create `can_bridge.cpp`
4. ✅ Update `CMakeLists.txt` to remove Qt
5. ✅ Create `can_bus/can_reader.py` with single-reader architecture
6. ✅ Verify CAN communication end-to-end

### Week 3-4: Data Flow
1. ✅ Implement Unix socket bridge (Python → C++)
2. ✅ Implement shared memory (Python → UI)
3. ✅ Integrate `lap_counter/` with coordinator
4. ✅ Implement CSV buffered logging
6. Test complete pipeline: CAN → CSV/Lap/Telemetry/UI (ready for testing - all components integrated)

### Week 5-6: Integration
1. Systemd service files and startup sequence
2. Error handling and recovery for all components
3. Performance profiling and optimization
4. Hardware testing on Raspberry Pi 4

### Week 7-8: Validation
1. End-to-end system testing
2. Failure mode testing (USB fail, CAN fail, crash recovery)
3. Documentation for next team
4. Neural network interface specification finalization

---

## 12. Final Recommendations Summary

| Area | Current State | Recommendation |
|------|---------------|----------------|
| **Qt Dependencies** | Still present in critical files | **Remove immediately** - blocks everything |
| **Main Entry Point** | Dual (C++ and Python) | Python coordinator, C++ telemetry-only |
| **CAN Reading** | Not integrated | Single Python reader with fan-out |
| **Python↔C++ IPC** | JSON files | Unix domain socket |
| **UI IPC** | JSON files | Shared memory for <1ms latency |
| **Lap Counter** | Python | **Keep in Python** - adequate performance |
| **Process Model** | Single process | 3 separate processes with crash isolation |
| **Textual UI** | Good foundation | Isolate in separate process, auto-restart |

### The Brutal Truth

Your EVOLUTION_PLAN.md says Qt is removed, but **it's not**. [Serial.cpp](backend/telemetrylib/Serial.cpp), [dataUnpacker.cpp](DataProcessor/dataUnpacker.cpp), and [dataFetcher.cpp](backend/dataFetcher.cpp) all still depend heavily on Qt. This is your **#1 blocker**.

The good news: your core architecture (DTI pattern, lap counter algorithm, CAN utilities) is solid. The integration patterns I've outlined above will work well for your use case.

**Start with Qt removal this week. Everything else depends on it.**

---

*Document generated: January 8, 2026*  
*Review requested by: Project Lead*  
*For: SC2 Driver IO 8-Week Sprint*
