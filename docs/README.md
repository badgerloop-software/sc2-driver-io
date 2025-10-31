# SC2 Driver IO Documentation

This folder contains comprehensive documentation for the SC2 Driver IO system.

## 📋 Documentation Index

### Core Architecture
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Complete technical documentation with data flow diagrams, thread architecture, performance targets, and integration points

### Implementation Guide  
- **[WORKFLOW_SUMMARY.md](WORKFLOW_SUMMARY.md)** - User-friendly workflow explanation with step-by-step process breakdown and performance analysis

### Deployment & Operations
- **[PI_DEPLOYMENT.md](PI_DEPLOYMENT.md)** - Complete Pi deployment guide with systemd services, auto-launch scripts, and race day procedures ✨
- **[DASHBOARD_INTEGRATION.md](DASHBOARD_INTEGRATION.md)** - Dashboard setup guide with JSON file formats and HDMI diagnostic procedures

### User Interface
- **[DASHBOARD_DEMO.md](DASHBOARD_DEMO.md)** - Visual demonstration of the live log viewer and complete dashboard layout

## 🏁 Quick Start

### For Race Operations:
1. Read **PI_DEPLOYMENT.md** for automatic startup configuration
2. Use **DASHBOARD_INTEGRATION.md** for HDMI diagnostic setup
3. Reference **DASHBOARD_DEMO.md** for troubleshooting guidance

### For Development:
1. Start with **WORKFLOW_SUMMARY.md** to understand the data pipeline
2. Review **ARCHITECTURE.md** for technical implementation details
3. Use **DASHBOARD_DEMO.md** to see what the live system looks like

## 🎯 Key Features Documented

- ✅ **8-thread architecture** for 3 Hz CAN message processing
- ✅ **Live dashboard** with log viewer, telemetry display, and system health
- ✅ **Pi auto-launch** via systemd services for race deployment
- ✅ **HDMI diagnostics** for emergency troubleshooting
- ✅ **Complete visibility** into all driver-io software operations
- ✅ **Performance optimization** with <50ms critical path processing

## 📊 System Overview

```
CAN RX → GPS → Lap Counter → Modify Array → [LTE|Radio|CAN TX|CSV|NN Buffer|Dashboard]
```

The system processes CAN messages at 3 Hz, integrates GPS and lap counter data, then transmits to multiple destinations in parallel while providing real-time dashboard monitoring.

---

**All documentation is up-to-date as of October 30, 2025** 📅