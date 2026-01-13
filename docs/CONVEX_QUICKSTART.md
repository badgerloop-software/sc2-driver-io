# Convex Integration - Quick Start

This guide will get your Convex database up and running in 10 minutes.

## Prerequisites
- Node.js 18+ installed  
- npm or yarn package manager
- A Convex account (free tier available at https://convex.dev)

## 1. Setup Convex Project (5 minutes)

```bash
# Navigate to the example directory
cd docs/convex-example

# Install dependencies
npm install

# Login to Convex (opens browser)
npx convex dev

# This will:
# 1. Create a new Convex project
# 2. Deploy your schema and functions
# 3. Give you a deployment URL like: https://happy-animal-123.convex.cloud
```

Copy the deployment URL - you'll need it for the next step.

## 2. Configure SC2 System

Edit `/path/to/sc2-driver-io/config.json`:

```json
{
  "convex_deployment_url": "https://happy-animal-123.convex.cloud",
  "convex_mutation_endpoint": "/api/mutation",
  "convex_mutation_name": "telemetry:storeTelemetry",
  "convex_timeout_ms": 5000,
  "convex_retry_interval_ms": 3000
}
```

## 3. Install libcurl on Raspberry Pi

```bash
sudo apt-get update
sudo apt-get install libcurl4-openssl-dev
```


## 4. Rebuild C++ System

```bash
cd /path/to/sc2-driver-io/build
cmake ..
make
```

## 5. Test Integration

```bash
# Run the full system on Raspberry Pi
./build/sc2-driver-io
# or
python3 services/coordinator.py
```

## 6. Monitor Data

- Dashboard: https://dashboard.convex.dev
- Navigate to: Your Project → Data → telemetry table
- You should see records appearing in real-time

## What Gets Sent

Each telemetry record is a JSON object with all telemetry fields parsed:

```json
{
  "timestamp": 1234567890,
  "source": "telemetry",
  "receivedAt": 1234567891,
  "speed": 45.5,
  "soc": 87.3,
  "packVoltage": 350.2,
  "packCurrent": 12.5,
  "driver_eStop": false,
  "packTemp": 35.2,
  ...
}
```

Field names and types match **sc1-data-format/format.json** exactly. Parsing happens **automatically in C++** before sending.

## Querying Data

```typescript
// Get recent telemetry
const data = useQuery(api.telemetry.getRecentTelemetry, { limit: 100 });

// Get specific fields for plotting
const speedData = useQuery(api.telemetry.getTelemetryFields, {
  fields: ["speed", "soc", "packVoltage"],
  startTime: Date.now() - 3600000,  // Last hour
  endTime: Date.now(),
  limit: 1000
});
```

## Advantages

- ✅ **No parsing needed**: Data already in readable format
- ✅ **Easy queries**: Just reference field names directly
- ✅ **Type-safe**: Numbers are numbers, booleans are booleans
- ✅ **Flexible**: Add fields by updating format.json and rebuilding

## Data Flow

```
CAN Bus → Coordinator → Telemetry Consumer → Unix Socket
                                                    ↓
                                            C++ Telemetry (sql.cpp)
                                                    ↓
                                            Parse using sc1-data-format
                                                    ↓
                                            Build JSON (name:value pairs)
                                                    ↓
                                            LTE Modem → Internet (HTTPS)
                                                    ↓
                                            Convex Cloud Database
```

## Troubleshooting

### "Convex URL not configured"
Add to config.json:
```json
"convex_deployment_url": "https://your-actual-deployment.convex.cloud"
```

### "CURL not found" during build
```bash
sudo apt-get install libcurl4-openssl-dev
# Then rebuild
```

### "HTTP 404" when sending
```bash
# Redeploy Convex functions
cd docs/convex-example
npx convex dev
```

### Test LTE connection
```bash
ping -c 3 8.8.8.8           # Check internet
ping -c 3 google.com        # Check DNS  
curl https://www.convex.dev # Test HTTPS
```

### "Failed to load format.json"
Ensure sc1-data-format/format.json exists and is valid JSON. The C++ program needs this to parse byte arrays.

## Performance

- Async sending (non-blocking)
- ~100-500ms latency per packet (depending on LTE signal)
- Queue-based architecture (won't block CAN reading)
- Automatic format loading on startup

## Next Steps

1. ✅ Setup complete - parsed data flowing to Convex
2. Build dashboard to visualize telemetry
3. Create custom queries for specific analysis
4. Set up webhooks for real-time alerts
5. Monitor LTE data usage

## Cost & Limits

Convex free tier:
- 1M function calls/month
- 1GB storage
- 1GB bandwidth

Should cover development/testing. Production may need paid plan.

