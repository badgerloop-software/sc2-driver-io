import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

// Mutation to store telemetry data
// Accepts a flexible object with all telemetry fields
export const storeTelemetry = mutation({
  args: v.any(), // Accept any object structure matching sc1-data-format
  handler: async (ctx, telemetryData) => {
    // Validate required metadata fields
    if (typeof telemetryData.timestamp !== 'number') {
      throw new Error("timestamp is required and must be a number");
    }
    if (typeof telemetryData.source !== 'string') {
      throw new Error("source is required and must be a string");
    }
    if (typeof telemetryData.receivedAt !== 'number') {
      throw new Error("receivedAt is required and must be a number");
    }
    
    // Store the entire object directly
    const id = await ctx.db.insert("telemetry", telemetryData);
    return id;
  },
});

// Query to get recent telemetry (last N records)
export const getRecentTelemetry = query({
  args: { limit: v.optional(v.number()) },
  handler: async (ctx, args) => {
    const limit = args.limit ?? 100;
    return await ctx.db
      .query("telemetry")
      .order("desc")
      .take(limit);
  },
});

// Query to get telemetry by timestamp range
export const getTelemetryByTimeRange = query({
  args: {
    startTime: v.number(),
    endTime: v.number(),
  },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("telemetry")
      .withIndex("by_timestamp", (q) =>
        q.gte("timestamp", args.startTime).lte("timestamp", args.endTime)
      )
      .collect();
  },
});

// Query to get telemetry by source
export const getTelemetryBySource = query({
  args: {
    source: v.string(),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const limit = args.limit ?? 100;
    return await ctx.db
      .query("telemetry")
      .withIndex("by_source", (q) => q.eq("source", args.source))
      .order("desc")
      .take(limit);
  },
});

// Query to get specific telemetry fields over time
// Useful for plotting specific metrics
export const getTelemetryFields = query({
  args: {
    fields: v.array(v.string()),
    startTime: v.optional(v.number()),
    endTime: v.optional(v.number()),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const limit = args.limit ?? 1000;
    
    let records;
    if (args.startTime !== undefined && args.endTime !== undefined) {
      records = await ctx.db
        .query("telemetry")
        .withIndex("by_timestamp", (q) =>
          q.gte("timestamp", args.startTime!).lte("timestamp", args.endTime!)
        )
        .take(limit);
    } else {
      records = await ctx.db
        .query("telemetry")
        .order("desc")
        .take(limit);
    }
    
    // Project only requested fields
    return records.map((record) => {
      const projected: any = {
        timestamp: record.timestamp,
      };
      for (const field of args.fields) {
        projected[field] = (record as any)[field];
      }
      return projected;
    });
  },
});
