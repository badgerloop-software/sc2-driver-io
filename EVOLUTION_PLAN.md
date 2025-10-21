# SC2 Driver IO Evolution Plan

## Current Architecture Analysis

### Existing Components to **PRESERVE**
- **Telemetry System** (`backend/telemetrylib/`)
  - SQL transmission for cloud data (LTE)
  - UDP transmission for chase car communication (radio)
  - DTI (Data Transmission Interface) architecture for modular communication
  - Data compression and caching mechanisms
- **GPS Module** (`gps/`)
  - Serial communication with GPS device
  - NMEA data parsing for location tracking
  - **Note**: May be superseded by EG25-G LTE module's integrated GNSS
- **Configuration System** (`Config.cpp/h`)
  - JSON-based configuration management
- **Data Format Structure** (`sc1-data-format/` submodule)
  - Binary data format definitions
- **Backend Processes** (`backend/backendProcesses.cpp/h`)
  - Threading for data processing
  - File sync capabilities via FastAPI server
  - HTTP-based telemetry file upload to VPS
- **File Sync System** (`backend/file_sync/`)
  - **file_sync_up**: Client that uploads telemetry files to server
  - **file_sync_server**: FastAPI server for receiving and managing telemetry files
  - **Current Issue**: Uses TCP/HTTP communication to VPS (Oracle Cloud suspension)

### Existing Components to **REMOVE**
- **Qt Framework Dependencies** *(Replaced with optional Textual terminal GUI)*
  - QML UI components (`UI/` directory) - **REMOVED** ✅
  - Qt application engine and GUI components - **MODERNIZED** ✅
  - Qt-specific threading and context management - **CONVERTED to std::thread** ✅
- **Ethernet Communication** *(Replaced with CAN bus)*
  - TCP server in `dataFetcher.cpp` [Need to look into this further]
  - Ethernet simulation (`ethernet_sim/`)
  - TCP-based data reception

## New Architecture Plan

### 1. CAN Snooper Module (EXISTING - Separate Repository)
**Location**: External repository to be integrated
**Language**: Python + React frontend
**Purpose**: Comprehensive electrical test board interface
**Hardware**: Waveshare RS485 CAN HAT

#### Existing Architecture:
- **WebSocket API** (`api/main.py`)
  - Real-time CAN data broadcasting via WebSocket (ws://localhost:8765)
  - Direct SocketCAN integration with `can0` interface
  - JSON message formatting for frontend consumption
- **CAN Utilities** (`can_utils/`)
  - `data_classes.py`: CAN message data structures
  - `read_can_messages.py`: Enhanced message parsing with signal decoding
  - `send_messages.py`: CAN message transmission utilities
- **React Frontend** (`frontend/`)
  - Real-time dashboard at http://localhost:5173
  - WebSocket client for live CAN data
  - Interactive message sending interface
- **Testing Infrastructure**
  - `mock_messages.py`: Simulated CAN data for development
  - Console utilities for debugging
- **Data Format Integration**: Uses `sc1-data-format` submodule for signal definitions

#### Integration Plan:
- Import CAN snooper as git submodule or copy into `can_snooper/` directory
- Extend existing WebSocket API to provide data feed for main driver IO system
- Add CAN message filtering specific to driver IO requirements

### 2. Lap Counter System
**Location**: `lap_counter.py` (root level) - **Currently in development by team member**
**Language**: Python
**Purpose**: Track lap completion and section timing using GPS coordinates

#### Current Implementation (In Development):
- Single method that takes car's current position (lat, lon) as input
- Returns lap/section data that needs CAN transmission capability

#### Recommended CAN-Compatible Output Format:
```python
# Option 1: Individual CAN signals (recommended for sc1-data-format integration)
def update_position(lat: float, lon: float) -> dict:
    return {
        'lap_count': int,           # [4, "uint32", "", 0, 9999, "Lap Counter", "0x400", 0]
        'current_section': int,     # [1, "uint8", "", 0, 255, "Lap Counter", "0x400", 4] 
        'section_time': float,      # [4, "float", "s", 0, 999.9, "Lap Counter", "0x401", 0]
        'lap_time': float,          # [4, "float", "s", 0, 9999.9, "Lap Counter", "0x401", 4]
        'position_valid': bool      # [1, "bool", "", 0, 1, "Lap Counter", "0x402", 0]
    }

# Option 2: Packed structure (more efficient but needs custom parsing)
from struct import pack
def update_position(lat: float, lon: float) -> bytes:
    # Pack into 16-byte CAN frame: lap_count(4) + section(1) + section_time(4) + lap_time(4) + flags(1) + reserved(2)
    return pack('<IIBfB', lap_count, current_section, section_time, lap_time, flags)
```

#### sc1-data-format Integration Required:
Add to `sc1-data-format/format.json`:
```json
{
  "lap_count": [4, "uint32", "", 0, 9999, "Lap Counter;Race Data"],
  "current_section": [1, "uint8", "", 0, 255, "Lap Counter;Race Data"],
  "section_time": [4, "float", "s", 0, 999.9, "Lap Counter;Race Timing"],
  "lap_time": [4, "float", "s", 0, 9999.9, "Lap Counter;Race Timing"],
  "position_valid": [1, "bool", "", 0, 1, "Lap Counter;GPS Status"]
}
```
**Note**: Current format.json uses 6-element arrays, needs investigation of 7th element purpose (CAN ID/offset)

#### Integration with Existing System:
- Output gets processed by C++ backend and included in telemetry stream
- Data transmitted via RFD900A radio (250 Kbps max, sufficient for lap data)
- CAN messages use dedicated IDs (0x400-0x402 range suggested)

### 3. CSV Data Logger
**Location**: `data_logger.py` (root level)
**Language**: Python
**Purpose**: Log all CAN data to CSV files on USB drive

#### Features:
- Real-time CSV writing to mounted USB drive
- Data buffering for performance
- File rotation based on time/size
- Integration with existing data format

### 4. Neural Network Interface (DEFERRED TO NEXT SPRINT)
**Location**: `neural_network/` (new directory) 
**Language**: Python + PyTorch
**Purpose**: AI-driven decision making and CAN publishing
**Status**: **OUT OF SCOPE** for current 8-week sprint

#### Collaboration with Race Strategy Team:
- **Training Data**: Simulink model representation of solar car for synthetic data generation
- **Framework**: PyTorch-based deep learning model
- **Integration Point**: Python interface for model inference on Raspberry Pi
- **Timeline**: Integration planned for next sprint after model training completion

#### Planned Interface (Future Sprint):
- **Model Interface** (`neural_network/model_interface.py`)
  - PyTorch model loading and inference
  - Input preprocessing from CAN data
  - Output postprocessing for CAN publishing
- **CAN Publisher** (`neural_network/can_publisher.py`)
  - Publish AI decisions back to CAN bus
  - Message formatting and timing control
  
#### Current Sprint Preparation:
- Design CAN message IDs for neural network outputs
- Create placeholder interface for future integration
- Document data format requirements for Race Strategy team

### 5. Textual Terminal Frontend (NEW - LIGHTWEIGHT GUI OPTION)
**Location**: `textual_frontend/` directory
**Language**: Python (Textual library)
**Purpose**: Lightweight terminal-based GUI replacement for Qt dashboard

#### Performance Benefits vs Qt:
- **70-90% RAM reduction** (50-100MB → 5-15MB)
- **80-90% CPU reduction** (5-15% → 0.5-2% baseline)
- **50-75% faster boot** (no desktop environment needed)
- **10-20% power savings** (no GPU rendering pipeline)

#### Architecture:
- **Terminal-based GUI** (`textual_dashboard.py`)
  - Real-time telemetry display (speed, battery, voltages, temperatures)
  - System monitoring (CPU, memory, temperature, power consumption)
  - Status indicators (lights, turn signals, hazards, parking brake)
  - Battery visualization with progress bars
- **Data Bridge** (`dashboard_launcher.py`)
  - JSON file interface with C++ backend
  - Named pipe support for low-latency data
  - Automatic reconnection and error handling
- **Auto-launch Configuration** (`setup_autolaunch.sh`)
  - Systemd service configuration
  - Console auto-login setup
  - Resource optimization (disabled unnecessary services)

#### Integration Options:
- **JSON File Interface**: C++ writes telemetry to `telemetry_data.json` (current implementation)
- **Named Pipe**: Higher performance with `/tmp/sc2_telemetry` pipe
- **Shared Memory**: Maximum performance for zero-copy data sharing

#### Deployment Advantages:
- **No Desktop Environment**: Direct console boot saves ~200MB RAM and significant CPU
- **SSH Compatible**: Can monitor dashboard remotely over network
- **Crash Resilient**: Automatic restart with systemd service management
- **Development Friendly**: Easy debugging and customization in Python

## Migration Strategy

### Phase 1: Infrastructure Preparation
1. **Remove Qt Dependencies**
   - Update CMakeLists.txt to remove Qt components
   - Create new main.cpp without QML engine
   - Preserve core C++ backend functionality

2. **Modernize Data Flow**
   - Replace Qt signals/slots with standard C++ callbacks
   - Convert QByteArray to std::vector<uint8_t>
   - Update threading to use std::thread instead of QThread

### Phase 2: CAN Integration
1. **Integrate Existing CAN Snooper**
   - Add CAN snooper repository as submodule or copy into project
   - Extend WebSocket API to feed data into main driver IO system
   - Configure CAN message filtering for driver IO specific signals
   - Test CAN communication with Waveshare RS485 CAN HAT on RPi4

2. **Replace Ethernet with CAN in C++ Backend**
   - Remove TCP server from `dataFetcher.cpp`
   - Add SocketCAN integration to receive CAN messages
   - Create CAN message parser compatible with existing data format
   - Update CMakeLists.txt to include CAN libraries

### Phase 3: Python Integration & Data Systems
1. **CSV Logger Implementation**
   - Create Python service for data logging
   - Integrate with USB drive mounting
   - Implement data buffering and file management

2. **Lap Counter Development**
   - Complete GPS-based section and lap detection algorithm
   - Create track section boundary configuration system
   - Design LapData structure output for integration with telemetry
   - Test with existing GPS data and validate section timing accuracy
   - **Performance Consideration**: Monitor for timing precision requirements that may necessitate C++ rewrite

### Phase 4: System Integration & Testing
1. **Component Integration**
   - Connect Python components to C++ backend via data bridges
   - Integrate lap counter and CSV logger with telemetry system
   - Test complete data flow from CAN → Processing → Telemetry

2. **Neural Network Interface Preparation**
   - Design placeholder interface for future Race Strategy team integration
   - Define CAN message specifications for AI model outputs
   - Document data format requirements and integration points

3. **System Validation**
   - End-to-end testing with real hardware
   - Performance optimization and error handling
   - Documentation and deployment preparation

## Technical Considerations

### Hardware Requirements
- **Raspberry Pi 4** (current target, potential upgrade to RPi5 or NVIDIA Jetson)
- **Waveshare RS485 CAN HAT** for CAN bus communication
- **USB Drive** for CSV data logging
- **EG25-G Mini PCIe LTE Module** for cloud data transmission and GPS
  - **LTE**: Category 4, up to 150Mbps down/50Mbps up (3GPP Release 11)
  - **Backward Compatibility**: EDGE, GSM/GPRS for remote area coverage
  - **GNSS**: Multi-constellation (GPS, GLONASS, BeiDou, Galileo, QZSS)
  - **Interface**: USB 2.0 high-speed with serial drivers
  - **Location Technology**: Qualcomm IZat Gen8C Lite positioning
  - **Thermal Management**: Software thermal mitigation with AT commands
  - **Form Factor**: Mini PCIe (51.0mm x 30.0mm x 4.9mm)
- **RFD900A Radio Module** for chase car telemetry
  - **Frequency**: 902-928 MHz ISM band
  - **Data Rate**: Up to 250 Kbps (sufficient for telemetry + lap data)
  - **Range**: 40km line-of-sight, 0.5-1km indoor
  - **Power**: Adjustable 0-30 dBm (up to 1W)
  - **Interface**: USB/UART with automatic switching
  - **Working Temperature**: -40°C to +85°C (suitable for vehicle environment)

### Language Assessment
**C++ Components (GOOD)**:
- Telemetry system architecture is well-designed and modular
- Backend processing is efficient for real-time operations
- GPS integration is robust
- Configuration management is clean

**Python Components (RECOMMENDED)**:
- CAN snooper benefits from Python's rapid development and rich libraries
- Data science tools (pandas, numpy) excellent for CSV handling
- Machine learning frameworks readily available
- Web UI development is straightforward

### Architecture Improvements Needed

1. **Data Flow Modernization**
   - Current Qt-centric architecture needs C++ modernization
   - Replace Qt containers with STL equivalents
   - Implement proper RAII and modern C++ practices

2. **Communication Protocol Issues**
   - Current telemetry system sends to both SQL and UDP but may have conflicts
   - **EG25-G LTE Module**: 150Mbps downlink provides excellent bandwidth for cloud telemetry
   - **RFD900A Radio Bandwidth**: 250 Kbps max should handle current telemetry + lap data easily
   - **LTE vs Radio interference**: Likely caused by USB interface conflicts or thermal management
   - **EG25-G Thermal Management**: Module has built-in thermal mitigation (AT+QTEMP, AT+QCFG commands)
   - Consider implementing priority-based transmission queuing
   - **GPS Source Consolidation**: EG25-G's integrated GNSS may replace separate GPS module

## Cloud Infrastructure Migration (DEFERRED TO NEXT SPRINT)

### Current Status: Oracle Cloud Issue Acknowledged
- **File sync server** currently hosted on Oracle Cloud free tier
- **Account suspension** due to inactivity during off-season
- **Decision**: Cloud migration research and implementation **deferred to next sprint**
- **Workaround**: Continue with localhost/local network testing for current sprint

### Next Sprint Scope (Cloud & Infrastructure):
- Comprehensive cloud provider evaluation and migration
- **FastAPI server** (`file_sync_server/main.py`) hosting solution
- **Mobile app backend** (~30 users) infrastructure planning
- Database architecture for telemetry analytics
- Cost optimization and scaling strategy

### Current Sprint Cloud-Related Tasks:
- **Document requirements** for cloud team handoff
- **Test file sync locally** to ensure compatibility
- **Design API contracts** for cloud integration
- **Prepare deployment configurations** for rapid migration

#### **1. Google Cloud Platform (RECOMMENDED)**
**Why**: Best free tier for your use case
- **Compute**: 0.25 vCPU, 1GB RAM VM (sufficient for FastAPI server)
- **Storage**: 5GB regional storage (US regions)
- **Network**: 1GB/month premium egress (plenty for telemetry files)
- **BigQuery**: 1TB querying/month + 10GB storage (great for telemetry analytics)
- **Cloud Run**: Serverless FastAPI hosting (scales to zero when idle)
- **Always free** (no expiration like Oracle)

**Migration Plan**:
```bash
# Deploy FastAPI server to Cloud Run
gcloud run deploy file-sync-server \
  --source=./backend/file_sync/file_sync_server \
  --platform=managed \
  --region=us-central1 \
  --allow-unauthenticated
```

#### **2. AWS (Alternative)**
**Why**: Most reliable, extensive free tier
- **EC2**: t3.micro instance (1 vCPU, 1GB RAM) - 750 hours/month
- **S3**: 5GB storage for telemetry files
- **Lambda**: 1M requests/month (perfect for file processing)
- **RDS**: 20GB database storage (for mobile app)
- **12 months free** then pay-as-you-go

#### **3. Cloudflare (Hybrid Approach)**
**Why**: Excellent for static hosting + edge functions
- **Pages**: Free static site hosting (mobile app frontend)
- **Workers**: 100k requests/day serverless functions
- **R2 Storage**: 10GB S3-compatible object storage
- **D1**: Serverless SQL database (perfect for mobile app)
- **Always free** + global CDN

### Database Hosting Strategy

#### **For Mobile App + Telemetry Analytics**:
1. **Google Cloud BigQuery** (recommended)
   - Perfect for telemetry data analytics
   - SQL interface familiar to team
   - 1TB queries/month free
   
2. **Cloudflare D1** (alternative)
   - Serverless SQLite at edge
   - Great for mobile app user data
   - Always free tier
   
3. **PlanetScale** (MySQL-compatible)
   - 10GB storage free
   - Excellent for mobile app backend
   - Easy scaling when club grows

### Implementation Recommendations

#### **Phase 1: Quick Migration (1-2 weeks)**
1. **Deploy to Google Cloud Run**:
   - Migrate `file_sync_server` to Cloud Run
   - Update `file_sync_up/config.py` with new URL
   - Test telemetry file upload/download

#### **Phase 2: Optimize Architecture (3-4 weeks)**
1. **Add BigQuery integration**:
   - Stream telemetry data directly to BigQuery
   - Create analytics dashboard for race data
   - Enable lap counter data analysis

2. **Mobile app backend**:
   - Deploy REST API for mobile app on Cloud Run
   - Use Cloudflare D1 or Google Cloud SQL for user data
   - Implement authentication for 30 club members

#### **Cost Optimization Strategies**
1. **Multi-cloud approach**:
   - Google Cloud: Primary compute + analytics
   - Cloudflare: CDN + static hosting + edge functions
   - AWS: Backup/secondary regions

2. **Resource scheduling**:
   - Use Cloud Scheduler to scale down during off-season
   - Implement cold start optimization for serverless functions

3. **Data lifecycle**:
   - Archive old telemetry data to cheap storage
   - Use compression for file uploads
   - Implement data retention policies

### Migration Timeline
- **Week 1**: Google Cloud setup + FastAPI migration
- **Week 2**: DNS cutover + testing with actual telemetry
- **Week 3**: Mobile app backend deployment
- **Week 4**: Analytics dashboard + BigQuery integration

### Error Handling & System Reliability
1. **CAN Communication**
   - Add comprehensive error handling for CAN bus failures
   - Implement graceful degradation when neural network is unavailable
   - Create robust USB drive detection and failure recovery

2. **Cloud Connectivity**
   - Implement offline telemetry buffering when cloud is unreachable
   - Add retry logic with exponential backoff
   - Monitor file sync health and alert on failures

## 8-Week Implementation Timeline (Current Sprint)

### **Sprint Goal**: Complete core driver IO functionality excluding neural network and cloud migration

### Week 1-2: Qt Removal & CAN Integration Foundation
- **Remove Qt dependencies** from C++ backend ✅
- **Modernize C++ architecture** (STL containers, std::thread, etc.) ✅
- **Deploy Textual terminal GUI** option for lightweight dashboard (alternative to Qt)
- **Integrate existing CAN snooper** repository as submodule
- **Set up Waveshare CAN HAT** communication and testing
- **Milestone**: Headless C++ application running with CAN communication + optional terminal GUI

### Week 3-4: Data Flow Replacement
- **Replace ethernet with CAN** in `dataFetcher.cpp`
- **Implement SocketCAN integration** for message reception
- **Create CSV data logger** Python service
- **Begin lap counter integration** with team member's GPS algorithm
- **Milestone**: CAN messages flowing from hardware through to telemetry system

### Week 5-6: System Integration & Validation
- **Complete lap counter integration** with CAN transmission
- **Connect Python components** (CSV logger, lap counter) to C++ backend
- **Test complete data pipeline** with real hardware
- **Performance optimization** and timing validation
- **Milestone**: Full system operational with all components integrated

### Week 7-8: Testing, Documentation & Handoff Preparation
- **End-to-end system testing** on Raspberry Pi 4
- **Error handling and recovery** implementation
- **Performance benchmarking** and optimization
- **Documentation** for next sprint handoffs
- **Prepare neural network interface specifications** for Race Strategy team
- **Document cloud requirements** for infrastructure team
- **Milestone**: Production-ready system with comprehensive documentation

### **Out of Scope (Next Sprint)**:
- ❌ Neural network model development and training
- ❌ Cloud provider research and migration
- ❌ Mobile app backend development  
- ❌ Database architecture design
- ❌ Advanced analytics and telemetry visualization

### **Sprint Deliverables**:
✅ Headless driver IO application (no Qt)
✅ CAN bus communication with existing snooper integration
✅ Real-time CSV data logging to USB drive
✅ GPS-based lap counter with CAN transmission
✅ Preserved telemetry transmission (LTE + radio)
✅ Integration interfaces ready for neural network team
✅ Requirements documentation for cloud migration team

## Files to Modify/Remove

### Remove:
- `main.cpp` (replace with non-Qt version)
- `UI/` directory (entire Qt UI)
- `ethernet_sim/` directory
- Qt-related entries in `CMakeLists.txt`
- `DataProcessor/dataUnpacker.h` Qt properties

### Modify:
- `backend/dataFetcher.cpp/h` (replace TCP with CAN)
- `backend/backendProcesses.cpp/h` (remove Qt dependencies)
- `backend/file_sync/file_sync_up/config.py` (update server URL for new cloud hosting)
- `CMakeLists.txt` (remove Qt, add CAN libraries)
- `Config.cpp/h` (remove Qt JSON dependencies)
- `sc1-data-format/format.json` (add lap counter signals)

### Add:
- CAN snooper integration (submodule or copy from existing repository)
- `lap_counter.py` with LapData structure support
- `data_logger.py`
- `neural_network/` directory (interface specifications only)
- New `main.cpp` for headless operation
- SocketCAN libraries and headers for CAN communication
- WebSocket integration for CAN snooper data feed

## Risk Assessment

### High Risk:
- Telemetry transmission conflicts (LTE vs radio) - needs debugging
- Real-time performance with Python components
- CAN bus reliability and error handling

### Medium Risk:
- USB drive failure scenarios  
- GPS accuracy for lap counting
- Integration timing with lap counter development

### Low Risk:
- CSV data logging implementation
- Configuration system migration
- CAN snooper integration (already proven working)

### **Deferred Risks** (Next Sprint):
- Neural network model complexity and inference latency
- Cloud provider selection and migration challenges
- Mobile app backend scaling and database design

## Success Metrics (8-Week Sprint)

1. **Functional Requirements**:
   - ✅ Reliable CAN message capture and display
   - ✅ Accurate lap counting based on GPS
   - ✅ Continuous CSV data logging to USB
   - 🔄 Neural network interface specifications (design only, implementation next sprint)

2. **Performance Requirements**:
   - Real-time CAN message processing (< 10ms latency)
   - Telemetry transmission success rate > 95%
   - GPS-based lap detection accuracy > 98%
   - System uptime > 99% during testing conditions

3. **Quality Requirements**:
   - Comprehensive error handling and recovery
   - Clean separation between C++ and Python components
   - Maintainable and well-documented codebase
   - **Handoff documentation** ready for neural network and cloud teams

4. **Sprint-Specific Goals**:
   - **Qt completely removed** from codebase
   - **CAN snooper successfully integrated** with existing telemetry system
   - **Race Strategy team requirements** documented for neural network integration
   - **Cloud migration requirements** documented for infrastructure team