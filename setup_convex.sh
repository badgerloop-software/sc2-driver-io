#!/bin/bash
# Quick setup script for Convex integration on Raspberry Pi

echo "SC2 Convex Integration Setup"
echo "============================="
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo "⚠️  Warning: This doesn't appear to be a Raspberry Pi"
    echo "   Continuing anyway..."
fi

# Check for libcurl
echo "Checking for libcurl..."
if ! pkg-config --exists libcurl; then
    echo "❌ libcurl not found. Installing..."
    sudo apt-get update
    sudo apt-get install -y libcurl4-openssl-dev
    echo "✅ libcurl installed"
else
    echo "✅ libcurl already installed"
fi

# Check for Python requests (for testing)
echo ""
echo "Checking for Python requests library..."
if ! python3 -c "import requests" 2>/dev/null; then
    echo "Installing Python requests..."
    pip3 install requests
    echo "✅ Python requests installed"
else
    echo "✅ Python requests already installed"
fi

# Check config.json
echo ""
echo "Checking config.json..."
if [ ! -f "config.json" ]; then
    echo "❌ config.json not found!"
    exit 1
fi

CONVEX_URL=$(python3 -c "import json; print(json.load(open('config.json')).get('convex_deployment_url', ''))" 2>/dev/null)

if [ -z "$CONVEX_URL" ] || [ "$CONVEX_URL" = "https://your-deployment.convex.cloud" ]; then
    echo "⚠️  Convex URL not configured in config.json"
    echo ""
    echo "Please update config.json with your Convex deployment URL:"
    echo '  "convex_deployment_url": "https://your-deployment.convex.site"'
    echo ""
    echo "Get your URL from: https://dashboard.convex.dev"
else
    echo "✅ Convex URL configured: $CONVEX_URL"
fi

# Rebuild C++ system
echo ""
echo "Rebuilding C++ telemetry system..."
if [ -d "build" ]; then
    cd build
    if cmake .. && make; then
        echo "✅ Build successful"
    else
        echo "❌ Build failed"
        exit 1
    fi
    cd ..
else
    echo "❌ Build directory not found. Run cmake first."
    exit 1
fi

# Test LTE connection
echo ""
echo "Testing internet connectivity..."
if ping -c 3 8.8.8.8 > /dev/null 2>&1; then
    echo "✅ Internet connection working"
else
    echo "⚠️  No internet connection detected"
    echo "   Make sure LTE modem is configured"
fi

echo ""
echo "Setup complete! Next steps:"
echo ""
echo "1. Deploy Convex functions (from your computer):"
echo "   cd sc2-convex"
echo "   npx convex deploy"
echo ""
echo "2. Update config.json with your Convex URL"
echo ""
echo "3. Test the integration:"
echo "   python3 test_convex_integration.py"
echo ""
echo "4. Run the full system:"
echo "   ./build/sc2-driver-io"
echo "   # or"
echo "   python3 services/coordinator.py"
echo ""
