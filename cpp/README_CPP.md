# SC2 Telemetry Tester — C++ Edition

C++ rewrite of the telemetry upload tool.  
Reads a CSV test dataset and streams or batch-uploads records to **InfluxDB Cloud** using the v2 Line Protocol HTTP API.  
Mirrors what the real Raspberry Pi (CAN bus → InfluxDB) implementation will do.

---

## Directory Structure

```
cpp/
├── CMakeLists.txt          # Build configuration (CMake 3.15+, C++17)
├── README_CPP.md           # This file
├── include/
│   ├── TelemetryRecord.h   # Typed struct — all 140+ signals
│   ├── CsvParser.h         # CSV → vector<TelemetryRecord>
│   └── InfluxWriter.h      # Line Protocol serialiser + libcurl HTTP POST
├── src/
│   ├── CsvParser.cpp
│   ├── InfluxWriter.cpp
│   └── main.cpp            # CLI entry point (stream & batch modes)
└── tests/
    └── test_main.cpp       # 10 unit tests (no external framework)
```

---

## Prerequisites

| Tool | Version |
|------|---------|
| CMake | ≥ 3.15 |
| C++ compiler | GCC 9+, Clang 10+, or Apple Clang 13+ |
| libcurl | system package |

### Install libcurl

**macOS (Homebrew)**
```bash
brew install curl
```

**Ubuntu / Debian**
```bash
sudo apt-get install libcurl4-openssl-dev
```

**Raspberry Pi OS (same as Debian)**
```bash
sudo apt-get install libcurl4-openssl-dev
```

---

## Build

```bash
# From the sc2-telemetry-tester/cpp directory:
mkdir -p build && cd build
cmake ..
make -j$(nproc)
```

This produces two binaries in `build/`:

| Binary | Purpose |
|--------|---------|
| `sc2_telemetry_tester` | Main upload tool |
| `sc2_telemetry_tests`  | Unit test runner |

---

## Configuration

Set the following environment variables **or** place them in a `.env` file in the
directory from which you run the binary:

```
INFLUX_URL=https://us-east-1-1.aws.cloud2.influxdata.com
INFLUX_TOKEN=<your-write-token>
INFLUX_ORG=307f8812c3d9b017
INFLUX_BUCKET=sc2-telemetry
```

Copy `.env.example` as a starting point:

```bash
cp ../.env.example ../.env
# then fill in your token
```

---

## Usage

### Stream mode (default — 1 record/second, loops)

```bash
cd build
./sc2_telemetry_tester
```

```bash
# Custom CSV and 500 ms interval
./sc2_telemetry_tester --csv ../../data/test_telemetry.csv --delay 500
```

### Batch mode (all records in one HTTP request)

```bash
./sc2_telemetry_tester --batch
```

### Full flag reference

```
./sc2_telemetry_tester [--batch] [--csv <path>] [--delay <ms>]

  --batch          Send all CSV records in a single HTTP POST
  --csv <path>     Path to CSV file (default: ../data/test_telemetry.csv)
  --delay <ms>     Stream inter-record delay in milliseconds (default: 1000)
```

Press **Ctrl+C** to stop stream mode gracefully.

---

## Running the Tests

```bash
cd build
./sc2_telemetry_tests
```

Or via CTest:

```bash
cd build
ctest --output-on-failure
```

### Test coverage

| # | Test | What it verifies |
|---|------|-----------------|
| 1 | Default values | `TelemetryRecord` initialises to safe defaults |
| 2 | LP format | Measurement name prefix, no double commas, timestamp suffix |
| 3 | Bool encoding | `eco=true`, `foot_brake=false` — not `1`/`0` |
| 4 | Float encoding | No integer `i` suffix on any numeric field |
| 5 | Timestamp omission | `timestampNs=0` → no trailing space + number |
| 6 | Missing CSV file | `CsvParser::parse()` throws `std::runtime_error` |
| 7 | Inline CSV parsing | Correct field mapping, unknown columns silently ignored |
| 8 | Empty CSV file | Returns empty `vector<TelemetryRecord>` |
| 9 | Batch join | Two LP lines joined by `\n`, no trailing newline |
| 10 | Missing env var | `InfluxWriter` constructor throws when `INFLUX_URL` unset |

---

## Line Protocol Design

All numeric values are written as **floats** (no `i` integer suffix).  
This avoids InfluxDB schema conflicts that arise when the same field is
occasionally a whole number in one record and a fraction in another.

Example line:
```
sc2_telemetry speed=42.500000,soc=87.100006,pack_voltage=100.250000,eco=true,foot_brake=false,... 1700000000000000000
```

---

## Porting to Raspberry Pi

On the real car the CAN bus reader will:

1. Decode each CAN frame into the equivalent `TelemetryRecord` field(s).
2. Call `InfluxWriter::toLineProtocol(record, nowNs())`.
3. Accumulate N lines then call `InfluxWriter::writeBatch(lines)` every ~1 s.

Only `CsvParser` needs to be replaced; `TelemetryRecord`, `InfluxWriter`, and the
build system are reusable as-is.
