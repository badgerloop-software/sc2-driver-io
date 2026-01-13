# Convex Integration Setup Guide

## Overview
The SC2 telemetry system uses Convex as the cloud database for LTE transmission. Telemetry data is **parsed in C++** and sent as JSON key-value pairs via HTTPS.

> **Note**: This system sends **parsed telemetry** (name:value pairs), not raw hex bytes. See `CONVEX_SIMPLIFIED.md` for architecture details.

## Quick Start
For a fast 10-minute setup, see **`CONVEX_QUICKSTART.md`**.

## Prerequisites
1. A Convex account and deployment at [convex.dev](https://www.convex.dev/)
2. Raspberry Pi configured with LTE internet connection
3. libcurl installed on the Raspberry Pi
4. sc1-data-format/format.json in your project

## Step 1: Install libcurl on Raspberry Pi
```bash
sudo apt-get update
sudo apt-get install libcurl4-openssl-dev
```

## Step 2: Deploy Convex Project

### Use the Provided Template
```bash
cd docs/convex-example

# Install dependencies
npm install

# Login and deploy (opens browser)
npx convex dev
```

### Schema Overview (convex/schema.ts)
The telemetry table stores parsed JSON objects:
```typescript
telemetry: defineTable({
  // Metadata fields
  timestamp: v.number(),
  source: v.string(),
  receivedAt: v.number(),
  
  // All telemetry fields from sc1-data-format
  // stored as direct properties (not in separate tables)
})
```

      offset: v.number(),
    })),
    updatedAt: v.number(),
  })
  .index("by_version", ["formatVersion"]),
});
```

### Create Mutation Function (convex/telemetry.ts)
```typescript
import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const storeTelemetry = mutation({
  args: {
    timestamp: v.number(),
    data: v.string(),
    dataSize: v.number(),
    source: v.string(),
    dataFormat: v.string(),       // "sc1-data-format"
    formatVersion: v.string(),    // "1.0"
    receivedAt: v.number(),
  },
  handler: async (ctx, args) => {
    // Validate format
    if (args.dataFormat !== "sc1-data-format") {
      console.warn(`Unknown data format: ${args.dataFormat}`);
    }
    
    // Store the telemetry data
    const id = await ctx.db.insert("telemetry", {
      timestamp: args.timestamp,
      data: args.data,
      dataSize: args.dataSize,
      source: args.source,
      dataFormat: args.dataFormat,
      formatVersion: args.formatVersion,
      receivedAt: args.receivedAt,
    });
    
    console.log(`Stored telemetry: ${args.dataSize} bytes (format: ${args.dataFormat} v${args.formatVersion})`);
    
    return { success: true, id };
  },
});
```

### Create Parser Functions (convex/telemetryParser.ts)
Copy the file from `docs/convex-example/telemetryParser.ts` to your Convex project.
This provides functions to parse the binary data according to sc1-data-format.

## Step 3: Deploy Convex Functions
```bash
cd your-convex-project

# Copy all example files
cp ../sc2-driver-io/docs/convex-example/*.ts convex/

# Deploy to Convex
npx convex deploy
```

## Step 4: Upload Format Schema
After deploying, upload the sc1-data-format schema to Convex:

```bash
cd /path/to/sc2-driver-io
python3 upload_format_to_convex.py
```

This will:
- Read `sc1-data-format/format.json`
- Calculate byte offsets for each field
- Upload the complete schema to Convex
- Enable automatic parsing of telemetry data

## Step 4: Update config.json
After deploying, get your deployment URL from the Convex dashboard and update `config.json`:

```json
{
  "convex_deployment_url": "https://your-deployment-name.convex.site",
  "convex_mutation_endpoint": "/api/mutation",
  "convex_mutation_name": "telemetry:storeTelemetry",
  "convex_timeout_ms": 5000,
  "convex_retry_interval_ms": 3000
}
```

**Important:** Replace `your-deployment-name` with your actual Convex deployment name from the dashboard.

## Step 5: Rebuild C++ Telemetry
```bash
cd /path/to/sc2-driver-io/build
cmake ..
make
```

## Step 6: Test the Integration

### Python Test Script
See `test_convex_integration.py` for a test that simulates telemetry data.

### Monitor Convex Dashboard
1. Go to your Convex dashboard
2. Navigate to Data → telemetry table
3. You should see records appearing as telemetry is sent

## Data Format

### Outgoing (C++ → Convex)
```json
{
  "path": "telemetry:storeTelemetry",
  "args": [{
    "timestamp": 1673890123456,
    "data": "0a1b2c3d4e5f...",  // Hex-encoded bytes
    "dataSize": 128,
    "source": "telemetry",
    "receivedAt": 1673890123789
  }]
}
```

### Storage (In Convex)
- `timestamp`: Original telemetry timestamp (ms since epoch)
- `data`: Hex-encoded byte array of telemetry data
- `dataSize`: Number of bytes in original data
- `source`: Identifier string (default: "telemetry")
- `receivedAt`: Server-side timestamp when received

## Decoding Data
To decode the hex data back to bytes in JavaScript/TypeScript:
```typescript
function hexToBytes(hex: string): Uint8Array {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.substr(i, 2), 16);
  }
  return bytes;
}
```

## Troubleshooting

### "Convex URL not configured"
- Ensure `convex_deployment_url` is set in `config.json`
- Verify the URL format includes `https://` and `.convex.site`

### "CURL error" or "HTTP 404"
- Check that mutation function is deployed: `npx convex deploy`
- Verify mutation name matches: `telemetry:storeTelemetry`
- Check endpoint path: `/api/mutation`

### "HTTP 400 Bad Request"
- Mutation arguments might not match schema
- Check Convex logs in dashboard for details

### Connection timeout
- Verify LTE connection: `ping 8.8.8.8`
- Check firewall rules allow outbound HTTPS
- Try increasing `convex_timeout_ms` in config.json

## Performance Notes
- Background worker thread prevents blocking telemetry collection
- Failed requests are logged but don't retry automatically (can be added if needed)
- Queue size is unlimited - monitor memory on long disconnections
- Consider adding queue size limits and disk buffering for production

## Security Considerations
- Convex deployments are secured by default
- Consider adding authentication for production use
- Monitor usage to stay within Convex free tier limits
- Data is transmitted over HTTPS (encrypted)

## Next Steps
1. Add data visualization dashboard using Convex queries
2. Implement exponential backoff retry logic
3. Add metrics for transmission success rate
4. Consider batching multiple records per request for efficiency
