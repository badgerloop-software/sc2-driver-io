#!/bin/bash
# Enable LTE connection on usb0 interface
# This script brings up the usb0 interface and requests DHCP

set -e

INTERFACE="usb0"
MAX_WAIT=30
WAIT_COUNT=0

echo "Waiting for $INTERFACE to appear..."
while [ ! -e "/sys/class/net/$INTERFACE" ] && [ $WAIT_COUNT -lt $MAX_WAIT ]; do
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
done

if [ ! -e "/sys/class/net/$INTERFACE" ]; then
    echo "ERROR: $INTERFACE did not appear after ${MAX_WAIT} seconds"
    exit 1
fi

echo "$INTERFACE found, configuring..."

# Bring up the interface
ip link set $INTERFACE up

# Get DHCP address
dhcpcd -b $INTERFACE

echo "LTE interface $INTERFACE is up and configured"
