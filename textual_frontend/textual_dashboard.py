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
from pathlib import Path

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
        return f"""
[bold cyan]Speed:[/] {self.speed:.1f} km/h
[bold green]Battery SoC:[/] {self.soc:.1f}%
[bold yellow]Pack Voltage:[/] {self.pack_voltage:.1f}V
[bold red]Pack Current:[/] {self.pack_current:.1f}A
[bold magenta]Motor Temp:[/] {self.motor_temp:.1f}°C
        """.strip()

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
        return f"""
[bold blue]CPU Usage:[/] {self.cpu_percent:.1f}%
[bold orange3]Memory:[/] {self.memory_percent:.1f}%
[bold red]CPU Temp:[/] {self.cpu_temp:.1f}°C
[bold green]Power Draw:[/] {self.power_draw:.1f}W
        """.strip()

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
        
        return f"""
Headlights: {status_icon(self.headlights)}
Left Turn: {status_icon(self.l_turn)}
Right Turn: {status_icon(self.r_turn)}
Hazards: {status_icon(self.hazards)}
Parking Brake: {status_icon(self.parking_brake)}
        """.strip()

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

class SC2Dashboard(App):
    """Main Textual dashboard application"""
    
    CSS_PATH = "dashboard.css"
    TITLE = "SC2 Driver IO Dashboard"
    SUB_TITLE = "Terminal-based Vehicle Telemetry"
    
    def __init__(self):
        super().__init__()
        self.telemetry_data = {}
        self.last_update = 0
    
    def compose(self) -> ComposeResult:
        """Create the dashboard layout"""
        yield Header()
        yield Container(
            Horizontal(
                Vertical(
                    TelemetryDisplay(id="telemetry"),
                    BatteryIndicator(id="battery"),
                    classes="left-panel"
                ),
                Vertical(
                    SystemInfo(id="system"),
                    StatusIndicators(id="status"),
                    classes="right-panel"
                ),
                classes="main-container"
            ),
            id="main"
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """Start background tasks when app starts"""
        self.set_interval(0.1, self.update_telemetry)  # 10Hz telemetry updates
        self.set_interval(1.0, self.update_system_info)  # 1Hz system updates
    
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

def main():
    """Entry point for the dashboard"""
    app = SC2Dashboard()
    app.run()

if __name__ == "__main__":
    main()