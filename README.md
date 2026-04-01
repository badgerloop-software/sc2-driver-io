# SC2 Driver IO Program

**Solar Car 2 Real-Time Telemetry and Control System**

A headless driver IO system for Solar Car 2, featuring CAN bus communication, real-time telemetry transmission, GPS-based lap counting, and an optional lightweight terminal dashboard.

> **🔐 Security Note**: Before pushing to a public repository, see [docs/SECURITY.md](docs/SECURITY.md) for critical information about protecting your Convex deployment URLs and other sensitive configuration.

---

## Work in Progress

This project is actively being developed. The architecture has been restructured with a clean Python/C++ hybrid design.

**Current Status:**
- ✅ Qt removal complete
- ✅ CAN bus integration complete
- ✅ Python coordinator with fan-out architecture
- ✅ GPS lap counter integrated
- 🔄 SystemD service setup (Week 5-6)
- 🔄 End-to-end testing

See [`docs/ARCHITECTURE_REVIEW.md`](docs/ARCHITECTURE_REVIEW.md) for detailed architecture information.

---

## System Overview

### Architecture

```
CAN Bus → Python Coordinator → ┬→ CSV Logger (USB)
                                ├→ Lap Counter (GPS)
                                ├→ C++ Telemetry (Radio/LTE)
                                └→ Textual Dashboard (Terminal UI)
```

### Key Components

- **CAN Bus Reader** (`can_bus/`) - Single-reader architecture distributing to multiple consumers
- **Telemetry System** (`telemetry/`) - C++ transmission over RFD900A radio and EG25-G LTE
- **Lap Counter** (`lap_counter/`) - GPS-based section and lap timing
- **Terminal Dashboard** (`textual_frontend/`) - Lightweight Terminal-based UI
- **Data Logger** (`can_bus/csv_logger.py`) - Buffered CSV writing to USB drive

---

## Hardware Requirements

- **Raspberry Pi 4** (or newer)
- **Waveshare RS485 CAN HAT** for CAN bus communication
- **EG25-G Mini PCIe LTE Module** for cloud telemetry and GNSS
- **RFD900A Radio Module** for chase car communication
- **USB Flash Drive** for data logging

---

## Quick Start

### 1. Clone Repository

```bash
# Clone with SSH (recommended)
git clone git@github.com:badgerloop-software/sc2-driver-io.git
cd sc2-driver-io

# Initialize submodules
git submodule update --init --recursive
```

### 2. Install Dependencies

#### On Raspberry Pi / Linux:

```bash
# System packages
sudo apt update
sudo apt install -y build-essential cmake python3 python3-pip git libcurl4-openssl-dev

# Python packages
pip3 install -r textual_frontend/textual_requirements.txt
pip3 install python-can

# CAN bus tools
sudo apt install -y can-utils
```

#### On macOS (development):

```bash
# Install Homebrew if needed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install cmake python3 curl

# Python packages
pip3 install -r textual_frontend/textual_requirements.txt
pip3 install python-can
```


### 4. Build C++ Components

```bash
mkdir -p build
cd build
cmake ..
make
cd ..
```

### 5. Configure CAN Interface (Linux only)

```bash
# Set up CAN interface
sudo ip link set can0 type can bitrate 500000
sudo ip link set can0 up

# Verify CAN interface
ip link show can0
```

### 5. Run the System

#### Option A: Full System (Production)

```bash
# Terminal 1: C++ Telemetry
sudo ./build/sc2-driver-io

# Terminal 2: Python Coordinator
python3 services/coordinator.py

# Terminal 3: Dashboard (optional)
python3 textual_frontend/textual_dashboard.py
```

#### Option B: Dashboard Only (Development)

```bash
# Run standalone dashboard with simulated data
python3 textual_frontend/dashboard_launcher.py
```

#### Option C: Systemd Services (Raspberry Pi)

```bash
# Install services
sudo cp services/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable and start
sudo systemctl enable sc2-telemetry sc2-coordinator sc2-dashboard
sudo systemctl start sc2-telemetry sc2-coordinator sc2-dashboard

# Check status
sudo systemctl status sc2-*
```

---

## Development

### Project Structure

```
sc2-driver-io/
├── can_bus/              # CAN communication (Python)
├── telemetry/            # Radio/LTE transmission (C++)
├── data_processor/       # Data validation (C++)
├── lap_counter/          # GPS-based lap counting (Python)
├── core/ipc/             # Inter-process communication
├── services/             # System coordination
├── textual_frontend/     # Terminal dashboard UI
├── neural_network/       # AI integration (next sprint)
└── docs/                 # Architecture documentation
```

### Key Files

- **`services/coordinator.py`** - Main Python orchestrator
- **`main.cpp`** - C++ telemetry entry point
- **`can_bus/can_reader.py`** - Single CAN reader with fan-out
- **`core/ipc/shared_data.py`** - Shared memory for dashboard
- **`core/ipc/telemetry_bridge.py`** - Unix socket to C++

### Testing

```bash
# Test CAN reader (requires CAN interface)
python3 can_bus/can_reader.py

# Test shared memory IPC
python3 core/ipc/shared_data.py

# Test telemetry bridge
python3 core/ipc/telemetry_bridge.py

# Test neural network interface
python3 neural_network/interface.py
```

### Contributing

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make your changes
3. Update submodules if needed: `git submodule update --remote`
4. Test your changes
5. Commit with descriptive messages
6. Push and open a pull request

---

## Raspberry Pi Deployment

### Hardware Setup

1. **Install Raspberry Pi OS Lite** (no desktop environment)
2. **Configure CAN interface** in `/etc/network/interfaces`:
   ```
   auto can0
   iface can0 inet manual
       pre-up /sbin/ip link set can0 type can bitrate 500000
       up /sbin/ip link set can0 up
   ```
3. **Mount USB drive** for data logging (e.g., `/mnt/usb`)
4. **Configure serial ports** for RFD900A and EG25-G

### Production Deployment

```bash
# Build on Pi
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j4
cd ..

# Install systemd services
sudo cp services/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sc2-telemetry sc2-coordinator

# Optional: Enable dashboard
sudo systemctl enable sc2-dashboard

# Start services
sudo systemctl start sc2-telemetry
sudo systemctl start sc2-coordinator
sudo systemctl start sc2-dashboard
```

### Monitoring

```bash
# Check service status
sudo systemctl status sc2-*

# View logs
sudo journalctl -u sc2-coordinator -f
sudo journalctl -u sc2-telemetry -f

# Check CAN bus
candump can0
```

---

## Configuration

Edit `config.json` for system settings:

```json
{
  "udp_chasecar_ip": "192.168.1.100",
  "udp_chasecar_port": 8888,
  "EthernetPort": 9999,
  "csv_log_path": "/mnt/usb/logs"
}
```

---

## Troubleshooting

### CAN Bus Not Working

```bash
# Check interface status
ip link show can0

# Restart interface
sudo ip link set can0 down
sudo ip link set can0 up type can bitrate 500000

# Monitor for errors
dmesg | grep -i can
```

### Telemetry Not Transmitting

```bash
# Check serial ports
ls -la /dev/ttyUSB* /dev/ttyS*

# Test RFD900A
sudo screen /dev/ttyS0 115200

# Monitor LTE module
sudo minicom -D /dev/ttyUSB2
```

### Dashboard Not Updating

```bash
# Check shared memory
ls -la /tmp/sc2_telemetry_shm

# Test shared memory
python3 core/ipc/shared_data.py

# Restart dashboard
sudo systemctl restart sc2-dashboard
```

---

## Documentation

- **[Architecture Review](docs/ARCHITECTURE_REVIEW.md)** - Comprehensive system design
- **[Evolution Plan](docs/EVOLUTION_PLAN.md)** - Migration strategy and roadmap
- **[Restructure Summary](docs/RESTRUCTURE_SUMMARY.md)** - Recent changes and status
- **[Neural Network Interface](neural_network/README.md)** - AI integration spec

---

## Libraries and Frameworks

- **[python-can](https://python-can.readthedocs.io/)** - CAN bus communication
- **[Textual](https://github.com/Textualize/textual)** - Terminal UI framework
- **[RapidJSON](https://rapidjson.org/)** - Fast JSON parsing (C++)
- **[serialib](3rdparty/serial/)** - Cross-platform serial communication
- **[InfluxDB Line Protocol](https://docs.influxdata.com/influxdb/v2/api/#operation/PostWrite)** - Cloud writes from `cpp/` (see below)

---

## InfluxDB cloud telemetry (`cpp/`)

The C++ upload path from [badgerloop-software/sc2-telemetry-tester](https://github.com/badgerloop-software/sc2-telemetry-tester) branch [`tester--cpp`](https://github.com/badgerloop-software/sc2-telemetry-tester/tree/tester--cpp) is merged with **full upstream history** so original authors keep credit. It targets **InfluxDB Cloud** (v2 write API / Line Protocol), not Supabase.

- **Build:** `cmake` / `make` from the repo root also builds `sc2_telemetry_tester` and `sc2_telemetry_tests` when `libcurl` development packages are installed (`libcurl4-openssl-dev` on Debian / Raspberry Pi OS).
- **Config:** copy `.env.example` to `.env` and set `INFLUX_URL`, `INFLUX_TOKEN`, `INFLUX_ORG`, and `INFLUX_BUCKET`. Do not commit `.env`.
- **CSV replay (bench / lab):** run `build/cpp/sc2_telemetry_tester` (paths documented in [cpp/README_CPP.md](cpp/README_CPP.md)).
- **Canonical signal schema:** submodule [sc-data-format](https://github.com/badgerloop-software/sc-data-format) (`sc-data-format/format.json`).

---

- **Optional systemd unit:** `services/systemd/sc2-influx-tester.service` runs `sc2_telemetry_tester` in stream mode (lab / replay). Copy `.env.example` to `.env`, install the unit, then `sudo systemctl enable --now sc2-influx-tester`. Replace with a live CAN→Influx path when the unpacker feeds `TelemetryRecord`.
