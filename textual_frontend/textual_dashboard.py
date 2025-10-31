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
from pathlib import Path
from datetime import datetime

class NetworkStatusBar(Static):
    """Widget to display network status in header"""
    
    lte_bars = reactive(0)
    lte_carrier = reactive("Unknown")
    wifi_bars = reactive(0)
    wifi_ssid = reactive("Not Connected")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def render(self) -> str:
        # Create visual bars representation
        lte_visual = self._bars_to_visual(self.lte_bars, "📶")
        wifi_visual = self._bars_to_visual(self.wifi_bars, "📡")
        
        # Color code based on signal strength
        lte_color = self._signal_color(self.lte_bars)
        wifi_color = self._signal_color(self.wifi_bars)
        
        return f"[bold]{lte_color}📶 {lte_visual} {self.lte_carrier}[/] │ [{wifi_color}]📡 {wifi_visual} {self.wifi_ssid}[/]"
    
    def _bars_to_visual(self, bars: int, icon: str) -> str:
        """Convert signal bars to visual representation"""
        if bars == 0:
            return "____"
        elif bars == 1:
            return "▂___"
        elif bars == 2:
            return "▂▄__"
        elif bars == 3:
            return "▂▄▆_"
        elif bars == 4:
            return "▂▄▆█"
        else:
            return "____"
    
    def _signal_color(self, bars: int) -> str:
        """Get color based on signal strength"""
        if bars >= 3:
            return "green"
        elif bars >= 2:
            return "yellow"
        elif bars >= 1:
            return "red"
        else:
            return "dim"

class TelemetryDisplay(Static):
    """Widget to display telemetry data"""
    
    speed = reactive(0.0)
    soc = reactive(0.0)
    pack_voltage = reactive(0.0)
    pack_current = reactive(0.0)
    motor_temp = reactive(0.0)
    lap_count = reactive(0)
    current_section = reactive(0)
    lap_time = reactive("0:00.00")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "Vehicle Telemetry"
    
    def render(self) -> str:
        return f"""

[bold cyan]SPEED:[/] [bold white]{self.speed:.1f} km/h[/]


[bold green]BATTERY SOC:[/] [bold white]{self.soc:.1f}%[/]


[bold yellow]PACK VOLTAGE:[/] [bold white]{self.pack_voltage:.1f}V[/]


[bold red]PACK CURRENT:[/] [bold white]{self.pack_current:.1f}A[/]


[bold magenta]LAP:[/] [bold white]{self.lap_count}[/]  [bold magenta]SECTION:[/] [bold white]{self.current_section}[/]  [bold magenta]TIME:[/] [bold white]{self.lap_time}[/]

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

[bold blue]CPU USAGE:[/] [bold white]{self.cpu_percent:.1f}%[/]


[bold orange3]MEMORY:[/] [bold white]{self.memory_percent:.1f}%[/]


[bold red]CPU TEMP:[/] [bold white]{self.cpu_temp:.1f}°C[/]


[bold green]POWER DRAW:[/] [bold white]{self.power_draw:.1f}W[/]

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
            return "[bold green]████[/]" if active else "[dim]────[/]"
        
        return f"""
HEADLIGHTS:      {status_icon(self.headlights)}

LEFT TURN:       {status_icon(self.l_turn)}

RIGHT TURN:      {status_icon(self.r_turn)}

HAZARDS:         {status_icon(self.hazards)}

PARKING BRAKE:   {status_icon(self.parking_brake)}
        """.strip()

class BatteryIndicator(Static):
    """Battery level indicator with progress display"""
    
    soc = reactive(0.0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "Battery Level"
    
    def render(self) -> str:
        # Create a visual progress bar using characters
        bar_width = 40
        filled_width = int((self.soc / 100.0) * bar_width)
        empty_width = bar_width - filled_width
        
        bar = "█" * filled_width + "░" * empty_width
        
        return f"""
BATTERY: [bold green]{self.soc:.1f}%[/]

[green]{bar}[/]
        """.strip()

class DiagnosticsPanel(Static):
    """System diagnostics and error display"""
    
    system_status = reactive("UNKNOWN")
    message_rate = reactive(0.0)
    threads_alive = reactive(0)
    threads_total = reactive(0)
    uptime = reactive(0.0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "System Health"
    
    def render(self) -> str:
        # Color-code system status
        if self.system_status == "RUNNING":
            status_color = "green"
        elif self.system_status == "WARNING":
            status_color = "yellow"
        elif self.system_status == "ERROR":
            status_color = "red"
        else:
            status_color = "white"
        
        # Format uptime
        hours = int(self.uptime // 3600)
        minutes = int((self.uptime % 3600) // 60)
        seconds = int(self.uptime % 60)
        uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        return f"""
[bold]STATUS:[/] [{status_color}]{self.system_status}[/{status_color}]  [bold]UPTIME:[/] {uptime_str}  [bold]RATE:[/] {self.message_rate:.2f} Hz  [bold]THREADS:[/] {self.threads_alive}/{self.threads_total}
        """.strip()

class LiveLogViewer(RichLog):
    """Scrolling log viewer showing real-time system logs"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "System Logs (Live)"
        self.max_lines = 500  # Keep last 500 log lines

class SC2Dashboard(App):
    """Main Textual dashboard application"""
    
    CSS_PATH = "dashboard.css"
    TITLE = "SC2 Driver IO Dashboard"
    SUB_TITLE = "Terminal-based Vehicle Telemetry"
    
    def __init__(self):
        super().__init__()
        self.telemetry_data = {}
        self.last_update = 0
        self.last_log_position = 0  # Track log file position for tail -f behavior
    
    def compose(self) -> ComposeResult:
        """Create the dashboard layout"""
        yield Header()
        yield NetworkStatusBar(id="network-status")
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
            # Compact diagnostics panel
            DiagnosticsPanel(id="diagnostics"),
            # Live scrolling log viewer (takes remaining space)
            LiveLogViewer(id="logs", highlight=True, markup=True),
            id="main"
        )
        yield Footer()
    
    def on_mount(self) -> None:
        """Start background tasks when app starts"""
        self.set_interval(0.1, self.update_telemetry)  # 10Hz telemetry updates
        self.set_interval(1.0, self.update_system_info)  # 1Hz system updates
        self.set_interval(0.5, self.update_diagnostics)  # 2Hz diagnostics updates
        self.set_interval(0.2, self.update_logs)  # 5Hz log updates (tail -f behavior)
    
    async def update_telemetry(self) -> None:
        """Update telemetry data from main.py coordinator"""
        try:
            # Read from shared data source (JSON file written by main.py)
            telemetry_file = Path("../telemetry_data.json")
            if telemetry_file.exists():
                with open(telemetry_file, 'r') as f:
                    data = json.load(f)
                
                # Update telemetry display
                telemetry_widget = self.query_one("#telemetry", TelemetryDisplay)
                telemetry_widget.speed = data.get("speed", 0.0)
                telemetry_widget.soc = data.get("battery_soc", 0.0)
                telemetry_widget.pack_voltage = data.get("pack_voltage", 0.0)
                telemetry_widget.pack_current = data.get("pack_current", 0.0)
                
                # Update lap counter data (NEW)
                telemetry_widget.lap_count = data.get("lap_count", 0)
                telemetry_widget.current_section = data.get("current_section", 0)
                telemetry_widget.lap_time = data.get("lap_time_formatted", "0:00.00")
                
                # Update network status (NEW)
                network_widget = self.query_one("#network-status", NetworkStatusBar)
                lte_data = data.get("lte_signal", {})
                wifi_data = data.get("wifi_status", {})
                
                network_widget.lte_bars = lte_data.get("bars", 0)
                network_widget.lte_carrier = lte_data.get("carrier", "Unknown")
                network_widget.wifi_bars = wifi_data.get("bars", 0)
                network_widget.wifi_ssid = wifi_data.get("ssid", "Not Connected")
                
                # Update battery indicator
                battery_widget = self.query_one("#battery", BatteryIndicator)
                battery_widget.soc = data.get("battery_soc", 0.0)
                
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
    
    async def update_diagnostics(self) -> None:
        """Update system diagnostics from system_health.json"""
        try:
            # Read system health data written by main.py
            health_file = Path("../system_health.json")
            if health_file.exists():
                with open(health_file, 'r') as f:
                    health = json.load(f)
                
                # Update diagnostics panel (compact version)
                diag_widget = self.query_one("#diagnostics", DiagnosticsPanel)
                diag_widget.system_status = health.get("system_status", "UNKNOWN")
                diag_widget.message_rate = health.get("message_rate_hz", 0.0)
                diag_widget.threads_alive = health.get("threads_alive", 0)
                diag_widget.threads_total = health.get("threads_total", 0)
                diag_widget.uptime = health.get("uptime_seconds", 0.0)
        
        except Exception as e:
            # Handle diagnostic read errors gracefully
            pass
    
    async def update_logs(self) -> None:
        """Update live log viewer with latest log entries (tail -f behavior)"""
        try:
            # Read from main.py log file (assumed to be redirected to file)
            log_file = Path("../driver_io.log")
            
            if not log_file.exists():
                # If no log file yet, show startup message
                if self.last_log_position == 0:
                    log_widget = self.query_one("#logs", LiveLogViewer)
                    log_widget.write("[dim]Waiting for driver-io logs...[/dim]")
                    self.last_log_position = 1  # Mark as initialized
                return
            
            # Read new lines from log file (tail -f behavior)
            with open(log_file, 'r') as f:
                f.seek(self.last_log_position)
                new_lines = f.readlines()
                self.last_log_position = f.tell()
            
            if new_lines:
                log_widget = self.query_one("#logs", LiveLogViewer)
                
                for line in new_lines:
                    line = line.rstrip()
                    if not line:
                        continue
                    
                    # Color-code log levels
                    if "ERROR" in line:
                        log_widget.write(f"[bold red]{line}[/bold red]")
                    elif "WARNING" in line:
                        log_widget.write(f"[bold yellow]{line}[/bold yellow]")
                    elif "INFO" in line:
                        log_widget.write(f"[cyan]{line}[/cyan]")
                    elif "DEBUG" in line:
                        log_widget.write(f"[dim]{line}[/dim]")
                    else:
                        log_widget.write(line)
        
        except Exception as e:
            # Handle log read errors gracefully
            pass

def main():
    """Entry point for the dashboard"""
    app = SC2Dashboard()
    app.run()

if __name__ == "__main__":
    main()