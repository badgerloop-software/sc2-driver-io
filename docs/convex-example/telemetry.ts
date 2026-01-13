/**
 * Convex Mutations and Queries for SC2 Telemetry
 * 
 * Save this file as: convex/telemetry.ts
 * Deploy: npx convex deploy
 */

import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

/**
 * Store raw telemetry data from the car
 * Called via HTTP API from C++ telemetry system
 */
export const storeTelemetry = mutation({
  args: {
    timestamp: v.number(),
    data: v.string(),           // Hex-encoded bytes (sc1-data-format structure)
    dataSize: v.number(),
    source: v.string(),
    dataFormat: v.string(),     // Should be "sc1-data-format"
    formatVersion: v.string(),  // e.g., "1.0"
    receivedAt: v.number(),
  },
  handler: async (ctx, args) => {
    // Validate data
    if (args.dataSize <= 0 || args.dataSize > 10000) {
      throw new Error("Invalid data size");
    }
    
    if (args.data.length !== args.dataSize * 2) {
      throw new Error("Data length mismatch with dataSize");
    }
    
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
    
    console.log(`Stored telemetry: ${args.dataSize} bytes from ${args.source} (format: ${args.dataFormat} v${args.formatVersion})`);
    
    return { success: true, id };
  },
});

/**
 * Get recent telemetry records
 */
export const getRecentTelemetry = query({
  args: {
    limit: v.optional(v.number()),
    source: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const limit = args.limit ?? 100;
    
    let query = ctx.db.query("telemetry");
    
    if (args.source) {
      query = query.withIndex("by_source", (q) => q.eq("source", args.source));
    }
    
    return await query
      .order("desc")
      .take(limit);
  },
});

/**
 * Get telemetry data within a time range
 */
export const getTelemetryByTimeRange = query({
  args: {
    startTime: v.number(),
    endTime: v.number(),
    source: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    let query = ctx.db.query("telemetry");
    
    if (args.source) {
      query = query.withIndex("by_source", (q) => q.eq("source", args.source));
    }
    
    const results = await query.collect();
    
    // Filter by timestamp range
    return results.filter(
      (record) => record.timestamp >= args.startTime && record.timestamp <= args.endTime
    );
  },
});

/**
 * Get statistics about stored telemetry
 */
export const getTelemetryStats = query({
  args: {},
  handler: async (ctx, args) => {
    const records = await ctx.db.query("telemetry").collect();
    
    if (records.length === 0) {
      return {
        totalRecords: 0,
        totalBytes: 0,
        oldestTimestamp: 0,
        newestTimestamp: 0,
        sources: [],
      };
    }
    
    const totalBytes = records.reduce((sum, r) => sum + r.dataSize, 0);
    const timestamps = records.map((r) => r.timestamp);
    const sources = [...new Set(records.map((r) => r.source))];
    
    return {
      totalRecords: records.length,
      totalBytes,
      oldestTimestamp: Math.min(...timestamps),
      newestTimestamp: Math.max(...timestamps),
      sources,
    };
  },
});

/**
 * Delete old telemetry data (cleanup function)
 * Call this periodically to keep storage manageable
 */
export const cleanupOldTelemetry = mutation({
  args: {
    olderThanMs: v.number(),  // Delete records older than this timestamp
  },
  handler: async (ctx, args) => {
    const oldRecords = await ctx.db
      .query("telemetry")
      .withIndex("by_timestamp")
      .filter((q) => q.lt(q.field("timestamp"), args.olderThanMs))
      .collect();
    
    let deletedCount = 0;
    for (const record of oldRecords) {
      await ctx.db.delete(record._id);
      deletedCount++;
    }
    
    console.log(`Cleaned up ${deletedCount} old telemetry records`);
    
    return { deletedCount };
  },
});
