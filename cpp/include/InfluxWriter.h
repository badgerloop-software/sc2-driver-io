#pragma once
#include <string>
#include "TelemetryRecord.h"

/**
 * InfluxWriter
 *
 * Converts TelemetryRecord structs to InfluxDB Line Protocol strings and
 * POSTs them to InfluxDB Cloud via libcurl.
 *
 * All numeric values are written as floats (no integer 'i' suffix) to prevent
 * schema conflicts when a field contains mixed whole/fractional values across
 * different records.
 *
 * Connection parameters are read from environment variables:
 *   INFLUX_URL    – e.g. https://us-east-1-1.aws.cloud2.influxdata.com
 *   INFLUX_TOKEN  – All-access or write token
 *   INFLUX_ORG    – Organisation ID (hex string)
 *   INFLUX_BUCKET – Bucket name, e.g. sc2-telemetry
 */
class InfluxWriter {
public:
    /**
     * Load connection parameters from environment variables.
     * @throws std::runtime_error if any required variable is missing.
     */
    explicit InfluxWriter();

    /**
     * Convert @p rec to a single InfluxDB Line Protocol line.
     *
     * @param rec         The telemetry record to encode.
     * @param timestampNs Nanosecond-precision Unix timestamp.
     *                    Pass 0 to omit (InfluxDB uses server time).
     * @returns A line-protocol string, e.g.:
     *          sc2_telemetry speed=42.3,soc=87.1 1700000000000000000
     */
    std::string toLineProtocol(const TelemetryRecord& rec,
                               int64_t timestampNs = 0) const;

    /**
     * HTTP POST a single Line Protocol string to InfluxDB.
     *
     * @throws std::runtime_error on curl/HTTP error or non-2xx response.
     */
    void write(const std::string& lineProtocol) const;

    /**
     * HTTP POST multiple Line Protocol lines (one per element) in a single
     * request.  Lines are joined with '\n'.
     */
    void writeBatch(const std::vector<std::string>& lines) const;

private:
    std::string url_;
    std::string token_;
    std::string org_;
    std::string bucket_;

    // Perform the actual HTTP POST; throws on failure.
    void httpPost(const std::string& body) const;
};
