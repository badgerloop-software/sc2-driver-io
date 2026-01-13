/**
 * Convex Schema for SC2 Telemetry Data
 * 
 * Deploy this to your Convex project:
 * 1. Create a Convex project: npx convex init
 * 2. Save this file as: convex/schema.ts
 * 3. Deploy: npx convex deploy
 */

import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  // Telemetry data table - stores raw byte arrays following sc1-data-format
  telemetry: defineTable({
    timestamp: v.number(),        // Original timestamp from car (ms since epoch)
    data: v.string(),             // Hex-encoded byte array structured per sc1-data-format/format.json
    dataSize: v.number(),         // Original data size in bytes
    source: v.string(),           // Identifier (e.g., "telemetry", "can_bridge")
    dataFormat: v.string(),       // Format identifier: "sc1-data-format"
    formatVersion: v.string(),    // Format version for compatibility: "1.0"
    receivedAt: v.number(),       // Server timestamp when received (ms since epoch)
  })
    .index("by_timestamp", ["timestamp"])
    .index("by_source", ["source"])
    .index("by_received", ["receivedAt"])
    .index("by_format", ["dataFormat"]),
  
  // Format metadata table - stores the sc1-data-format schema
  telemetryFormat: defineTable({
    formatVersion: v.string(),    // "1.0"
    fields: v.array(v.object({    // Field definitions from format.json
      name: v.string(),           // Field name (e.g., "speed", "soc")
      numBytes: v.number(),       // Number of bytes
      dataType: v.string(),       // "float", "uint8", "bool", etc.
      units: v.string(),          // Units (e.g., "mph", "%", "degC")
      nominalMin: v.number(),     // Expected minimum value
      nominalMax: v.number(),     // Expected maximum value
      category: v.string(),       // Category/Subsystem
      offset: v.number(),         // Byte offset in array
    })),
    updatedAt: v.number(),        // When format was last updated
  })
    .index("by_version", ["formatVersion"]),
  
  // Optional: Parsed telemetry values for easier querying
  telemetryParsed: defineTable({
    timestamp: v.number(),
    speed: v.optional(v.number()),
    soc: v.optional(v.number()),
    packVoltage: v.optional(v.number()),
    packCurrent: v.optional(v.number()),
    motorTemp: v.optional(v.number()),
    packTemp: v.optional(v.number()),
    lapCount: v.optional(v.number()),
    source: v.string(),
    receivedAt: v.number(),
  })
    .index("by_timestamp", ["timestamp"])
    .index("by_source", ["source"]),
});
