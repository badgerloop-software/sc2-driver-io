import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

// Simplified schema: stores telemetry as flexible JSON objects
// Each field from sc1-data-format is stored directly as a property
// Example record:
// {
//   timestamp: 1234567890,
//   source: "telemetry",
//   receivedAt: 1234567891,
//   speed: 45.5,
//   soc: 87.3,
//   packVoltage: 350.2,
//   packCurrent: 12.5,
//   driver_eStop: false,
//   ... (all other fields from format.json)
// }

export default defineSchema({
  telemetry: defineTable({
    // Metadata fields (always present)
    timestamp: v.number(),        // Original data collection time
    source: v.string(),           // Data source identifier (e.g., "telemetry")
    receivedAt: v.number(),       // Server receipt time
    
    // Telemetry data stored as flexible object
    // All fields from sc1-data-format/format.json will be present
    // Field names and types match the format specification
  })
    .index("by_timestamp", ["timestamp"])
    .index("by_source", ["source"])
    .index("by_received", ["receivedAt"]),
});
