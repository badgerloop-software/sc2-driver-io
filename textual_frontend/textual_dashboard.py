#!/usr/bin/env python3
"""
SC2 Driver IO - Textual Terminal Dashboard
Lightweight terminal-based GUI replacement for Qt frontend
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, RichLog
from textual.reactive import reactive
import asyncio
import psutil
import json
import time
import sys
from pathlib import Path
from collections import deque
sys.path.append('..')
from lte_network import LTENetworkManager

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

class ActiveLogging(ScrollableContainer):
    """Widget to display active logging messages"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._rich_log = None
        self._last_log_count = 0
    
    def compose(self) -> ComposeResult:
        """Create the RichLog widget"""
        yield RichLog(wrap=True, highlight=True, markup=True, id="rich_log")
    
    def on_mount(self) -> None:
        """Get reference to RichLog after mounting"""
        self._rich_log = self.query_one("#rich_log", RichLog)
        self._rich_log.write("[dim]Waiting for logs...[/dim]")
    
    def add_log(self, message: str, level: str = "INFO") -> None:
        """Add a new log message"""
        if self._rich_log:
            timestamp = time.strftime("%H:%M:%S")
            color_map = {
                "DEBUG": "dim",
                "INFO": "cyan",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold red"
            }
            color = color_map.get(level, "white")
            formatted_msg = f"[{color}]{timestamp} [{level}][/{color}] {message}"
            self._rich_log.write(formatted_msg)

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
            NetworkInfo(id="network"),
            Horizontal(
                Vertical(
                    SystemInfo(id="system"),
                    FaultsDisplay(id="faults"),
                    id="left-column"
                ),
                ActiveLogging(id="logging"),
                id="main-container"
            ),
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """Start background tasks when app starts"""
        # Initialize network info immediately
        self.call_later(self.update_cellular_info)
        self.set_interval(1.0, self.update_system_info)  # 1Hz system updates
        self.set_interval(5.0, self.update_cellular_info)  # 5 second cellular updates
        self.set_interval(0.1, self.update_logs)  # 10Hz log updates
    
    async def update_logs(self) -> None:
        """Update logs from the main application"""
        try:
            # Read from shared log file
            log_file = Path("../dashboard_logs.json")
            if log_file.exists():
                with open(log_file, 'r') as f:
                    logs = json.load(f)
                
                logging_widget = self.query_one("#logging", ActiveLogging)
                
                # Initialize last_log_timestamp if not set
                if not hasattr(self, '_last_log_timestamp'):
                    self._last_log_timestamp = 0
                
                # Process new logs
                for log_entry in logs.get('messages', []):
                    entry_timestamp = log_entry.get('timestamp', 0)
                    if entry_timestamp > self._last_log_timestamp:
                        logging_widget.add_log(
                            log_entry.get('message', ''),
                            log_entry.get('level', 'INFO')
                        )
                        self._last_log_timestamp = entry_timestamp
                
                # Also update faults from telemetry data
                telemetry_file = Path("../telemetry_data.json")
                if telemetry_file.exists():
                    with open(telemetry_file, 'r') as f:
                        data = json.load(f)
                    
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
        # Initialize with defaults
        cellular_carrier = "Unknown"
        cellular_signal_bars = 0
        wifi_network = "Not Connected"
        wifi_signal_bars = 0
        radio_connected = False
        
        try:
            # Get cellular info
            try:
                cellular_data = self.lte_manager.get_cellular_info()
                cellular_carrier = cellular_data.get('carrier', 'Unknown')
                cellular_signal_bars = cellular_data.get('signal_bars', 0)
            except Exception as e:
                # LTE manager error, use defaults
                pass
            
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
            network_widget.cellular_carrier = cellular_carrier
            network_widget.cellular_signal_bars = cellular_signal_bars
            network_widget.wifi_network = wifi_network
            network_widget.wifi_signal_bars = wifi_signal_bars
            network_widget.radio_connected = radio_connected
            
        except Exception as e:
            # Handle network info errors gracefully - still update with defaults
            try:
                network_widget = self.query_one("#network", NetworkInfo)
                network_widget.cellular_carrier = cellular_carrier
                network_widget.cellular_signal_bars = cellular_signal_bars
                network_widget.wifi_network = wifi_network
                network_widget.wifi_signal_bars = wifi_signal_bars
                network_widget.radio_connected = radio_connected
            except:
                pass

def main():
    """Entry point for the dashboard"""
    app = SC2Dashboard()
    app.run()

if __name__ == "__main__":
    main()