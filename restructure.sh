#!/bin/bash
set -e

echo "Starting project restructure..."

# Create new directory structure
echo "Creating new directories..."
mkdir -p core/ipc
mkdir -p core/data_format
mkdir -p can_bus
mkdir -p telemetry
mkdir -p data_processor
mkdir -p services/systemd
mkdir -p neural_network
mkdir -p textual_frontend/widgets

# Move can_utils to can_bus and rename files
echo "Restructuring CAN utilities..."
if [ -d "can_utils" ]; then
    cp can_utils/__init__.py can_bus/__init__.py 2>/dev/null || touch can_bus/__init__.py
    cp can_utils/data_classes.py can_bus/data_classes.py
    cp can_utils/read_can_messages.py can_bus/signal_parser.py
    cp can_utils/send_messages.py can_bus/can_writer.py
    cp can_utils/csv_writer.py can_bus/csv_logger.py
fi

# Move backend/telemetrylib to telemetry
echo "Restructuring telemetry..."
if [ -d "backend/telemetrylib" ]; then
    cp backend/telemetrylib/*.h telemetry/ 2>/dev/null || true
    cp backend/telemetrylib/*.cpp telemetry/ 2>/dev/null || true
    cp backend/telemetrylib/CMakeLists.txt telemetry/ 2>/dev/null || true
fi

# Rename DataProcessor to data_processor
echo "Restructuring data processor..."
if [ -d "DataProcessor" ]; then
    cp DataProcessor/*.h data_processor/ 2>/dev/null || true
    cp DataProcessor/*.cpp data_processor/ 2>/dev/null || true
    cp DataProcessor/CMakeLists.txt data_processor/ 2>/dev/null || true
fi

# Rename lapscounter.py to lap_counter.py
echo "Restructuring lap counter..."
if [ -f "lap_counter/lapscounter.py" ]; then
    cp lap_counter/lapscounter.py lap_counter/lap_counter.py
fi
touch lap_counter/__init__.py

# Move main.py to services/coordinator.py
echo "Setting up services..."
if [ -f "main.py" ]; then
    cp main.py services/coordinator.py
fi

# Create neural_network structure
echo "Creating neural network placeholder..."
touch neural_network/__init__.py

echo "Restructure complete!"
echo "Note: Original files preserved. Review changes and remove old directories when ready."

