#!/bin/bash
# SC2 Driver IO - Auto-launch setup script for Raspberry Pi
# Integrates with existing sunpi/Weston configuration

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}SC2 Driver IO - Terminal Dashboard Setup${NC}"
echo "========================================"
echo "Integrating with existing Raspberry Pi OS Lite + Weston setup"

# Get the project directory
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$(dirname "$PROJECT_DIR")"
echo "Project directory: $PROJECT_ROOT"

# Install Python dependencies for sunpi user
echo -e "\n${YELLOW}Installing Python dependencies for sunpi user...${NC}"
sudo -u sunpi pip3 install -r "$PROJECT_DIR/textual_requirements.txt"

# Create C++ backend service (runs as root for GPS access)
BACKEND_SERVICE="/etc/systemd/system/sc2-backend.service"
echo -e "\n${YELLOW}Creating C++ backend service (root for GPS access)...${NC}"

sudo tee "$BACKEND_SERVICE" > /dev/null <<EOF
[Unit]
Description=SC2 Driver IO Backend (Headless C++)
After=network.target
Wants=network.target
Before=sc2-coordinator.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=$PROJECT_ROOT
ExecStart=$PROJECT_ROOT/build/sc2-driver-io
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Create Python coordinator service (runs as sunpi user)
COORDINATOR_SERVICE="/etc/systemd/system/sc2-coordinator.service"
echo -e "\n${YELLOW}Creating Python coordinator service (sunpi user)...${NC}"

sudo tee "$COORDINATOR_SERVICE" > /dev/null <<EOF
[Unit]
Description=SC2 Driver IO Python Coordinator
After=network.target sc2-backend.service
Wants=network.target
Requires=sc2-backend.service

[Service]
Type=simple
User=sunpi
Group=sunpi
WorkingDirectory=$PROJECT_ROOT
Environment=PYTHONPATH=$PROJECT_ROOT
ExecStart=/usr/bin/python3 $PROJECT_ROOT/main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Create Textual dashboard service (runs as sunpi user on main console)
DASHBOARD_SERVICE="/etc/systemd/system/sc2-dashboard.service"
echo -e "\n${YELLOW}Creating Textual dashboard service...${NC}"

sudo tee "$DASHBOARD_SERVICE" > /dev/null <<EOF
[Unit]
Description=SC2 Driver IO Terminal Dashboard
After=network.target sc2-coordinator.service
Wants=network.target

[Service]
Type=simple
User=sunpi
Group=sunpi
WorkingDirectory=$PROJECT_DIR
Environment=TERM=xterm-256color
Environment=PYTHONPATH=$PROJECT_ROOT
Environment=DISPLAY=:0
ExecStart=/usr/bin/python3 $PROJECT_DIR/dashboard_launcher.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Run on VT2 (leave VT1 for Weston if needed)
StandardInput=tty
TTYPath=/dev/tty2
TTYReset=yes
TTYVHangup=yes

[Install]
WantedBy=multi-user.target
EOF

# Option: Alternative Weston integration script
WESTON_SCRIPT="/home/sunpi/start-sc2-dashboard.sh"
echo -e "\n${YELLOW}Creating Weston integration script (alternative)...${NC}"

sudo tee "$WESTON_SCRIPT" > /dev/null <<EOF
#!/bin/bash
# Alternative: Start SC2 components from within Weston

# Start C++ backend as root (for GPS access)
sudo systemctl start sc2-backend.service

# Start Python coordinator
systemctl --user start sc2-coordinator.service

# Option 1: Start Textual dashboard in terminal
gnome-terminal -- python3 $PROJECT_DIR/dashboard_launcher.py

# Option 2: Or run in current terminal (fullscreen)
# python3 $PROJECT_DIR/dashboard_launcher.py
EOF

sudo chmod +x "$WESTON_SCRIPT"
sudo chown sunpi:sunpi "$WESTON_SCRIPT"

# Reload systemd and enable services
echo -e "\n${YELLOW}Enabling services...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable sc2-backend.service
sudo systemctl enable sc2-coordinator.service

# Ask user for boot preference
echo -e "\n${YELLOW}Choose boot configuration:${NC}"
echo "1) Headless mode (no Weston, just terminal dashboard on tty2) - RECOMMENDED"
echo "2) Keep existing Weston setup + add terminal dashboard"
echo "3) Integrate with existing Weston autolaunch"
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo -e "\n${YELLOW}Configuring headless mode...${NC}"
        sudo systemctl enable sc2-dashboard.service
        sudo systemctl set-default multi-user.target
        echo "System will boot to console with terminal dashboard on tty2"
        echo "Access dashboard: Alt+F2, main console: Alt+F1"
        ;;
    2)
        echo -e "\n${YELLOW}Keeping Weston + adding terminal dashboard...${NC}"
        sudo systemctl enable sc2-dashboard.service
        echo "Weston will still start, terminal dashboard available on tty2"
        echo "Switch between: Alt+F1 (Weston), Alt+F2 (Dashboard)"
        ;;
    3)
        echo -e "\n${YELLOW}Integrating with Weston autolaunch...${NC}"
        echo "Update /home/sunpi/.config/weston.ini [autolaunch] section:"
        echo "path=/home/sunpi/start-sc2-dashboard.sh"
        echo "This will start all SC2 components when Weston starts"
        ;;
esac

echo -e "\n${GREEN}Setup complete!${NC}"
echo "================"
echo "Services created:"
echo "  - sc2-backend.service  (C++ headless telemetry)"
echo "  - sc2-dashboard.service (Textual terminal GUI)"
echo ""
echo "To start now:"
echo "  sudo systemctl start sc2-backend"
echo "  sudo systemctl start sc2-dashboard"
echo ""
echo "To check status:"
echo "  sudo systemctl status sc2-backend"
echo "  sudo systemctl status sc2-dashboard"
echo ""
echo -e "${YELLOW}Reboot to test auto-launch:${NC} sudo reboot"