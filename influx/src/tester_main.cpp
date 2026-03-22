/**
 * main.cpp — SC2 Telemetry Tester (C++ edition)
 *
 * Reads the CSV test dataset and writes records to InfluxDB Cloud using the
 * InfluxDB v2 Line Protocol API.
 *
 * Usage:
 *   ./sc2_telemetry_tester [--batch] [--csv <path>] [--delay <ms>]
 *
 * Flags:
 *   --batch          Send all records in one HTTP batch (default: stream 1/s)
 *   --csv <path>     Path to CSV file (default: ../data/test_telemetry.csv)
 *   --delay <ms>     Stream delay in milliseconds (default: 1000)
 *
 * Required environment variables (set in .env or export):
 *   INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG, INFLUX_BUCKET
 */

#include "CsvParser.h"
#include "InfluxWriter.h"

#include <chrono>
#include <csignal>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

// ─────────────────────────────────────────────────────────────────────────────
//  Graceful shutdown
// ─────────────────────────────────────────────────────────────────────────────

static volatile bool g_running = true;

static void onSignal(int /*sig*/) {
    g_running = false;
}

// ─────────────────────────────────────────────────────────────────────────────
//  .env loader  (key=value, ignores # comments, trims whitespace)
// ─────────────────────────────────────────────────────────────────────────────

static std::string trim(const std::string& s) {
    size_t start = s.find_first_not_of(" \t\r\n\"'");
    if (start == std::string::npos) return "";
    size_t end   = s.find_last_not_of(" \t\r\n\"'");
    return s.substr(start, end - start + 1);
}

static void loadDotEnv(const std::string& path = ".env") {
    std::ifstream file(path);
    if (!file.is_open()) return;  // .env is optional if vars are already exported

    std::string line;
    while (std::getline(file, line)) {
        // Strip comments and blank lines
        size_t hash = line.find('#');
        if (hash != std::string::npos) line = line.substr(0, hash);
        line = trim(line);
        if (line.empty()) continue;

        size_t eq = line.find('=');
        if (eq == std::string::npos) continue;

        std::string key = trim(line.substr(0, eq));
        std::string val = trim(line.substr(eq + 1));
        if (!key.empty()) {
            // Don't overwrite if already in environment
#if defined(_WIN32)
            if (!std::getenv(key.c_str())) _putenv_s(key.c_str(), val.c_str());
#else
            setenv(key.c_str(), val.c_str(), 0 /* no overwrite */);
#endif
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
//  Timestamp helper — nanoseconds since Unix epoch
// ─────────────────────────────────────────────────────────────────────────────

static int64_t nowNs() {
    using namespace std::chrono;
    return static_cast<int64_t>(
        duration_cast<nanoseconds>(
            system_clock::now().time_since_epoch())
        .count());
}

// ─────────────────────────────────────────────────────────────────────────────
//  Argument parsing
// ─────────────────────────────────────────────────────────────────────────────

struct Args {
    bool        batch     = false;
    std::string csvPath   = "../data/test_telemetry.csv";
    int         delayMs   = 1000;
};

static Args parseArgs(int argc, char** argv) {
    Args a;
    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], "--batch") == 0) {
            a.batch = true;
        } else if (std::strcmp(argv[i], "--csv") == 0 && i + 1 < argc) {
            a.csvPath = argv[++i];
        } else if (std::strcmp(argv[i], "--delay") == 0 && i + 1 < argc) {
            a.delayMs = std::stoi(argv[++i]);
        } else {
            std::cerr << "Unknown argument: " << argv[i] << "\n"
                      << "Usage: sc2_telemetry_tester [--batch] [--csv <path>] [--delay <ms>]\n";
            std::exit(1);
        }
    }
    return a;
}

// ─────────────────────────────────────────────────────────────────────────────
//  Stream mode — one record per <delayMs> ms, looping
// ─────────────────────────────────────────────────────────────────────────────

static void runStream(const std::vector<TelemetryRecord>& records,
                      const InfluxWriter& writer,
                      int delayMs) {
    std::cout << "[stream] Sending " << records.size()
              << " records, looping.  Ctrl+C to stop.\n";

    size_t index = 0;
    int    sent  = 0;

    while (g_running) {
        const TelemetryRecord& rec = records[index % records.size()];
        std::string lp = writer.toLineProtocol(rec, nowNs());

        try {
            writer.write(lp);
            ++sent;
            std::cout << "\r[stream] Sent " << sent << " records" << std::flush;
        } catch (const std::exception& ex) {
            std::cerr << "\n[stream] ERROR: " << ex.what() << "\n";
        }

        ++index;
        std::this_thread::sleep_for(std::chrono::milliseconds(delayMs));
    }

    std::cout << "\n[stream] Stopped after " << sent << " records.\n";
}

// ─────────────────────────────────────────────────────────────────────────────
//  Batch mode — all records in one HTTP request
// ─────────────────────────────────────────────────────────────────────────────

static void runBatch(const std::vector<TelemetryRecord>& records,
                     const InfluxWriter& writer) {
    std::cout << "[batch] Building " << records.size() << " line-protocol lines...\n";

    std::vector<std::string> lines;
    lines.reserve(records.size());

    // Space timestamps 1 second apart starting from now
    int64_t ts = nowNs();
    const int64_t step = 1'000'000'000LL;  // 1 second in nanoseconds

    for (const auto& rec : records) {
        lines.push_back(writer.toLineProtocol(rec, ts));
        ts += step;
    }

    std::cout << "[batch] Sending " << lines.size() << " records in one request...\n";
    writer.writeBatch(lines);
    std::cout << "[batch] Done.\n";
}

// ─────────────────────────────────────────────────────────────────────────────
//  main
// ─────────────────────────────────────────────────────────────────────────────

int main(int argc, char** argv) {
    // Register signal handlers
    std::signal(SIGINT,  onSignal);
    std::signal(SIGTERM, onSignal);

    // Load .env (from the directory where the binary is run)
    loadDotEnv(".env");
    // Also try parent directory (for running from build/)
    loadDotEnv("../.env");

    Args args = parseArgs(argc, argv);

    // ── Parse CSV ────────────────────────────────────────────────────────────
    std::cout << "[init] Parsing CSV: " << args.csvPath << "\n";
    std::vector<TelemetryRecord> records;
    try {
        records = CsvParser::parse(args.csvPath);
    } catch (const std::exception& ex) {
        std::cerr << "[error] Failed to parse CSV: " << ex.what() << "\n";
        return 1;
    }
    std::cout << "[init] Parsed " << records.size() << " records.\n";

    if (records.empty()) {
        std::cerr << "[error] CSV contained no records.\n";
        return 1;
    }

    // ── Init InfluxDB writer ─────────────────────────────────────────────────
    InfluxWriter writer;
    try {
        // InfluxWriter constructor throws if env vars are missing
    } catch (const std::exception& ex) {
        std::cerr << "[error] InfluxWriter init failed: " << ex.what() << "\n";
        return 1;
    }

    std::cout << "[init] InfluxDB configured.  Bucket: "
              << (std::getenv("INFLUX_BUCKET") ? std::getenv("INFLUX_BUCKET") : "?")
              << "\n";

    // ── Run mode ─────────────────────────────────────────────────────────────
    if (args.batch) {
        try {
            runBatch(records, writer);
        } catch (const std::exception& ex) {
            std::cerr << "[error] Batch write failed: " << ex.what() << "\n";
            return 1;
        }
    } else {
        runStream(records, writer, args.delayMs);
    }

    return 0;
}
