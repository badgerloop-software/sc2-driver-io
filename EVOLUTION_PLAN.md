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
- **Configuration System** (`Config.cpp/h`)
  - JSON-based configuration management
- **Data Format Structure** (`sc1-data-format/` submodule)
  - Binary data format definitions
- **Backend Processes** (`backend/backendProcesses.cpp/h`)
  - Threading for data processing
  - File sync capabilities

### Existing Components to **REMOVE**
- **Qt Framework Dependencies**
  - QML UI components (`UI/` directory)
  - Qt application engine and GUI components
  - Qt-specific threading and context management
- **Ethernet Communication**
  - TCP server in `dataFetcher.cpp`
  - Ethernet simulation (`ethernet_sim/`)
  - TCP-based data reception

## New Architecture Plan

### 1. CAN Snooper Module
**Location**: `can_snooper/` (new directory)
**Language**: Python
**Purpose**: Comprehensive electrical test board interface

#### Components:
- **Main Application** (`can_snooper/main.py`)
  - Real-time CAN message display dashboard
  - CAN signal mocking interface
  - Live telemetry visualization
- **CAN Interface** (`can_snooper/can_interface.py`)
  - SocketCAN integration for Linux
  - Message parsing and filtering
  - Signal encoding/decoding
- **UI Components** (`can_snooper/ui/`)
  - Web-based interface (Flask/FastAPI + HTML/JS)
  - Real-time data streaming via WebSockets
  - Configuration panels for test scenarios
- **Dependencies**: `python-can`, `flask/fastapi`, `websockets`

### 2. Lap Counter System
**Location**: `lap_counter.py` (root level)
**Language**: Python
**Purpose**: Track lap completion using GPS coordinates

#### Implementation:
```python
class LapCounter:
    def __init__(self, track_boundaries: List[Tuple[float, float]]):
        # Load hardcoded track coordinate data
        
    def update_position(self, x: float, y: float) -> Optional[int]:
        # Process live GPS coordinates
        # Return lap number if lap completed
        
    def get_current_lap(self) -> int:
        # Return current lap count
```

### 3. CSV Data Logger
**Location**: `data_logger.py` (root level)
**Language**: Python
**Purpose**: Log all CAN data to CSV files on USB drive

#### Features:
- Real-time CSV writing to mounted USB drive
- Data buffering for performance
- File rotation based on time/size
- Integration with existing data format

### 4. Neural Network Interface
**Location**: `neural_network/` (new directory)
**Language**: Python
**Purpose**: AI-driven decision making and CAN publishing

#### Components:
- **Model Interface** (`neural_network/model_interface.py`)
  - TensorFlow/PyTorch model loading
  - Input preprocessing from CAN data
  - Output postprocessing for CAN publishing
- **CAN Publisher** (`neural_network/can_publisher.py`)
  - Publish AI decisions back to CAN bus
  - Message formatting and timing control

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
1. **Add CAN Support to C++ Backend**
   - Integrate SocketCAN for Linux CAN communication
   - Create CAN message parser compatible with existing data format
   - Replace ethernet TCP server with CAN message reception

2. **Develop CAN Snooper**
   - Create Python-based CAN monitoring tool
   - Implement web UI for real-time display
   - Add CAN message mocking capabilities

### Phase 3: Python Integration
1. **CSV Logger Implementation**
   - Create Python service for data logging
   - Integrate with USB drive mounting
   - Implement data buffering and file management

2. **Lap Counter Development**
   - Implement GPS-based lap detection algorithm
   - Create track boundary configuration system
   - Test with existing GPS data

### Phase 4: AI Integration
1. **Neural Network Interface**
   - Design model input/output specifications
   - Create Python-C++ data bridge
   - Implement CAN message publishing for AI decisions

2. **System Integration**
   - Connect all components through shared data bus
   - Implement proper error handling and recovery
   - Add comprehensive logging and monitoring

## Technical Considerations

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
   - Need to debug LTE vs radio transmission interference
   - Consider implementing priority-based transmission queuing

3. **Error Handling**
   - Add comprehensive error handling for CAN communication failures
   - Implement graceful degradation when neural network is unavailable
   - Create robust USB drive detection and failure recovery

## Implementation Timeline

### Week 1-2: Foundation
- Remove Qt dependencies
- Modernize C++ backend
- Set up CAN infrastructure

### Week 3-4: Core Features
- Implement CAN snooper basic functionality
- Create CSV data logger
- Develop lap counter algorithm

### Week 5-6: Integration
- Connect Python components to C++ backend
- Implement neural network interface
- System testing and debugging

### Week 7-8: Polish & Optimization
- Performance optimization
- Error handling improvements
- Documentation and deployment preparation

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
- `CMakeLists.txt` (remove Qt, add CAN libraries)
- `Config.cpp/h` (remove Qt JSON dependencies)

### Add:
- `can_snooper/` directory with Python application
- `lap_counter.py`
- `data_logger.py`
- `neural_network/` directory
- New `main.cpp` for headless operation
- CAN interface libraries and headers

## Risk Assessment

### High Risk:
- Telemetry transmission conflicts (LTE vs radio) - needs debugging
- Real-time performance with Python components
- CAN bus reliability and error handling

### Medium Risk:
- USB drive failure scenarios
- Neural network model integration complexity
- GPS accuracy for lap counting

### Low Risk:
- CSV data logging implementation
- Configuration system migration
- CAN snooper UI development

## Success Metrics

1. **Functional Requirements**:
   - Reliable CAN message capture and display
   - Accurate lap counting based on GPS
   - Continuous CSV data logging to USB
   - Neural network integration with CAN publishing

2. **Performance Requirements**:
   - Real-time CAN message processing (< 10ms latency)
   - Telemetry transmission success rate > 95%
   - GPS-based lap detection accuracy > 98%
   - System uptime > 99% during race conditions

3. **Quality Requirements**:
   - Comprehensive error handling and recovery
   - Clean separation between C++ and Python components
   - Maintainable and well-documented codebase
   - Proper testing coverage for critical components