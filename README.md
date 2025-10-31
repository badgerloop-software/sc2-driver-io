# SC2 Driver IO System

## Multi-Threaded Data Processing Coordinator

The SC2 Driver IO system is a high-performance, multi-threaded coordinator for real-time CAN message processing, GPS integration, lap counting, and parallel data transmission for Solar Car 2 race operations.

## 🏗️ Architecture Overview

```
CAN RX → GPS → Lap Counter → Modify Array → [LTE|Radio|CAN TX|CSV|NN Buffer|Dashboard]
```

- **8 parallel threads** for 3 Hz CAN message processing
- **<50ms critical path** with 6.6x safety margin
- **Live dashboard** with network monitoring and log viewer
- **Race-ready deployment** via systemd services

## 📊 Dashboard Interface

**Textual Terminal GUI** ⭐ (Primary Interface)
- Lightweight terminal-based interface
- Minimal resource usage (~10-15MB RAM, <1% CPU)
- **Network status monitoring** (LTE signal bars + carrier, WiFi status)
- **Live log viewer** with color-coded messages (ERROR/WARNING/INFO/DEBUG)
- **Real-time telemetry** (speed, battery, lap counter, system health)
- Located in `textual_frontend/` directory
- Works on HDMI display or over SSH

## 🌐 Network Monitoring Features ✨ (NEW)

### LTE Signal Monitoring
- **Signal strength**: Visual bars (📶 ▂▄▆█) based on RSSI
- **Carrier name**: Displays network operator (Verizon, AT&T, T-Mobile, etc.)
- **Connection status**: Real-time connectivity monitoring
- **AT command integration**: Uses EG25-G module commands (AT+CSQ, AT+COPS)

### WiFi Status Display  
- **Signal strength**: Visual bars (📡 ▂▄▆_) based on dBm
- **Network name**: Shows connected SSID or "Not Connected"
- **Connection management**: Keyboard-controlled network selection
- **Linux integration**: Uses nmcli commands for network discovery

### Performance Impact
- **<0.02% CPU overhead** for network monitoring
- **Updates every 10 seconds** (configurable)
- **Zero impact** on critical CAN processing path

## 🚀 Quick Start

### Development (Windows)
```powershell
# Terminal 1 - Start coordinator
python main.py

# Terminal 2 - Start dashboard  
cd textual_frontend
python textual_dashboard.py
```

### Production (Raspberry Pi)
```bash
# Auto-launch everything
sudo systemctl start sc2-driver-io.service textual-dashboard.service

# Or use launch script
./start_sc2_system.sh
```

## 📚 Documentation

Complete documentation available in `docs/` folder:

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Technical architecture and data flow
- **[WORKFLOW_SUMMARY.md](docs/WORKFLOW_SUMMARY.md)** - User-friendly workflow explanation  
- **[PI_DEPLOYMENT.md](docs/PI_DEPLOYMENT.md)** - Raspberry Pi deployment guide
- **[DASHBOARD_INTEGRATION.md](docs/DASHBOARD_INTEGRATION.md)** - Dashboard setup and troubleshooting
- **[DASHBOARD_DEMO.md](docs/DASHBOARD_DEMO.md)** - Visual demo of live log viewer

## 🔧 Libraries/Frameworks

- **[Textual](https://github.com/Textualize/textual)** - Terminal GUI framework (primary interface)
- **[RapidJSON](https://rapidjson.org/)** - JSON parsing library
- **Python Threading** - Multi-threaded coordination
- **SocketCAN** - Linux CAN bus interface

### Cloning the Repository and Data Format Submodule

0. If you don't already have an SSH key, [generate a new SSH key](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent) (only the steps under "Generating a new SSH key" are required) and [add it to your GitHub account](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account).
1. Clone this repository using SSH
2. Initialize the data format submodule: `git submodule update --init`

### Running the System

#### Development Mode (Skeleton Testing)
```bash
# Start main coordinator (logs to console + file)
python main.py

# In separate terminal - start dashboard
cd textual_frontend  
python textual_dashboard.py
```

#### Production Mode (Raspberry Pi)
```bash
# Option 1: Systemd services (automatic startup)
sudo systemctl start sc2-driver-io.service textual-dashboard.service

# Option 2: Launch script  
./start_sc2_system.sh

# Option 3: Manual launch
python main.py &
cd textual_frontend && python textual_dashboard.py
```
### Contributing to the System

1. Clone the repository using SSH
2. Initialize submodules: `git submodule update --init` 
3. Update submodules: `git submodule update --remote`
4. Create a feature branch: `git checkout -b feature/your-feature-name`
5. Test your changes:
   ```bash
   # Test coordinator
   python main.py
   
   # Test dashboard in separate terminal
   cd textual_frontend && python textual_dashboard.py
   ```
6. Commit and push changes
7. Open a pull request for code review

### System Architecture

**Multi-threaded Pipeline:**
- **Thread 0**: CAN RX + GPS + Lap Counter (critical path, <50ms)  
- **Thread 1**: LTE transmission (cloud SQL upload)
- **Thread 2**: Radio transmission (chase car UDP)
- **Thread 3**: CAN TX (lap data broadcast)
- **Thread 4**: CSV logging (batched writes)
- **Thread 5**: Neural network buffer (future ML inference)
- **Thread 6**: Dashboard updates (JSON file writing)
- **Thread 7**: System management + network monitoring

**Performance Targets:**
- **3 Hz message rate** (333ms period)
- **<50ms critical path** processing
- **6.6x safety margin** for real-time operation
- **Zero queue backlog** under normal operation

## 🔗 Integration Points

### External Modules (To Be Developed)
- **can_snooper/** - CAN bus interface (SocketCAN)
- **lap_counter/** - GPS-based lap counting algorithm  
- **data_logger/** - CSV batch writing to USB drive
- **lte_modem/** - EG25-G GPS and cellular interface
- **telemetry/** - Existing C++ backend integration

### Hardware Interfaces
- **CAN Bus**: Waveshare RS485 CAN HAT
- **GPS**: EG25-G LTE modem GNSS (AT+QGPSLOC)
- **LTE**: EG25-G Mini PCIe module (150 Mbps)
- **Radio**: RFD900A (250 Kbps, 902-928 MHz)
- **Display**: 7" HDMI touchscreen for dashboard
- **Storage**: USB drive for CSV data logging

## 🏁 Race Day Deployment

### Pi Auto-Launch Configuration
```bash
# Install systemd services
sudo systemctl enable sc2-driver-io.service textual-dashboard.service

# Boot sequence
Pi Boot → CAN Interface → Main Coordinator → Dashboard → Live Monitoring
```

### Emergency Diagnosis
- **HDMI Display**: Dashboard shows all system activity
- **SSH Access**: Remote troubleshooting from chase car  
- **Live Logs**: Color-coded ERROR/WARNING/INFO messages
- **System Health**: Thread status, queue depths, message rates

### Performance Monitoring
- **Message Rate**: Target 3.0 Hz (monitor via dashboard)
- **Thread Health**: All 8 threads must stay alive
- **Queue Depths**: Alert if >80% full
- **Network Status**: LTE/WiFi signal strength monitoring

## 📁 Project Structure

### Root Directory
- **main.py**: Python coordinator for multi-threaded system orchestration
- **config.json**: JSON configuration settings
- **CMakeLists.txt**: Build configuration for C++ components (legacy)
- **Config.cpp/h**: Configuration management (legacy C++ components)

### docs/ ✨ (NEW)
Complete documentation for the SC2 Driver IO system:
- **ARCHITECTURE.md**: Technical architecture and data flow diagrams
- **WORKFLOW_SUMMARY.md**: User-friendly workflow explanation
- **PI_DEPLOYMENT.md**: Raspberry Pi deployment guide with systemd services
- **DASHBOARD_INTEGRATION.md**: Dashboard setup and troubleshooting
- **DASHBOARD_DEMO.md**: Visual demo of live log viewer and network monitoring

### textual_frontend/ ⭐ (Primary Interface)
**Lightweight terminal-based dashboard with network monitoring:**
- **textual_dashboard.py**: Main dashboard application with live log viewer
- **dashboard.css**: Styling for terminal interface layout
- **setup_autolaunch.sh**: Pi integration script for race deployment

### 3rdparty/
Third-party libraries:
- **rapidjson/**: Header-only JSON parsing library for C++
- **serial/**: Serial communication library (serialib) for GPS devices

### backend/ (Legacy C++ Components)
Backend data processing and communication:
- **backendProcesses.cpp/h**: Backend process management
- **dataFetcher.cpp/h**: Network data fetching (TCP server integration)
- **telemetrylib/**: Telemetry operations (TCP, UDP, SQL, DTI handling)
- **file_sync/**: File synchronization scripts

### DataProcessor/ (Legacy)
Data processing and unpacking:
- **dataUnpacker.cpp/h**: Binary data unpacking for telemetry properties

### ethernet_sim/
Ethernet communication simulation:
- **main.py**: Ethernet telemetry simulation script
- **gps_dataset/**: Sample GPS data files (CSV, GPX, JSON)

### gps/ (Legacy)
GPS functionality:
- **gps.cpp/h**: GPS device interface via serial communication

### sc1-data-format/ (Submodule)
Data format definitions for telemetry packets (empty until submodule initialized)

### UI/ (Legacy Qt Components - Deprecated)
**Note: Qt GUI components have been replaced by Textual terminal interface**
- **Items/**: QML UI components (Dashboard, Speed, Batteries, etc.)
- **Images/**: Image assets for Qt dashboard
- **fonts/**: Font files (Work Sans) for Qt interface

## 🔄 Migration from Qt to Textual

The project has transitioned from Qt-based GUI to a lightweight Textual terminal interface:

**Advantages of New Architecture:**
- **Performance**: 90% reduction in resource usage (10-15MB vs 50-100MB)
- **Deployment**: No graphics dependencies, works over SSH
- **Race Operations**: HDMI diagnostic display for troubleshooting
- **Real-time Monitoring**: Live log viewer with network status
- **Simplicity**: Single Python file vs complex QML/C++ integration

**Migration Status:**
- ✅ Terminal dashboard with telemetry display
- ✅ Network monitoring (LTE signal, WiFi status)  
- ✅ Live log viewer with color-coded messages
- ✅ System health monitoring and diagnostics
- ✅ Pi deployment via systemd services
- 🔄 External module integration (CAN, GPS, lap counter)
- 📋 Qt components maintained for reference only
