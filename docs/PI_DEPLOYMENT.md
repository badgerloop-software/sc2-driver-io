# Pi Deployment Guide

## Overview

This guide covers deploying the SC2 Driver IO system on Raspberry Pi 4 with automatic startup and dashboard integration for race operations.

## Auto-Launch Strategies

### Option 1: Systemd Services (Recommended for Production)

Create two systemd services that start together automatically on boot:

#### Main Driver IO Service
Create `/etc/systemd/system/sc2-driver-io.service`:
```ini
[Unit]
Description=SC2 Driver IO System
After=network.target can-interface.service
Requires=can-interface.service

[Service]
Type=simple
User=sunpi
Group=sunpi
WorkingDirectory=/home/sunpi/sc2-driver-io
ExecStart=/home/sunpi/sc2-driver-io/venv/bin/python main.py
Restart=always
RestartSec=5
Environment=PYTHONPATH=/home/sunpi/sc2-driver-io

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=sc2-driver-io

# Performance
Nice=-10
IOSchedulingClass=1
IOSchedulingPriority=4

[Install]
WantedBy=multi-user.target
```

#### Dashboard Service
Create `/etc/systemd/system/textual-dashboard.service`:
```ini
[Unit]
Description=SC2 Textual Dashboard
After=sc2-driver-io.service
Requires=sc2-driver-io.service
Wants=graphical-session.target

[Service]
Type=simple
User=sunpi
Group=sunpi
WorkingDirectory=/home/sunpi/sc2-driver-io/textual_frontend
ExecStart=/home/sunpi/sc2-driver-io/venv/bin/python textual_dashboard.py
Restart=always
RestartSec=5
Environment=DISPLAY=:0
Environment=PYTHONPATH=/home/sunpi/sc2-driver-io

# TTY for display
StandardInput=tty-force
StandardOutput=tty
StandardError=tty
TTYPath=/dev/tty1

[Install]
WantedBy=graphical-session.target
```

#### CAN Interface Service
Create `/etc/systemd/system/can-interface.service`:
```ini
[Unit]
Description=CAN Bus Interface Setup
Before=sc2-driver-io.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/sbin/ip link set can0 up type can bitrate 500000
ExecStop=/sbin/ip link set can0 down
TimeoutStartSec=30

[Install]
WantedBy=multi-user.target
```

#### Enable Services
```bash
sudo systemctl daemon-reload
sudo systemctl enable can-interface.service
sudo systemctl enable sc2-driver-io.service
sudo systemctl enable textual-dashboard.service

# Start immediately (for testing)
sudo systemctl start can-interface.service
sudo systemctl start sc2-driver-io.service
sudo systemctl start textual-dashboard.service

# Check status
sudo systemctl status sc2-driver-io.service
sudo systemctl status textual-dashboard.service
```

### Option 2: Launch Script (Simpler for Development)

Create `/home/sunpi/start_sc2_system.sh`:
```bash
#!/bin/bash
set -e

# Setup CAN interface
sudo ip link set can0 up type can bitrate 500000

# Create log directory
mkdir -p /home/sunpi/sc2-driver-io/logs

cd /home/sunpi/sc2-driver-io

echo "Starting SC2 Driver IO System..."

# Start main.py in background
python main.py > logs/main.log 2>&1 &
MAIN_PID=$!

echo "Main coordinator started (PID: $MAIN_PID)"
sleep 2

# Start dashboard in foreground (takes over terminal/HDMI)
echo "Starting dashboard..."
cd textual_frontend
python textual_dashboard.py

# Kill main.py when dashboard exits
echo "Dashboard closed, stopping main coordinator..."
kill $MAIN_PID 2>/dev/null || true

echo "System stopped."
```

Make executable and test:
```bash
chmod +x /home/sunpi/start_sc2_system.sh
./start_sc2_system.sh
```

### Option 3: Weston Auto-Launch (Best for HDMI Display)

Configure Weston (Wayland compositor) to auto-launch the dashboard on the HDMI display while main.py runs as a background service.

#### Install Weston
```bash
sudo apt update
sudo apt install weston
```

#### Create Weston Configuration
Create `/home/sunpi/.config/weston.ini`:
```ini
[core]
backend=drm-backend.so
gbm-format=xrgb8888

[shell]
background-image=/home/sunpi/sc2-driver-io/UI/Images/main_telem.png
background-type=scale-crop
panel-position=none
locking=false

[output]
name=HDMI-A-1
mode=1024x600
transform=normal

[autolaunch]
path=/home/sunpi/sc2-driver-io/textual_frontend
args=python textual_dashboard.py
```

#### Auto-start Weston
Add to `/home/sunpi/.bashrc`:
```bash
# Auto-start Weston on HDMI login
if [ -z "$WAYLAND_DISPLAY" ] && [ "$XDG_VTNR" = "1" ]; then
    exec weston --log=/tmp/weston.log
fi
```

## Race Day Workflow

### Boot Sequence
1. **Pi boots** → systemd starts `can-interface.service`
2. **CAN bus ready** → systemd starts `sc2-driver-io.service`
3. **Data collection begins** → main.py starts processing CAN/GPS
4. **Dashboard launches** → textual_dashboard.py shows on HDMI
5. **Live monitoring** → Dashboard reads from `driver_io.log` and JSON files

### Operation States
- **RUNNING**: Green status, 3 Hz message rate, all threads alive
- **WARNING**: Yellow status, degraded performance, recoverable errors
- **ERROR**: Red status, system failure, requires intervention

### Emergency Diagnosis
If problems occur during race:
1. **Connect to HDMI display** (dashboard should be visible)
2. **Check diagnostics panel** at bottom of screen
3. **Review recent errors/warnings** for root cause
4. **SSH access** from chase car if needed:
   ```bash
   ssh sunpi@<pi-ip>
   sudo systemctl status sc2-driver-io.service
   sudo journalctl -u sc2-driver-io.service -f
   ```

## Development vs Production

### Windows Development
```powershell
# Terminal 1
python main.py

# Terminal 2
cd textual_frontend
python textual_dashboard.py
```

### Pi Production
```bash
# Automatic startup via systemd
sudo systemctl start sc2-driver-io.service
sudo systemctl start textual-dashboard.service

# Or single script
./start_sc2_system.sh
```

## Service Management

### Start/Stop Services
```bash
# Start system
sudo systemctl start sc2-driver-io.service textual-dashboard.service

# Stop system
sudo systemctl stop textual-dashboard.service sc2-driver-io.service

# Restart after code changes
sudo systemctl restart sc2-driver-io.service

# View logs
sudo journalctl -u sc2-driver-io.service -f
sudo journalctl -u textual-dashboard.service -f
```

### Update Deployment
```bash
# Pull latest code
cd /home/sunpi/sc2-driver-io
git pull origin main

# Restart services
sudo systemctl restart sc2-driver-io.service textual-dashboard.service

# Check status
sudo systemctl status sc2-driver-io.service
```

## Hardware Setup

### Required Hardware
- **Raspberry Pi 4** (4GB+ RAM recommended)
- **Waveshare RS485 CAN HAT** for CAN bus interface
- **EG25-G Mini PCIe Module** for LTE and GPS
- **7" HDMI Display** for dashboard (1024x600 recommended)
- **USB Drive** for CSV data logging
- **RFD900A Radio Module** for chase car communication

### CAN Bus Configuration
```bash
# Add to /etc/systemd/system/can-interface.service
sudo ip link set can0 up type can bitrate 500000

# Verify CAN interface
ip link show can0
cansend can0 123#DEADBEEF
```

### USB Auto-Mount
Create `/etc/systemd/system/usb-automount.service`:
```ini
[Unit]
Description=USB Drive Auto-mount
DefaultDependencies=false

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/bin/mkdir -p /media/usb0
ExecStart=/bin/mount -t vfat /dev/sda1 /media/usb0
ExecStop=/bin/umount /media/usb0

[Install]
WantedBy=multi-user.target
```

## Logging and Monitoring

### Log Files
- **System logs**: `sudo journalctl -u sc2-driver-io.service`
- **Application logs**: `/home/sunpi/sc2-driver-io/driver_io.log`
- **Dashboard logs**: `sudo journalctl -u textual-dashboard.service`
- **CSV data**: `/media/usb0/telemetry_YYYYMMDD_HHMMSS.csv`

### Performance Monitoring
```bash
# CPU/Memory usage
htop

# CAN bus traffic
candump can0

# System health
systemctl status sc2-driver-io.service textual-dashboard.service

# Queue depths and message rate
tail -f /home/sunpi/sc2-driver-io/driver_io.log | grep "Performance Stats"
```

## Troubleshooting

### Common Issues

#### CAN Interface Not Available
```bash
# Check hardware
lsmod | grep can
dmesg | grep can

# Restart CAN service
sudo systemctl restart can-interface.service
```

#### Dashboard Not Showing on HDMI
```bash
# Check display connection
cat /sys/class/drm/card*/status

# Check Weston
ps aux | grep weston

# Restart dashboard
sudo systemctl restart textual-dashboard.service
```

#### GPS Not Working
```bash
# Check EG25-G module
lsusb | grep Quectel
sudo minicom -D /dev/ttyUSB2

# Test AT commands
AT+QGPSLOC?
```

#### High CPU Usage
```bash
# Check thread performance
top -H -p $(pgrep python)

# Review message rate
grep "CAN processing took" /home/sunpi/sc2-driver-io/driver_io.log
```

### Emergency Recovery

#### Safe Mode Boot
1. Edit `/boot/cmdline.txt`
2. Add `systemd.unit=rescue.target`
3. Reboot and fix issues
4. Remove safe mode and reboot

#### Remote Recovery
```bash
# SSH from chase car
ssh sunpi@<pi-ip>

# Kill hung processes
sudo pkill -f "python main.py"
sudo pkill -f "textual_dashboard.py"

# Restart services
sudo systemctl restart sc2-driver-io.service textual-dashboard.service
```

## Security Considerations

### User Permissions
```bash
# Add sunpi to required groups
sudo usermod -a -G dialout,gpio,spi,i2c,can sunpi

# Set file permissions
sudo chown -R sunpi:sunpi /home/sunpi/sc2-driver-io
chmod +x /home/sunpi/start_sc2_system.sh
```

### Network Security
- **Disable SSH password authentication** (use keys only)
- **Configure firewall** to allow only required ports
- **Use VPN** for remote access during races

## Performance Optimization

### CPU Scheduling
```bash
# Set real-time priority for critical threads
sudo echo 'sunpi - rtprio 99' >> /etc/security/limits.conf

# Pin threads to specific cores (in main.py)
import os
os.sched_setaffinity(0, {0})  # Pin to core 0
```

### Memory Management
```bash
# Increase swap for safety
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Disk I/O
```bash
# Use faster USB 3.0 drive for CSV logging
# Mount with optimized flags
sudo mount -t vfat -o rw,uid=1000,gid=1000,umask=0022,sync /dev/sda1 /media/usb0
```

## Summary

The Pi deployment provides:
- ✅ **Automatic startup** via systemd services
- ✅ **HDMI diagnostics** for race day troubleshooting  
- ✅ **Robust error recovery** with service restarts
- ✅ **Performance monitoring** through logs and dashboard
- ✅ **Remote access** via SSH for emergency fixes
- ✅ **Hardware integration** with CAN, GPS, LTE, and USB logging

**Your Raspberry Pi is now race-ready with full diagnostic capabilities!** 🏁