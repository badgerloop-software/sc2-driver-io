#pragma once
#include <string>
#include <vector>
#include "TelemetryRecord.h"

/**
 * CsvParser
 *
 * Reads a CSV file whose columns match the signal names in data_format.json
 * and returns a vector of TelemetryRecord objects.
 *
 * The first row of the CSV must be a header row containing field names.
 * Missing or empty values are silently skipped (field retains its default).
 */
class CsvParser {
public:
    /**
     * Parse the CSV file at @p filePath.
     *
     * @throws std::runtime_error if the file cannot be opened.
     * @returns A vector of fully-populated TelemetryRecord structs.
     */
    static std::vector<TelemetryRecord> parse(const std::string& filePath);

private:
    // Split a single CSV line respecting quoted fields.
    static std::vector<std::string> splitLine(const std::string& line);

    // Apply one (header, value) pair to a TelemetryRecord.
    static void applyField(TelemetryRecord& rec,
                           const std::string& name,
                           const std::string& value);

    // Helpers
    static double  toDouble(const std::string& s, double  fallback = 0.0);
    static bool    toBool  (const std::string& s, bool    fallback = false);
    static int64_t toInt64 (const std::string& s, int64_t fallback = 0);
};
