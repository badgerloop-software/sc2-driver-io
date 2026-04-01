cmake_minimum_required(VERSION 3.15)
project(sc2-driver-io)

# Set C++ standard to C++20
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Add shared sources to build
set(SOURCES
        ${SOURCES}
        main.cpp
        data_processor/dataUnpacker.cpp
        telemetry/telemetry.cpp
        telemetry/can_bridge.cpp
        gps/gps.cpp
        3rdparty/serial/serialib.cpp
        Config.cpp
        )

# Add the header files
set(HEADERS
        ${HEADERS}
        data_processor/dataUnpacker.h
        backendprocesses.h
        telemetry/telemetry.h
        telemetry/DTI.h
        telemetry/can_bridge.h
        gps/gps.h
        3rdparty/serial/serialib.h
        Config.h
        )

# Add the executable target
add_executable(${PROJECT_NAME} ${SOURCES} ${HEADERS})

# Link against standard libraries
if(UNIX)
    target_link_libraries(${PROJECT_NAME} PRIVATE pthread)
endif()

# Include directories
target_include_directories(${PROJECT_NAME} PRIVATE 
    ./
    ./3rdparty
    ./telemetry
    ./data_processor
)

# InfluxDB / Line Protocol tester + shared library (merged from sc2-telemetry-tester tester--cpp)
find_package(CURL REQUIRED)
add_subdirectory(cpp)
