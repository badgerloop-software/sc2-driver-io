/**
 * Utility functions for parsing sc1-data-format telemetry data
 * Use these in your Convex queries to decode the hex data
 */

import { v } from "convex/values";
import { query, mutation } from "./_generated/server";

/**
 * Helper function to parse hex string to bytes
 */
function hexToBytes(hex: string): Uint8Array {
  const bytes = new Uint8Array(hex.length / 2);
  for (let i = 0; i < hex.length; i += 2) {
    bytes[i / 2] = parseInt(hex.substr(i, 2), 16);
  }
  return bytes;
}

/**
 * Helper function to read float from bytes (little-endian)
 */
function readFloat(bytes: Uint8Array, offset: number): number {
  const buffer = new ArrayBuffer(4);
  const view = new DataView(buffer);
  for (let i = 0; i < 4; i++) {
    view.setUint8(i, bytes[offset + i]);
  }
  return view.getFloat32(0, true); // true = little-endian
}

/**
 * Helper function to read uint8 from bytes
 */
function readUint8(bytes: Uint8Array, offset: number): number {
  return bytes[offset];
}

/**
 * Helper function to read uint16 from bytes (little-endian)
 */
function readUint16(bytes: Uint8Array, offset: number): number {
  return bytes[offset] | (bytes[offset + 1] << 8);
}

/**
 * Helper function to read bool from bytes
 */
function readBool(bytes: Uint8Array, offset: number): boolean {
  return bytes[offset] !== 0;
}

/**
 * Upload format schema from sc1-data-format/format.json
 * Call this once to store the format in Convex
 */
export const uploadFormatSchema = mutation({
  args: {
    formatVersion: v.string(),
    fields: v.array(v.object({
      name: v.string(),
      numBytes: v.number(),
      dataType: v.string(),
      units: v.string(),
      nominalMin: v.number(),
      nominalMax: v.number(),
      category: v.string(),
      offset: v.number(),
    })),
  },
  handler: async (ctx, args) => {
    // Check if format already exists
    const existing = await ctx.db
      .query("telemetryFormat")
      .withIndex("by_version", (q) => q.eq("formatVersion", args.formatVersion))
      .first();
    
    if (existing) {
      // Update existing format
      await ctx.db.patch(existing._id, {
        fields: args.fields,
        updatedAt: Date.now(),
      });
      console.log(`Updated format schema v${args.formatVersion}`);
      return { updated: true, id: existing._id };
    } else {
      // Insert new format
      const id = await ctx.db.insert("telemetryFormat", {
        formatVersion: args.formatVersion,
        fields: args.fields,
        updatedAt: Date.now(),
      });
      console.log(`Inserted format schema v${args.formatVersion}`);
      return { updated: false, id };
    }
  },
});

/**
 * Get the current format schema
 */
export const getFormatSchema = query({
  args: { formatVersion: v.optional(v.string()) },
  handler: async (ctx, args) => {
    const version = args.formatVersion ?? "1.0";
    return await ctx.db
      .query("telemetryFormat")
      .withIndex("by_version", (q) => q.eq("formatVersion", version))
      .first();
  },
});

/**
 * Parse telemetry data and return as structured object
 */
export const parseTelemetryData = query({
  args: { telemetryId: v.id("telemetry") },
  handler: async (ctx, args) => {
    // Get the telemetry record
    const telemetry = await ctx.db.get(args.telemetryId);
    if (!telemetry) {
      throw new Error("Telemetry record not found");
    }
    
    // Get the format schema
    const format = await ctx.db
      .query("telemetryFormat")
      .withIndex("by_version", (q) => q.eq("formatVersion", telemetry.formatVersion))
      .first();
    
    if (!format) {
      throw new Error(`Format schema v${telemetry.formatVersion} not found`);
    }
    
    // Parse the hex data
    const bytes = hexToBytes(telemetry.data);
    const parsed: Record<string, any> = {
      _timestamp: telemetry.timestamp,
      _source: telemetry.source,
      _receivedAt: telemetry.receivedAt,
    };
    
    // Parse each field according to the format
    for (const field of format.fields) {
      try {
        switch (field.dataType) {
          case "float":
            parsed[field.name] = readFloat(bytes, field.offset);
            break;
          case "uint8":
            parsed[field.name] = readUint8(bytes, field.offset);
            break;
          case "uint16":
            parsed[field.name] = readUint16(bytes, field.offset);
            break;
          case "bool":
            parsed[field.name] = readBool(bytes, field.offset);
            break;
          default:
            parsed[field.name] = null;
            console.warn(`Unknown data type: ${field.dataType} for field ${field.name}`);
        }
      } catch (error) {
        console.error(`Error parsing field ${field.name}:`, error);
        parsed[field.name] = null;
      }
    }
    
    return parsed;
  },
});

/**
 * Get parsed telemetry data for a time range
 */
export const getParsedTelemetryByTimeRange = query({
  args: {
    startTime: v.number(),
    endTime: v.number(),
    source: v.optional(v.string()),
    fields: v.optional(v.array(v.string())), // Optional: only return specific fields
  },
  handler: async (ctx, args) => {
    // Get telemetry records
    let query = ctx.db.query("telemetry");
    if (args.source) {
      query = query.withIndex("by_source", (q) => q.eq("source", args.source));
    }
    
    const records = await query.collect();
    const filtered = records.filter(
      (r) => r.timestamp >= args.startTime && r.timestamp <= args.endTime
    );
    
    // Get format schema (assume all use same version)
    if (filtered.length === 0) return [];
    
    const format = await ctx.db
      .query("telemetryFormat")
      .withIndex("by_version", (q) => q.eq("formatVersion", filtered[0].formatVersion))
      .first();
    
    if (!format) {
      throw new Error("Format schema not found");
    }
    
    // Parse all records
    const parsed = filtered.map((record) => {
      const bytes = hexToBytes(record.data);
      const data: Record<string, any> = {
        _id: record._id,
        _timestamp: record.timestamp,
        _source: record.source,
      };
      
      // Parse requested fields (or all if not specified)
      const fieldsToParse = args.fields 
        ? format.fields.filter((f) => args.fields?.includes(f.name))
        : format.fields;
      
      for (const field of fieldsToParse) {
        try {
          switch (field.dataType) {
            case "float":
              data[field.name] = readFloat(bytes, field.offset);
              break;
            case "uint8":
              data[field.name] = readUint8(bytes, field.offset);
              break;
            case "uint16":
              data[field.name] = readUint16(bytes, field.offset);
              break;
            case "bool":
              data[field.name] = readBool(bytes, field.offset);
              break;
          }
        } catch (error) {
          data[field.name] = null;
        }
      }
      
      return data;
    });
    
    return parsed;
  },
});
