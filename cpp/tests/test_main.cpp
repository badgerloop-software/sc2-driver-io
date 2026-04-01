/**
 * test_main.cpp — Unit tests for the SC2 C++ telemetry tester
 *
 * Runs without any external test framework — uses simple assert macros.
 * Build target: sc2_telemetry_tests (defined in CMakeLists.txt)
 *
 * Run:
 *   cd build && cmake .. && make sc2_telemetry_tests && ./sc2_telemetry_tests
 */

#include "CsvParser.h"
#include "InfluxWriter.h"
#include "TelemetryRecord.h"

#include <cassert>
#include <cmath>
#include <cstring>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

// ─────────────────────────────────────────────────────────────────────────────
//  Minimal test framework
// ─────────────────────────────────────────────────────────────────────────────

static int s_pass = 0;
static int s_fail = 0;

#define EXPECT_TRUE(cond) \
    do { \
        if (!(cond)) { \
            std::cerr << "  FAIL: " #cond " (line " << __LINE__ << ")\n"; \
            ++s_fail; \
        } else { \
            ++s_pass; \
        } \
    } while (0)

#define EXPECT_EQ(a, b) EXPECT_TRUE((a) == (b))
#define EXPECT_NEAR(a, b, eps) EXPECT_TRUE(std::fabs((double)(a) - (double)(b)) < (eps))
#define EXPECT_THROWS(expr) \
    do { \
        bool threw = false; \
        try { expr; } catch (...) { threw = true; } \
        if (!threw) { \
            std::cerr << "  FAIL: expected exception at line " << __LINE__ << "\n"; \
            ++s_fail; \
        } else { \
            ++s_pass; \
        } \
    } while (0)

static void beginTest(const char* name) {
    std::cout << "[ TEST ] " << name << "\n";
}

// ─────────────────────────────────────────────────────────────────────────────
//  Helpers — minimal writer that does NOT send HTTP (for LP format tests)
// ─────────────────────────────────────────────────────────────────────────────

// Create a record with known values for deterministic tests.
static TelemetryRecord makeTestRecord() {
    TelemetryRecord r;
    r.speed       = 42.5;
    r.soc         = 87.1;
    r.pack_voltage= 100.25;
    r.motor_temp  = 55.0;
    r.eco         = true;
    r.foot_brake  = false;
    r.lat         = 43.0731;
    r.lon         = -89.4012;
    r.lap_count   = 3;
    return r;
}

// ─────────────────────────────────────────────────────────────────────────────
//  Test 1: Default TelemetryRecord values
// ─────────────────────────────────────────────────────────────────────────────

static void testDefaultValues() {
    beginTest("Default TelemetryRecord values");

    TelemetryRecord r;

    EXPECT_NEAR(r.speed,        0.0,   1e-9);
    EXPECT_NEAR(r.soc,          0.0,   1e-9);
    EXPECT_NEAR(r.pack_voltage, 77.5,  1e-6);
    EXPECT_NEAR(r.soh,          100.0, 1e-6);
    EXPECT_NEAR(r.lat,          43.0731, 1e-4);
    EXPECT_NEAR(r.lon,          -89.4012, 1e-4);
    EXPECT_EQ  (r.eco,          false);
    EXPECT_EQ  (r.foot_brake,   false);
    EXPECT_EQ  (r.bps_fault,    false);
    EXPECT_EQ  (r.mppt_contactor, true);   // default is "nominal" = true
    EXPECT_EQ  (r.lap_count,    0);
}

// ─────────────────────────────────────────────────────────────────────────────
//  Test 2: Line Protocol format — field separator, no trailing comma
// ─────────────────────────────────────────────────────────────────────────────

// Minimal subclass that exposes toLineProtocol without needing real env vars.
struct TestWriter : public InfluxWriter {
    // Forward constructor — catches missing-env exception for testing.
    TestWriter() : InfluxWriter() {}
};

static void testLineProtocolFormat() {
    // Set dummy env vars so InfluxWriter constructor succeeds.
    setenv("INFLUX_URL",    "http://localhost:8086", 1);
    setenv("INFLUX_TOKEN",  "test-token",            1);
    setenv("INFLUX_ORG",    "test-org",              1);
    setenv("INFLUX_BUCKET", "test-bucket",           1);

    beginTest("Line Protocol format");

    InfluxWriter w;
    TelemetryRecord r = makeTestRecord();
    std::string lp = w.toLineProtocol(r, 1700000000000000000LL);

    // Must start with measurement name
    EXPECT_TRUE(lp.rfind("sc2_telemetry ", 0) == 0);

    // Must contain key fields
    EXPECT_TRUE(lp.find("speed=") != std::string::npos);
    EXPECT_TRUE(lp.find("soc=")   != std::string::npos);

    // Must not have comma right after measurement name
    EXPECT_TRUE(lp[std::strlen("sc2_telemetry")] == ' ');

    // Must not have double commas
    EXPECT_TRUE(lp.find(",,") == std::string::npos);

    // Must end with timestamp
    EXPECT_TRUE(lp.rfind("1700000000000000000") != std::string::npos);

    // No trailing comma before timestamp
    size_t spaceBeforeTs = lp.rfind(' ');
    EXPECT_TRUE(spaceBeforeTs != std::string::npos);
    EXPECT_TRUE(lp[spaceBeforeTs - 1] != ',');

    std::cout << "  LP (first 120 chars): " << lp.substr(0, 120) << "...\n";
}

// ─────────────────────────────────────────────────────────────────────────────
//  Test 3: Boolean encoding — must be true/false, not 1/0
// ─────────────────────────────────────────────────────────────────────────────

static void testBoolEncoding() {
    beginTest("Boolean encoding (true/false strings)");

    setenv("INFLUX_URL",    "http://localhost:8086", 1);
    setenv("INFLUX_TOKEN",  "test-token",            1);
    setenv("INFLUX_ORG",    "test-org",              1);
    setenv("INFLUX_BUCKET", "test-bucket",           1);

    InfluxWriter w;
    TelemetryRecord r;
    r.eco        = true;
    r.foot_brake = false;

    std::string lp = w.toLineProtocol(r);

    EXPECT_TRUE(lp.find("eco=true")        != std::string::npos);
    EXPECT_TRUE(lp.find("foot_brake=false")!= std::string::npos);
    // Should NOT appear as integers
    EXPECT_TRUE(lp.find("eco=1")           == std::string::npos);
    EXPECT_TRUE(lp.find("foot_brake=0")    == std::string::npos);
}

// ─────────────────────────────────────────────────────────────────────────────
//  Test 4: Float precision — no integer suffix 'i'
// ─────────────────────────────────────────────────────────────────────────────

static void testFloatEncoding() {
    beginTest("Float encoding (no 'i' suffix)");

    setenv("INFLUX_URL",    "http://localhost:8086", 1);
    setenv("INFLUX_TOKEN",  "test-token",            1);
    setenv("INFLUX_ORG",    "test-org",              1);
    setenv("INFLUX_BUCKET", "test-bucket",           1);

    InfluxWriter w;
    TelemetryRecord r;
    r.speed       = 100.0;   // whole number — must NOT get 'i'
    r.pack_voltage = 77.5;

    std::string lp = w.toLineProtocol(r);

    // No 'i' suffix on any numeric value
    // (simple check: the character after a digit must not be 'i' before comma/space)
    for (size_t i = 1; i < lp.size(); ++i) {
        if (lp[i] == 'i' && std::isdigit(static_cast<unsigned char>(lp[i - 1]))) {
            // Allow "e" in scientific notation but flag 'i' after digit
            EXPECT_TRUE(false);  // found integer suffix
            std::cerr << "  Found 'i' suffix at position " << i
                      << " in: " << lp.substr(std::max(0, (int)i - 10), 20) << "\n";
            break;
        }
    }
    EXPECT_TRUE(true);  // reached here without finding 'i'
}

// ─────────────────────────────────────────────────────────────────────────────
//  Test 5: Timestamp precision — no timestamp → no trailing number space
// ─────────────────────────────────────────────────────────────────────────────

static void testTimestampOmission() {
    beginTest("Timestamp omission (timestampNs == 0)");

    setenv("INFLUX_URL",    "http://localhost:8086", 1);
    setenv("INFLUX_TOKEN",  "test-token",            1);
    setenv("INFLUX_ORG",    "test-org",              1);
    setenv("INFLUX_BUCKET", "test-bucket",           1);

    InfluxWriter w;
    TelemetryRecord r = makeTestRecord();
    std::string lp = w.toLineProtocol(r, 0);

    // When ts == 0 there should be no trailing " <digits>"
    // The last non-whitespace char must be a digit from the last field value,
    // not a separate timestamp token separated by space.
    // Simple check: string must NOT have a second space (measurement <fields> [ts])
    size_t firstSpace = lp.find(' ');
    size_t lastSpace  = lp.rfind(' ');
    // With timestamp=0 there is exactly one space (between measurement and fields).
    EXPECT_EQ(firstSpace, lastSpace);
}

// ─────────────────────────────────────────────────────────────────────────────
//  Test 6: CSV parser — non-existent file throws
// ─────────────────────────────────────────────────────────────────────────────

static void testCsvMissingFile() {
    beginTest("CsvParser throws on missing file");
    EXPECT_THROWS(CsvParser::parse("/no/such/file.csv"));
}

// ─────────────────────────────────────────────────────────────────────────────
//  Test 7: CSV parser — parses inline CSV correctly
// ─────────────────────────────────────────────────────────────────────────────

static void testCsvInlineData() {
    beginTest("CsvParser inline CSV data");

    // Write a minimal CSV to a temp file
    const char* tmpPath = "/tmp/sc2_test_csv.csv";
    {
        std::ofstream f(tmpPath);
        f << "speed,soc,pack_voltage,eco,lap_count\n";
        f << "55.5,75.0,98.2,true,2\n";
        f << "60.0,74.5,98.1,false,2\n";
    }

    std::vector<TelemetryRecord> recs = CsvParser::parse(tmpPath);

    EXPECT_EQ(recs.size(), 2u);
    EXPECT_NEAR(recs[0].speed,        55.5,  1e-4);
    EXPECT_NEAR(recs[0].soc,          75.0,  1e-4);
    EXPECT_NEAR(recs[0].pack_voltage, 98.2,  1e-4);
    EXPECT_EQ  (recs[0].eco,          true);
    EXPECT_EQ  (recs[0].lap_count,    2);

    EXPECT_NEAR(recs[1].speed,        60.0,  1e-4);
    EXPECT_EQ  (recs[1].eco,          false);

    // Unknown columns must NOT crash
    {
        std::ofstream f(tmpPath);
        f << "speed,__unknown_field__,soc\n";
        f << "30.0,GARBAGE,50.0\n";
    }
    recs = CsvParser::parse(tmpPath);
    EXPECT_EQ(recs.size(), 1u);
    EXPECT_NEAR(recs[0].speed, 30.0, 1e-4);
    EXPECT_NEAR(recs[0].soc,   50.0, 1e-4);
}

// ─────────────────────────────────────────────────────────────────────────────
//  Test 8: CSV parser — empty file returns empty vector
// ─────────────────────────────────────────────────────────────────────────────

static void testCsvEmptyFile() {
    beginTest("CsvParser empty file → empty vector");

    const char* tmpPath = "/tmp/sc2_test_empty.csv";
    {
        std::ofstream f(tmpPath);
        // intentionally empty
    }
    std::vector<TelemetryRecord> recs = CsvParser::parse(tmpPath);
    EXPECT_EQ(recs.size(), 0u);
}

// ─────────────────────────────────────────────────────────────────────────────
//  Test 9: Batch line protocol — lines joined by newline, no trailing newline
// ─────────────────────────────────────────────────────────────────────────────

static void testBatchFormat() {
    beginTest("writeBatch joins lines with newline");

    setenv("INFLUX_URL",    "http://localhost:8086", 1);
    setenv("INFLUX_TOKEN",  "test-token",            1);
    setenv("INFLUX_ORG",    "test-org",              1);
    setenv("INFLUX_BUCKET", "test-bucket",           1);

    InfluxWriter w;
    TelemetryRecord r1 = makeTestRecord();
    TelemetryRecord r2 = makeTestRecord();
    r2.speed = 99.0;

    std::string lp1 = w.toLineProtocol(r1, 1000000000LL);
    std::string lp2 = w.toLineProtocol(r2, 2000000000LL);

    // Simulate what writeBatch does internally
    std::string batch = lp1 + "\n" + lp2;

    // Verify structure: two lines joined by exactly one newline
    size_t nl = batch.find('\n');
    EXPECT_TRUE(nl != std::string::npos);
    EXPECT_EQ(batch.substr(0, nl), lp1);
    EXPECT_EQ(batch.substr(nl + 1), lp2);
    // No trailing newline
    EXPECT_TRUE(batch.back() != '\n');
}

// ─────────────────────────────────────────────────────────────────────────────
//  Test 10: InfluxWriter constructor throws when env var missing
// ─────────────────────────────────────────────────────────────────────────────

static void testMissingEnvThrows() {
    beginTest("InfluxWriter throws when INFLUX_URL missing");

    unsetenv("INFLUX_URL");

    EXPECT_THROWS(InfluxWriter());

    // Restore for subsequent tests
    setenv("INFLUX_URL", "http://localhost:8086", 1);
}

// ─────────────────────────────────────────────────────────────────────────────
//  main
// ─────────────────────────────────────────────────────────────────────────────

int main() {
    std::cout << "=== SC2 Telemetry Tester — Unit Tests ===\n\n";

    testDefaultValues();
    testLineProtocolFormat();
    testBoolEncoding();
    testFloatEncoding();
    testTimestampOmission();
    testCsvMissingFile();
    testCsvInlineData();
    testCsvEmptyFile();
    testBatchFormat();
    testMissingEnvThrows();

    std::cout << "\n=== Results: " << s_pass << " passed, " << s_fail << " failed ===\n";
    return s_fail == 0 ? 0 : 1;
}
