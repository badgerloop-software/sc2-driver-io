# Solar Car 2 Driver IO Program

## Solar Car Dashboard

### Libraries/Frameworks

- [Qt](https://www.qt.io/) - Development framework
- [RapidJSON](https://rapidjson.org/) - JSON parsing library

### Cloning the Data Format Repository and Initializing the Submodule

0. If you don't already have an SSH key, [generate a new SSH key](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent) (only the steps under "Generating a new SSH key" are required) and [add it to your GitHub account](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account).
1. Once you have an SSH key, clone this repository to your computer. Make sure to clone it using SSH (when you go to copy the clone link, there will be an SSH option above the link).
2. Next, `cd` into the `sc1-driver-io` repository and run `git submodule update --init`.

### Running with CMake

CMake is a more popular project make system, it allows you to edit the project with your ide of choice and enables features like autocomplete while not bounded to using qtcreator.

0. If you are using windows, install Ubuntu via WSL, you can use any other distribution if you're experienced with linux.
1. Ensure you have cmake and build-essentials installed you can do so by `sudo apt install build-essential cmake`
2. Install qt packages with `sudo apt install qt5-doc qtbase5-examples qtbase5-doc-html qtdeclarative5-dev qml-module-qtquick-controls2`
3. `cd`into your project directory and `mkdir build` to create a new build folder then `cd build`
4. Run `cmake ..` to generate make file for the project, then run `make` to compile the project.
5. To execute the program run `./solar-car-dashboard`.

### Contributing to the Dashboard

0. Again, make sure you have [Qt](https://www.qt.io/download-open-source?hsCtaTracking=9f6a2170-a938-42df-a8e2-a9f0b1d6cdce%7C6cb0de4f-9bb5-4778-ab02-bfb62735f3e5) installed on your computer.
1. Clone the repository to your computer (see steps 0-1 of "Cloning the Data Format Repository and Initializing the Submodule" for instructions on cloning a repo using SSH).
2. If you have not already, clone the `sc1-data-format` repository and initialize the submodule (see instructions above).
3. Open the repository in Qt Creator and, if necessary, configure the project using the appropriate kit for your environment.
4. Run `git submodule update --remote` to update necessary submodules. You should also do this any time the submodule might have changed (i.e. whenever the [data format](https://github.com/badgerloop-software/sc1-data-format/blob/main/format.json) has been modified).
   1. To avoid pushing changes that use obsolete data, update the submodule before you `git push` your changes. If there are changes to the data format, run the dashboard to make sure your code still works.
5. To run the dashboard on your computer, simply press the green arrow in the bottom-left corner of the Qt Creator window. To run the project on a Raspberry Pi, see "Compiling and Running the Project on a Rapberry Pi" below.
6. Once you have finished making your necessary changes to your code, switch to a new branch that has a good name for the feature or names the Jira issue (e.g. `SW-23/skeleton`).
7. Commit related changes to that branch and push to this repository. (Do this often so that it is easy to finely revert to a previous state!)
   1. When committing and pushing changes, do not add your solar-car-dashboard.pro.user file to the version control, as this is specific to your computer.
8. Once you are happy with the state of your code, open a pull request and request someone to conduct a code review. It may be kicked back with some suggestions or edits, but when it is accepted, it will be merged with `main`. Congrats! Now it's just time to rinse and repeat.

### Compiling and Running the Project on a Rapberry Pi

0. If running the project on the driver IO board, skip this step, as the necessary dependencies have already been installed on it. Otherwise, if you have not already, install the dependencies on the Raspberry Pi:
   ```
   sudo apt install build-essential cmake
   sudo apt install qt5-doc qtbase5-examples qtbase5-doc-html qtdeclarative5-dev qml-module-qtquick-controls2
   ```
1. Copy the project to the Raspberry Pi.
2. make a build directory with in the project, make sure you are in the directory
3. Make and run the project on the Raspberry Pi by running the following commands:
   ```
   cmake ..
   make
   ./solar-car-dashboard
   ```

## Project Structure

This section provides an overview of the key folders and their purposes in the Solar Car 1 Driver IO project.

### Root Directory
- **CMakeLists.txt**: Build configuration file for CMake, used to compile the project.
- **main.cpp**: Main entry point of the Qt application, sets up the QML engine, loads the UI, and initializes the DataUnpacker.
- **Config.cpp/h**: Singleton class for reading and managing configuration from `config.json`.
- **config.json**: JSON file containing application configuration settings.

### 3rdparty/
Contains third-party libraries used in the project.
- **rapidjson/**: Header-only JSON parsing library for C++.
- **serial/**: Library for serial communication (serialib), used for interfacing with serial devices like GPS.

### backend/
Handles backend data processing and communication.
- **backendProcesses.cpp/h**: Manages backend processes, including telemetry data handling via TCP, UDP, and SQL connections. Runs in a separate thread to process incoming data.
- **dataFetcher.cpp/h**: Fetches data from network sources (TCP server), integrates GPS data, and manages data buffers.
- **file_sync/**: Contains scripts for synchronizing files, likely for uploading telemetry data.
- **telemetrylib/**: Library for telemetry operations, including TCP, UDP, SQL, and DTI (Data Transmission Interface) handling.

### DataProcessor/
Responsible for processing and unpacking telemetry data.
- **dataUnpacker.cpp/h**: Core class that unpacks binary data into readable properties exposed to the QML UI, such as fan speed, timestamps, LED statuses, and shutdown circuit states.
- **CMakeLists.txt**: Build configuration for the DataProcessor module.

### ethernet_sim/
Simulation tools for testing ethernet communication.
- **main.py**: Python script that simulates telemetry data transmission over ethernet, using the data format from `sc1-data-format` and GPS datasets.
- **gps_dataset/**: Sample GPS data files (CSV, GPX, JSON) used in simulations.

### gps/
GPS functionality module.
- **gps.cpp/h**: Class for interfacing with GPS devices via serial communication, parsing NMEA data to extract latitude, longitude, and altitude.

### sc1-data-format/
Git submodule containing the data format definitions for telemetry packets. This folder is empty until the submodule is initialized (see cloning instructions above).

### UI/
User interface components built with Qt QML.
- **Items/**: QML files defining UI components like Dashboard, Speed, Batteries, Blinkers, etc.
- **Images/**: Image assets (PNG, SVG) for the dashboard, such as needles, icons, and backgrounds.
- **fonts/**: Font files (Work Sans) used in the UI, with licensing information.
