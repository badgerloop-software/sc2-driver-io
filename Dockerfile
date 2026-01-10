# Use Debian Trixie as base (ARM64 for Pi simulation)
FROM arm64v8/debian:trixie

# Update and install system dependencies
RUN apt-get update && apt-get install -y \
    cmake \
    g++ \
    build-essential \
    python3 \
    python3-pip \
    python3-dev \
    libgpiod-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages (adjust based on your textual_requirements.txt)
RUN pip3 install --no-cache-dir \
    textual \
    gpiozero \
    attrs \
    certifi \
    cryptography \
    psutil \
    rich \
    pyserial \
    python-can \
    websockets

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Build C++ components (if needed)
RUN mkdir build && cd build && cmake .. && make

# Expose ports if your app uses them (e.g., for telemetry)
EXPOSE 8080

# Default command (adjust for your entry point, e.g., services/coordinator.py)
CMD ["python3", "services/coordinator.py"]