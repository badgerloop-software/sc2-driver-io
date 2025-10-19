cmake_minimum_required(VERSION 3.5)
project(sc2-driver-io)

# Set C++ standard to C++20
set(CMAKE_CXX_STANDARD 20)

# Add shared sources to build
set(SOURCES
        ${SOURCES}
        backend/backendProcesses.cpp
        main.cpp
        DataProcessor/dataUnpacker.cpp
        backend/dataFetcher.cpp
        backend/telemetrylib/tcp.cpp
        backend/telemetrylib/telemetry.cpp
        backend/telemetrylib/sql.cpp
        gps/gps.cpp
        3rdparty/serial/serialib.cpp
        Config.cpp
        )

# Add the header files
set(HEADERS
        ${HEADERS}
        DataProcessor/dataUnpacker.h
        backend/dataFetcher.h
        backend/backendProcesses.h
        backend/telemetrylib/telemetry.h
        backend/telemetrylib/DTI.h
        gps/gps.h
        3rdparty/serial/serialib.h
        Config.h
        )

# Add the executable target
add_executable(${PROJECT_NAME} ${SOURCES} ${HEADERS})

# Link against standard libraries
# Note: pthread linking will be platform-specific
if(UNIX)
    target_link_libraries(${PROJECT_NAME} PRIVATE pthread)
endif()

target_include_directories(${PROJECT_NAME} PRIVATE ./)
