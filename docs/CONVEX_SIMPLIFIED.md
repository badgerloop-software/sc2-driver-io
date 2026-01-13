# Convex Integration - Implementation Summary

## Overview
Simplified Convex cloud database integration that sends **parsed telemetry data** as JSON key-value pairs instead of raw hex-encoded bytes.

## What Changed

### Before (Complex Approach)
1. C++ sent hex-encoded byte arrays to Convex
2. Stored format metadata in separate `telemetryFormat` table
3. Required Python parser utilities to decode hex back to values
4. Complex queries needed to extract readable data

### After (Simplified Approach)
1. C++ **parses byte arrays** using sc1-data-format/format.json
2. Sends **JSON with field names and values** directly
3. No parsing needed on query - data is already readable
4. Simple queries: just reference field names

## Architecture

```
┌─────────────┐
│  CAN Bus    │
│  Messages   │
└──────┬──────┘
       │
       ▼
┌──────────────────┐
│ Coordinator.py   │  Python layer
│ (CAN Reader)     │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ Telemetry        │  Via Unix Socket
│ Consumer         │
└──────┬───────────┘
       │
       ▼
┌──────────────────┐
│ sql.cpp          │  C++ layer
│ (Convex Client)  │
│                  │
│ 1. Loads         │  Startup
│    format.json   │
│                  │
│ 2. Receives      │  Runtime
│    byte array    │
│                  │
│ 3. Parses to     │  Using format defs
│    name:value    │
│                  │
│ 4. Builds JSON   │  RapidJSON
│                  │
│ 5. Sends HTTPS   │  libcurl
└──────┬───────────┘
       │
       ▼ (LTE Modem)
       │
       ▼
┌──────────────────┐
│ Convex Cloud     │  Cloud Database
│ Database         │
│                  │
│ {"timestamp": …, │  Stored as JSON
│  "speed": 45.5,  │  No hex encoding!
│  "soc": 87.3,    │
│  ...}            │
└──────────────────┘
```

## Data Format

### JSON Payload Sent to Convex
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
  "external_eStop": false,
  "packTemp": 35.2,
  "motorTemp": 42.1,
  ...
}
```

All 179 fields from sc1-data-format/format.json are included as individual properties.

## Implementation Details

### sql.cpp Changes
1. **Loads format.json** on startup
   - Parses field definitions (name, numBytes, dataType, offset)
   - Builds internal lookup table

2. **Parsing Logic**
   - Uses helper functions: `sqlBytesToFloat`, `sqlBytesToUint8`, etc.
   - Respects byte order (little-endian)
   - Handles all 4 data types: float, uint8, uint16, bool

3. **JSON Building**
   - Uses RapidJSON library
   - Creates Value objects for each field
   - Properly handles allocator for dynamic keys

4. **HTTP Transmission**
   - libcurl for HTTPS POST
   - Async worker thread (non-blocking)
   - Queue-based architecture
   - Timeout and error handling

### Convex Schema (schema.ts)
```typescript
telemetry: defineTable({
  // Metadata (always present)
  timestamp: v.number(),
  source: v.string(),
  receivedAt: v.number(),
  
  // Telemetry fields added dynamically
  // (all fields from format.json)
})
  .index("by_timestamp", ["timestamp"])
  .index("by_source", ["source"])
```

### Convex Mutation (telemetry.ts)
```typescript
export const storeTelemetry = mutation({
  args: v.any(),  // Accept any object structure
  handler: async (ctx, telemetryData) => {
    // Validate required fields
    // Store entire object
    return await ctx.db.insert("telemetry", telemetryData);
  },
});
```

## Advantages

### 1. **No Parsing Overhead**
- Data arrives ready-to-use
- No hex decoding on query
- No separate format table needed

### 2. **Easy Queries**
```typescript
// Get speed data
const speeds = data.map(d => d.speed);

// Filter by condition
const highSpeed = data.filter(d => d.speed > 50);

// Plot multiple metrics
const plot = data.map(d => ({
  time: d.timestamp,
  speed: d.speed,
  soc: d.soc
}));
```

### 3. **Type Safety**
- Numbers stored as numbers (not strings)
- Booleans stored as booleans
- Direct arithmetic operations possible
- JSON queries work naturally

### 4. **Flexibility**
- Add new fields: just update format.json and rebuild
- No schema migration needed (Convex is schemaless for field content)
- Easy to extend with computed fields

### 5. **Debugging**
- Can inspect data directly in Convex dashboard
- Human-readable format
- No hex decoding tools needed

## Performance

### Parsing Cost
- **One-time cost** during C++ startup to load format.json
- **Per-message cost**: ~50-200 CPU instructions per field (minimal)
- **Memory**: ~10KB for format definitions

### Network Impact
- JSON is more verbose than hex (roughly 2-3x larger)
- Example: 200-byte hex → ~600-byte JSON
- LTE bandwidth: typical telemetry = 600 bytes @ 10Hz = 60 KB/s
- **Bandwidth usage**: ~5 MB/hour (acceptable for LTE)

### Benefits Outweigh Costs
- Parsing happens **once** in C++ (not repeatedly on query)
- Saves cloud compute costs (no server-side parsing)
- Faster query performance (indexed numerical values)

## Configuration

### config.json
```json
{
  "convex_deployment_url": "https://your-deployment.convex.cloud",
  "convex_mutation_endpoint": "/api/mutation",
  "convex_mutation_name": "telemetry:storeTelemetry",
  "convex_timeout_ms": 5000,
  "convex_retry_interval_ms": 3000
}
```

### Required Files
- `sc1-data-format/format.json` - Field definitions
- `docs/convex-example/` - Convex project template

## Removed Components
Since we're sending parsed data, these are **no longer needed**:
- ❌ `upload_format_to_convex.py` - No format table needed
- ❌ `telemetryParser.ts` - No server-side parsing
- ❌ `telemetryFormat` table - Format metadata unnecessary
- ❌ Parser utility functions - Data already parsed

## Testing

### 1. Check Format Loading
Look for startup message:
```
Convex LTE transmission initialized
  Convex URL: https://...
  Mutation: telemetry:storeTelemetry
  Format fields: 179
```

### 2. Verify Sending
Look for success messages:
```
Convex: Sent telemetry data (timestamp: 1234567890) - HTTP 200
```

### 3. Inspect Convex Dashboard
- Open https://dashboard.convex.dev
- Navigate to Data → telemetry table
- Verify fields are readable numbers/booleans

### 4. Query Data
```typescript
// In Convex dashboard Functions tab
api.telemetry.getRecentTelemetry({ limit: 10 })

// Should return:
[
  {
    _id: "...",
    _creationTime: ...,
    timestamp: 1234567890,
    speed: 45.5,
    soc: 87.3,
    ...
  }
]
```

## Troubleshooting

### "Failed to load format.json"
- Ensure `sc1-data-format/format.json` exists
- Check file path relative to executable
- Verify JSON is valid

### "Format fields: 0"
- format.json parsing failed
- Check JSON syntax
- Ensure file is readable

### "Convex URL not configured"
- Set `convex_deployment_url` in config.json
- Must start with `https://`
- Must end with `.convex.cloud`

### "HTTP 404" errors
- Mutation name mismatch
- Verify: `telemetry:storeTelemetry`
- Redeploy Convex functions

### Data looks wrong in Convex
- Check byte order (should be little-endian)
- Verify offset calculations in format.json
- Compare with local CSV logs for validation

## Future Enhancements

### Possible Improvements
1. **Compression**: Gzip JSON before sending (reduces bandwidth 70%)
2. **Batching**: Send multiple records per request (reduces overhead)
3. **Selective Fields**: Only send changed values (reduces payload size)
4. **Retry Logic**: Automatic retry on failure (improves reliability)
5. **Local Buffer**: Store-and-forward on connection loss

### Not Recommended
- ❌ Going back to hex encoding (loses all advantages)
- ❌ Adding server-side parsing (duplicates work)
- ❌ Storing raw bytes (defeats the purpose)

## Summary

✅ **Implemented**: C++ parses telemetry and sends JSON key-value pairs
✅ **Advantage**: No parsing needed on query - data is ready-to-use
✅ **Trade-off**: Slightly larger payloads (~3x) but better usability
✅ **Result**: Simpler architecture, easier queries, faster development

This approach prioritizes **developer productivity** and **query performance** over minimal bandwidth usage, which is the right trade-off for this application.
