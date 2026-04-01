cmake_minimum_required(VERSION 3.15)
project(sc2_telemetry_tester CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# ── Compiler warnings ─────────────────────────────────────────────────────────
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang|AppleClang")
    add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# ── Find libcurl ──────────────────────────────────────────────────────────────
find_package(CURL REQUIRED)

# ── Shared library of business-logic sources ─────────────────────────────────
# (Lets both the main binary and the test binary link the same object files)
add_library(sc2_core STATIC
    src/CsvParser.cpp
    src/InfluxWriter.cpp
)
target_include_directories(sc2_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(sc2_core PUBLIC CURL::libcurl)

# ── Main executable ───────────────────────────────────────────────────────────
add_executable(sc2_telemetry_tester src/main.cpp)
target_link_libraries(sc2_telemetry_tester PRIVATE sc2_core)

# ── Test executable ───────────────────────────────────────────────────────────
add_executable(sc2_telemetry_tests tests/test_main.cpp)
target_link_libraries(sc2_telemetry_tests PRIVATE sc2_core)

# ── CTest integration (optional: run with `ctest`) ────────────────────────────
enable_testing()
add_test(NAME unit_tests COMMAND sc2_telemetry_tests)

# ── Build type defaults ───────────────────────────────────────────────────────
if(NOT CMAKE_BUILD_TYPE)
    set(CMAKE_BUILD_TYPE Release)
endif()

message(STATUS "Build type : ${CMAKE_BUILD_TYPE}")
message(STATUS "C++ std    : ${CMAKE_CXX_STANDARD}")
message(STATUS "libcurl    : ${CURL_VERSION_STRING}")
