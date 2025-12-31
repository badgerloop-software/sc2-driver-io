#!/usr/bin/env python3
"""
SC2 Driver IO - Textual Terminal Dashboard
Lightweight terminal-based GUI replacement for Qt frontend
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, ProgressBar
from textual.reactive import reactive
import asyncio
import psutil
import json
import time
import sys
from pathlib import Path
sys.path.append('..')
from lte_network import LTENetworkManager

class TelemetryDisplay(Static):
    """Widget to display telemetry data"""
    
    speed = reactive(0.0)
    soc = reactive(0.0)
    pack_voltage = reactive(0.0)
    pack_current = reactive(0.0)
    motor_temp = reactive(0.0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "Vehicle Telemetry"
    
    def render(self) -> str:
        return f"[bold cyan]Speed:[/] {self.speed:.1f} km/h  [bold green]SoC:[/] {self.soc:.1f}%  [bold yellow]Pack V:[/] {self.pack_voltage:.1f}V  [bold red]Pack I:[/] {self.pack_current:.1f}A  [bold magenta]Motor T:[/] {self.motor_temp:.1f}°C"

class SystemInfo(Static):
    """Widget to display system information"""
    
    cpu_percent = reactive(0.0)
    memory_percent = reactive(0.0)
    cpu_temp = reactive(0.0)
    power_draw = reactive(0.0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "System Status"
    
    def render(self) -> str:
        return f"[bold blue]CPU:[/] {self.cpu_percent:.1f}%  [bold orange3]Mem:[/] {self.memory_percent:.1f}%  [bold red]CPU T:[/] {self.cpu_temp:.1f}°C  [bold green]Power:[/] {self.power_draw:.1f}W"

class NetworkInfo(Static):
    """Widget to display network information (cellular, WiFi, and radio)"""
    
    cellular_carrier = reactive("Unknown")
    cellular_signal_bars = reactive(0)
    wifi_network = reactive("Not Connected")
    wifi_signal_bars = reactive(0)
    radio_connected = reactive(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "Network Settings"
    
    def render(self) -> str:
        # Create signal bar displays
        cellular_bars = ""
        for i in range(4):
            if i < self.cellular_signal_bars:
                cellular_bars += "[bold green]▮[/]"
            else:
                cellular_bars += "[dim]▯[/]"
        
        wifi_bars = ""
        for i in range(4):
            if i < self.wifi_signal_bars:
                wifi_bars += "[bold blue]▮[/]"
            else:
                wifi_bars += "[dim]▯[/]"
        
        radio_status = "[bold red]●[/]" if self.radio_connected else "[dim]○[/]"
        
        return f"[bold cyan]Cell:[/] {self.cellular_carrier} {cellular_bars} | [bold blue]WiFi:[/] {self.wifi_network} {wifi_bars} | [bold yellow]Radio:[/] {radio_status}"

class StatusIndicators(Static):
    """Widget for boolean status indicators"""
    
    headlights = reactive(False)
    l_turn = reactive(False)
    r_turn = reactive(False)
    hazards = reactive(False)
    parking_brake = reactive(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "Vehicle Status"
    
    def render(self) -> str:
        def status_icon(active: bool) -> str:
            return "[bold green]●[/]" if active else "[dim]○[/]"
        
        return f"Headlights: {status_icon(self.headlights)}  Left: {status_icon(self.l_turn)}  Right: {status_icon(self.r_turn)}  Hazards: {status_icon(self.hazards)}  Park: {status_icon(self.parking_brake)}"

class BatteryIndicator(Container):
    """Battery level indicator with progress bar"""
    
    soc = reactive(0.0)
    
    def compose(self) -> ComposeResult:
        yield Static("Battery Level", classes="label")
        yield ProgressBar(total=100, show_percentage=True, classes="battery")
    
    def watch_soc(self, soc: float) -> None:
        """Update battery progress bar when SoC changes"""
        progress_bar = self.query_one(ProgressBar)
        progress_bar.progress = soc

class FaultsDisplay(Static):
    """Widget to display active faults"""
    
    faults = reactive({})
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "Vehicle Faults"
        # Define all possible faults
        self.all_faults = [
            "bps_fault",
            "voltage_failsafe",
            "current_failsafe",
            "relay_failsafe",
            "charge_interlock_failsafe",
            "thermistor_b_value_table_invalid",
            "input_power_supply_failsafe",
            "discharge_limit_enforcement_fault",
            "charger_safety_relay_fault",
            "internal_hardware_fault",
            "internal_heatsink_fault",
            "internal_software_fault",
            "highest_cell_voltage_too_high_fault",
            "lowest_cell_voltage_too_low_fault",
            "pack_too_hot_fault",
            "high_voltage_interlock_signal_fault",
            "precharge_circuit_malfunction",
            "abnormal_state_of_charge_behavior",
            "internal_communication_fault",
            "cell_balancing_stuck_off_fault",
            "weak_cell_fault",
            "low_cell_voltage_fault",
            "open_wiring_fault",
            "current_sensor_fault",
            "highest_cell_voltage_over_5V_fault",
            "cell_asic_fault",
            "weak_pack_fault",
            "fan_monitor_fault",
            "thermistor_fault",
            "external_communication_fault",
            "redundant_power_supply_fault",
            "high_voltage_isolation_fault",
            "input_power_supply_fault",
            "charge_limit_enforcement_fault"
        ]
    
    def render(self) -> str:
        active_faults = [fault for fault in self.all_faults if self.faults.get(fault, False)]
        if not active_faults:
            return "[green]No active faults[/]"
        
        fault_lines = []
        for fault in active_faults:
            # Format fault name for display
            display_name = fault.replace('_', ' ').title()
            fault_lines.append(f"[bold red]●[/] {display_name}")
        
        return "\n".join(fault_lines)

class SC2Dashboard(App):
    """Main Textual dashboard application"""
    
    CSS_PATH = "dashboard.css"
    TITLE = "SC2 Driver IO Dashboard"
    
    def __init__(self):
        super().__init__()
        self.telemetry_data = {}
        self.last_update = 0
        self.lte_manager = LTENetworkManager()
    
    def compose(self) -> ComposeResult:
        """Create the dashboard layout"""
        yield Header()
        yield Vertical(
            Vertical(
                NetworkInfo(id="network"),
                Container(
                    Horizontal(
                        Vertical(
                            TelemetryDisplay(id="telemetry"),
                            BatteryIndicator(id="battery"),
                            classes="left-panel"
                        ),
                        Vertical(
                            SystemInfo(id="system"),
                            StatusIndicators(id="status"),
                            classes="middle-panel"
                        ),
                        Vertical(
                            FaultsDisplay(id="faults"),
                            classes="right-panel"
                        ),
                        classes="main-container"
                    ),
                    id="main"
                ),
            ),
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """Start background tasks when app starts"""
        self.set_interval(0.1, self.update_telemetry)  # 10Hz telemetry updates
        self.set_interval(1.0, self.update_system_info)  # 1Hz system updates
        self.set_interval(5.0, self.update_cellular_info)  # 5 second cellular updates
    
    async def update_telemetry(self) -> None:
        """Update telemetry data from C++ backend"""
        try:
            # Read from shared data source (JSON file, named pipe, or direct C++ interface)
            telemetry_file = Path("../telemetry_data.json")
            if telemetry_file.exists():
                with open(telemetry_file, 'r') as f:
                    data = json.load(f)
                
                # Update telemetry display
                telemetry_widget = self.query_one("#telemetry", TelemetryDisplay)
                telemetry_widget.speed = data.get("speed", 0.0)
                telemetry_widget.soc = data.get("soc", 0.0)
                telemetry_widget.pack_voltage = data.get("pack_voltage", 0.0)
                telemetry_widget.pack_current = data.get("pack_current", 0.0)
                telemetry_widget.motor_temp = data.get("motor_temp", 0.0)
                
                # Update battery indicator
                battery_widget = self.query_one("#battery", BatteryIndicator)
                battery_widget.soc = data.get("soc", 0.0)
                
                # Update status indicators
                status_widget = self.query_one("#status", StatusIndicators)
                status_widget.headlights = data.get("headlights", False)
                status_widget.l_turn = data.get("l_turn_led_en", False)
                status_widget.r_turn = data.get("r_turn_led_en", False)
                status_widget.hazards = data.get("hazards", False)
                status_widget.parking_brake = data.get("parking_brake", False)
                
                # Update faults display
                faults_widget = self.query_one("#faults", FaultsDisplay)
                faults_data = {}
                for fault in faults_widget.all_faults:
                    faults_data[fault] = data.get(fault, False)
                faults_widget.faults = faults_data
                
        except Exception as e:
            # Handle data reading errors gracefully
            pass
    
    async def update_system_info(self) -> None:
        """Update system performance metrics"""
        try:
            # Get system metrics
            cpu_percent = psutil.cpu_percent(interval=None)
            memory = psutil.virtual_memory()
            
            # Get CPU temperature (Raspberry Pi specific)
            cpu_temp = 0.0
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    cpu_temp = int(f.read()) / 1000.0
            except:
                pass
            
            # Estimate power draw (approximation for Pi 4)
            # More accurate with external power monitoring
            power_draw = 2.5 + (cpu_percent / 100.0) * 2.5  # 2.5-5W range
            
            # Update system info display
            system_widget = self.query_one("#system", SystemInfo)
            system_widget.cpu_percent = cpu_percent
            system_widget.memory_percent = memory.percent
            system_widget.cpu_temp = cpu_temp
            system_widget.power_draw = power_draw
            
        except Exception as e:
            # Handle system metric errors gracefully
            pass
    
    async def update_cellular_info(self) -> None:
        """Update network information (cellular and WiFi)"""
        try:
            # Get cellular info
            cellular_data = self.lte_manager.get_cellular_info()
            
            # Get WiFi info
            wifi_network = "Not Connected"
            wifi_signal_bars = 0
            
            try:
                # Try to get WiFi info using nmcli
                result = await asyncio.create_subprocess_exec(
                    "nmcli", "-t", "-f", "active,ssid,signal", "device", "wifi", "list",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate()
                
                if result.returncode == 0:
                    lines = stdout.decode().strip().split('\n')
                    for line in lines:
                        if line.startswith('yes:'):
                            parts = line.split(':')
                            if len(parts) >= 3:
                                wifi_network = parts[1]
                                try:
                                    signal = int(parts[2])
                                    # Convert signal percentage to bars
                                    if signal >= 75:
                                        wifi_signal_bars = 4
                                    elif signal >= 50:
                                        wifi_signal_bars = 3
                                    elif signal >= 25:
                                        wifi_signal_bars = 2
                                    elif signal > 0:
                                        wifi_signal_bars = 1
                                except ValueError:
                                    pass
                                break
            except Exception as e:
                # Fallback to iwconfig if nmcli fails
                try:
                    result = await asyncio.create_subprocess_exec(
                        "iwconfig", "wlan0",
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    stdout, stderr = await result.communicate()
                    
                    if result.returncode == 0:
                        output = stdout.decode()
                        # Parse ESSID and signal from iwconfig output
                        for line in output.split('\n'):
                            if 'ESSID:' in line:
                                essid_part = line.split('ESSID:')[1].strip()
                                if essid_part != 'off/any':
                                    wifi_network = essid_part.strip('"')
                            elif 'Signal level=' in line:
                                signal_part = line.split('Signal level=')[1].split()[0]
                                try:
                                    signal = int(float(signal_part))
                                    # iwconfig gives dBm, convert to bars
                                    if signal >= -50:
                                        wifi_signal_bars = 4
                                    elif signal >= -60:
                                        wifi_signal_bars = 3
                                    elif signal >= -70:
                                        wifi_signal_bars = 2
                                    elif signal >= -80:
                                        wifi_signal_bars = 1
                                except ValueError:
                                    pass
                except Exception:
                    pass
            
            # Check radio connection (RFD900A)
            radio_connected = False
            try:
                # Check for RFD900A radio (typically appears as ttyUSB or ttyACM device)
                result = await asyncio.create_subprocess_exec(
                    "ls", "/dev/ttyUSB*", "/dev/ttyACM*",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await result.communicate()
                
                if result.returncode == 0:
                    devices = stdout.decode().strip().split('\n')
                    # Look for radio-specific patterns (this is a basic check)
                    for device in devices:
                        if 'ttyUSB' in device or 'ttyACM' in device:
                            # Additional check: try to access the device
                            try:
                                test_result = await asyncio.create_subprocess_exec(
                                    "timeout", "1", "cat", device,
                                    stdout=asyncio.subprocess.PIPE,
                                    stderr=asyncio.subprocess.PIPE
                                )
                                await test_result.wait()
                                if test_result.returncode == 124:  # timeout occurred, device is accessible
                                    radio_connected = True
                                    break
                            except:
                                pass
            except Exception:
                pass
            
            # Update network info display
            network_widget = self.query_one("#network", NetworkInfo)
            network_widget.cellular_carrier = cellular_data.get('carrier', 'Unknown')
            network_widget.cellular_signal_bars = cellular_data.get('signal_bars', 0)
            network_widget.wifi_network = wifi_network
            network_widget.wifi_signal_bars = wifi_signal_bars
            network_widget.radio_connected = radio_connected
            
        except Exception as e:
            # Handle network info errors gracefully
            pass

def main():
    """Entry point for the dashboard"""
    app = SC2Dashboard()
    app.run()

if __name__ == "__main__":
    main()