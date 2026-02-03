-- Supabase SQL Schema for SC2 Telemetry
-- Run this in your Supabase SQL Editor to create the required tables

-- Enable the uuid-ossp extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Main telemetry table for storing all telemetry data
CREATE TABLE IF NOT EXISTS telemetry (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    timestamp BIGINT NOT NULL,
    source VARCHAR(50) DEFAULT 'telemetry',
    received_at BIGINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Dynamic telemetry fields (add your specific fields from format.json)
    -- These will be added automatically when data is inserted via REST API
    -- Supabase's schemaless JSONB approach is also an option
    
    -- Common telemetry fields (examples - adjust based on your format.json)
    speed REAL,
    soc REAL,
    pack_voltage REAL,
    pack_current REAL,
    motor_rpm REAL,
    motor_temp REAL,
    controller_temp REAL,
    battery_temp_max REAL,
    battery_temp_min REAL,
    gps_lat REAL,
    gps_lon REAL,
    gps_speed REAL,
    
    -- Index for efficient time-based queries
    CONSTRAINT telemetry_timestamp_check CHECK (timestamp > 0)
);

-- Create index for timestamp queries (most common query pattern)
CREATE INDEX IF NOT EXISTS idx_telemetry_timestamp ON telemetry(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_source ON telemetry(source);
CREATE INDEX IF NOT EXISTS idx_telemetry_created_at ON telemetry(created_at DESC);

-- Schema metadata table for storing format.json information
CREATE TABLE IF NOT EXISTS telemetry_schema (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    format_version VARCHAR(20) NOT NULL,
    name VARCHAR(100) NOT NULL,
    num_bytes INTEGER NOT NULL,
    data_type VARCHAR(20) NOT NULL,
    units VARCHAR(50),
    nominal_min REAL,
    nominal_max REAL,
    category VARCHAR(50),
    "offset" INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_telemetry_schema_name ON telemetry_schema(name);
CREATE INDEX IF NOT EXISTS idx_telemetry_schema_version ON telemetry_schema(format_version);

-- Enable Row Level Security (RLS)
ALTER TABLE telemetry ENABLE ROW LEVEL SECURITY;
ALTER TABLE telemetry_schema ENABLE ROW LEVEL SECURITY;

-- Policy: Allow anonymous inserts for telemetry (from the car)
CREATE POLICY "Allow anonymous insert" ON telemetry
    FOR INSERT
    WITH CHECK (true);

-- Policy: Allow authenticated users to read telemetry
CREATE POLICY "Allow authenticated read" ON telemetry
    FOR SELECT
    USING (true);

-- Policy: Allow read access to schema
CREATE POLICY "Allow schema read" ON telemetry_schema
    FOR SELECT
    USING (true);

-- Policy: Allow insert to schema (for upload script)
CREATE POLICY "Allow schema insert" ON telemetry_schema
    FOR INSERT
    WITH CHECK (true);

-- Policy: Allow delete from schema (for schema updates)
CREATE POLICY "Allow schema delete" ON telemetry_schema
    FOR DELETE
    USING (true);

-- Function to get latest telemetry
CREATE OR REPLACE FUNCTION get_latest_telemetry(limit_count INTEGER DEFAULT 100)
RETURNS SETOF telemetry
LANGUAGE sql
STABLE
AS $$
    SELECT * FROM telemetry
    ORDER BY timestamp DESC
    LIMIT limit_count;
$$;

-- Function to get telemetry by time range
CREATE OR REPLACE FUNCTION get_telemetry_by_time_range(
    start_time BIGINT,
    end_time BIGINT
)
RETURNS SETOF telemetry
LANGUAGE sql
STABLE
AS $$
    SELECT * FROM telemetry
    WHERE timestamp >= start_time AND timestamp <= end_time
    ORDER BY timestamp ASC;
$$;

-- Real-time subscription setup
-- Enable real-time for the telemetry table
-- Note: Run this in the Supabase Dashboard under Database > Replication
-- ALTER PUBLICATION supabase_realtime ADD TABLE telemetry;

COMMENT ON TABLE telemetry IS 'Stores all telemetry data from the SC2 solar car';
COMMENT ON TABLE telemetry_schema IS 'Stores the format.json schema for parsing telemetry data';
COMMENT ON COLUMN telemetry.timestamp IS 'Unix timestamp in milliseconds from the car';
COMMENT ON COLUMN telemetry.received_at IS 'Unix timestamp when data was received by the server';
COMMENT ON COLUMN telemetry.source IS 'Identifier for the data source';
