# Network Failover Configuration

## Overview

This system is configured with automatic network failover between WiFi and LTE using routing metrics. WiFi has priority when available, and LTE serves as an automatic fallback connection.

## Configuration

### Network Interfaces

- **wlan0** (WiFi): Primary connection
  - Connection name: `[network name]`
  - Routing metric: **100** (higher priority)
  
- **usb0** (LTE): Backup connection
  - Hardware: Quectel EG25 LTE modem
  - Routing metric: **1003** (lower priority)
  - APN: `fast.t-mobile.com`

### How It Works

Linux routing uses **metrics** to determine connection priority:
- **Lower metric = higher priority**
- When multiple default routes exist, traffic uses the route with the lowest metric
- When WiFi (metric 100) is active, all traffic routes through WiFi
- When WiFi disconnects, LTE (metric 1003) automatically becomes the active route

## Usage

### Check Current Connection

```bash
# View active default routes
ip route show default

# Check connection status
nmcli connection show --active
```

### Manual WiFi Control

```bash
# Disconnect WiFi (switches to LTE automatically)
sudo nmcli connection down [network name]

# Reconnect to saved WiFi network
sudo nmcli device connect wlan0

# Or reconnect by connection name
sudo nmcli connection up [network name]
```

### Verify Failover

```bash
# Check which interface is being used
ip route get 8.8.8.8

# Test connectivity
ping -c 3 google.com
```

## Connection Details

### WiFi Configuration
- Metric: 100
- Auto-connect: Yes
- Managed by: NetworkManager

### LTE Configuration
- Metric: 1003
- Interface: usb0 (cdc_ether driver)
- Protocol: Direct ethernet (not PPP)
- Auto-connect: Yes via initial EPS bearer
- The modem maintains a default-attach bearer automatically

## Troubleshooting

### Check LTE Modem Status

```bash
# List modems
mmcli -L

# View detailed modem info
mmcli -m 0

# Check signal strength
mmcli -m 0 | grep "signal quality"
```

### Check usb0 Interface

```bash
# View interface status
ip addr show usb0

# Check if DHCP is active
nmcli device show usb0
```

### View Routing Table

```bash
# Show all routes with metrics
ip route show

# Show only default routes
ip route show default
```

## Configuration Files

Network metrics are configured in NetworkManager connection profiles:
- WiFi: `/etc/NetworkManager/system-connections/[network name].nmconnection`
- LTE: Managed by ModemManager initial bearer

## Notes

- The LTE modem uses the `cdc_ether` driver which creates a direct ethernet interface (usb0)
- No PPP configuration is required - the modem handles connectivity internally
- The system automatically switches between connections based on availability
- Both connections can be active simultaneously; routing metrics determine which is used
- The setup persists across reboots via NetworkManager's autoconnect feature
