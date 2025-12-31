#!/usr/bin/env python3
"""
LTE Network Module for SC2 Driver IO
Forces specific connections to use LTE interface while allowing others to use WiFi
"""

import socket
import subprocess
import logging
import serial
import time
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class LTENetworkManager:
    """Manages network routing to force cloud connections over LTE"""
    
    def __init__(self, lte_interface: str = "usb0", cloud_domain: str = "live.bsr-dev.org"):
        self.lte_interface = lte_interface
        self.cloud_domain = cloud_domain
        self.lte_local_addr = None
        self._detect_lte_address()
    
    def _detect_lte_address(self):
        """Detect the local IPv6 address on LTE interface"""
        try:
            result = subprocess.run(
                ["ip", "-6", "addr", "show", "dev", self.lte_interface],
                capture_output=True, text=True, check=True
            )
            for line in result.stdout.split('\n'):
                if 'scope global' in line:
                    addr = line.strip().split()[1].split('/')[0]
                    self.lte_local_addr = addr
                    logger.info(f"LTE interface {self.lte_interface} has address: {addr}")
                    break
        except Exception as e:
            logger.error(f"Failed to detect LTE address: {e}")
    
    def create_socket(self, family=socket.AF_INET6, sock_type=socket.SOCK_STREAM) -> socket.socket:
        """
        Create a socket bound to the LTE interface
        
        Args:
            family: Socket family (AF_INET or AF_INET6)
            sock_type: Socket type (SOCK_STREAM or SOCK_DGRAM)
            
        Returns:
            Socket bound to LTE interface
        """
        sock = socket.socket(family, sock_type)
        
        try:
            # Bind to the LTE interface
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, 
                          self.lte_interface.encode())
            logger.debug(f"Socket bound to {self.lte_interface}")
        except Exception as e:
            logger.error(f"Failed to bind socket to {self.lte_interface}: {e}")
            # Socket will use default routing
        
        return sock
    
    def resolve_cloud_server(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Resolve cloud server to IPv4 and IPv6 addresses
        
        Returns:
            Tuple of (ipv4_address, ipv6_address)
        """
        ipv4, ipv6 = None, None
        
        try:
            # Get all addresses
            addr_info = socket.getaddrinfo(self.cloud_domain, None)
            for info in addr_info:
                family, _, _, _, addr = info
                if family == socket.AF_INET and not ipv4:
                    ipv4 = addr[0]
                elif family == socket.AF_INET6 and not ipv6:
                    ipv6 = addr[0]
            
            logger.info(f"Resolved {self.cloud_domain}: IPv4={ipv4}, IPv6={ipv6}")
        except Exception as e:
            logger.error(f"Failed to resolve {self.cloud_domain}: {e}")
        
        return ipv4, ipv6
    
    def connect_to_cloud(self, port: int = 443, use_ipv6: bool = True) -> Optional[socket.socket]:
        """
        Create a connection to the cloud server over LTE
        
        Args:
            port: Port number to connect to
            use_ipv6: Prefer IPv6 if available
            
        Returns:
            Connected socket or None on failure
        """
        ipv4, ipv6 = self.resolve_cloud_server()
        
        # Try IPv6 first if available and preferred
        if use_ipv6 and ipv6:
            try:
                sock = self.create_socket(socket.AF_INET6, socket.SOCK_STREAM)
                sock.connect((ipv6, port))
                logger.info(f"Connected to {self.cloud_domain} via IPv6 over {self.lte_interface}")
                return sock
            except Exception as e:
                logger.warning(f"IPv6 connection failed: {e}")
        
        # Fallback to IPv4
        if ipv4:
            try:
                sock = self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect((ipv4, port))
                logger.info(f"Connected to {self.cloud_domain} via IPv4 over {self.lte_interface}")
                return sock
            except Exception as e:
                logger.error(f"IPv4 connection failed: {e}")
        
        return None
    
    def check_lte_status(self) -> dict:
        """
        Check LTE connection status
        
        Returns:
            Dictionary with status information
        """
        status = {
            'interface': self.lte_interface,
            'local_address': self.lte_local_addr,
            'is_up': False,
            'has_gateway': False,
            'signal_quality': None,
            'operator_name': None
        }
        
        try:
            # Check if interface is up
            result = subprocess.run(
                ["ip", "link", "show", self.lte_interface],
                capture_output=True, text=True, check=True
            )
            status['is_up'] = 'state UP' in result.stdout
            
            # Check for default route
            result = subprocess.run(
                ["ip", "-6", "route", "show", "dev", self.lte_interface],
                capture_output=True, text=True, check=True
            )
            status['has_gateway'] = 'default' in result.stdout
            
            # Get modem information
            result = subprocess.run(
                ["mmcli", "-m", "1", "-K"],
                capture_output=True, text=True, check=True
            )
            for line in result.stdout.split('\n'):
                if 'signal-quality.value' in line:
                    status['signal_quality'] = line.split(':')[1].strip()
                elif 'modem.3gpp.operator-name' in line and 'network-rejection' not in line:
                    status['operator_name'] = line.split(':')[1].strip()
        
        except Exception as e:
            logger.error(f"Failed to check LTE status: {e}")
        
        return status
    
    def get_cellular_info(self) -> dict:
        """
        Get cellular information for dashboard display
        
        Returns:
            Dictionary with carrier and signal bars
        """
        carrier = "Unknown"
        signal_quality = 0
        
        try:
            # Open serial connection to modem AT port
            with serial.Serial('/dev/ttyUSB2', 115200, timeout=1) as ser:
                # Get operator name
                ser.write(b'AT+COPS?\r\n')
                time.sleep(0.5)
                response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                
                # Parse operator name from response
                for line in response.split('\n'):
                    if '+COPS:' in line:
                        # Format: +COPS: 0,0,"Tello",7
                        parts = line.split(',')
                        if len(parts) >= 3:
                            carrier = parts[2].strip('"')
                        break
                
                # Get signal quality
                ser.write(b'AT+CSQ\r\n')
                time.sleep(0.5)
                response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                
                # Parse signal quality from response
                for line in response.split('\n'):
                    if '+CSQ:' in line:
                        # Format: +CSQ: 20,99
                        parts = line.split(':')[1].split(',')
                        if len(parts) >= 1:
                            try:
                                rssi = int(parts[0].strip())
                                # Convert RSSI to percentage (0-31 range, 99=unknown)
                                if rssi <= 31:
                                    signal_quality = min(100, (rssi * 100) // 31)
                                else:
                                    signal_quality = 0
                            except ValueError:
                                signal_quality = 0
                        break
        
        except Exception as e:
            logger.error(f"Failed to get cellular info via AT commands: {e}")
            # Fallback to mmcli if AT commands fail
            try:
                status = self.check_lte_status()
                carrier = status.get('operator_name', 'Unknown')
                signal_quality = int(status.get('signal_quality', 0))
            except:
                pass
        
        # Convert signal quality percentage to bars
        signal_bars = 0
        if signal_quality >= 80:
            signal_bars = 4
        elif signal_quality >= 60:
            signal_bars = 3
        elif signal_quality >= 40:
            signal_bars = 2
        elif signal_quality >= 20:
            signal_bars = 1
        
        return {
            'carrier': carrier,
            'signal_bars': signal_bars,
            'signal_quality': str(signal_quality)
        }
    
    def get_data_usage_info(self) -> str:
        """
        Attempt to get cellular data usage information
        NOT CURRENTLY USED - Serial port conflicts with ModemManager
        This is carrier-specific and may not work for all providers
        For Tello/T-Mobile: uses *3282# USSD code
        """
        data_info = "Query Failed"
        
        try:
            # Try AT command to query data usage (carrier-specific)
            with serial.Serial('/dev/ttyUSB2', 115200, timeout=2) as ser:
                # Some carriers support USSD via AT+CUSD command
                # For Tello/T-Mobile, try *3282# (data usage USSD code)
                
                # First check if USSD is supported
                ser.write(b'AT+CUSD=?\r\n')
                time.sleep(0.5)
                response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                
                if 'OK' in response:
                    # Try Tello/T-Mobile data usage USSD (*3282#)
                    ser.write(b'AT+CUSD=1,"*3282#",15\r\n')
                    time.sleep(3)  # Wait longer for USSD response
                    response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
                    
                    # Parse USSD response (this is very carrier-specific)
                    if '+CUSD:' in response:
                        # Look for data usage information in the response
                        if 'data' in response.lower() or 'gb' in response.lower() or 'mb' in response.lower():
                            data_info = "Data Info Received"
                        else:
                            data_info = "USSD Response Parsed"
                    else:
                        data_info = "No USSD Response"
                else:
                    data_info = "USSD Not Supported"
                    
        except Exception as e:
            logger.error(f"Failed to query data usage: {e}")
            data_info = "Query Error"
        
        return data_info
    
    def setup_routing(self):
        """Setup routing rules for LTE (requires root)"""
        try:
            script_path = "/home/sunpi/setup-lte-routing.sh"
            result = subprocess.run(
                ["sudo", script_path],
                capture_output=True, text=True, check=True
            )
            logger.info("LTE routing configured successfully")
            logger.debug(result.stdout)
            return True
        except Exception as e:
            logger.error(f"Failed to setup routing: {e}")
            return False


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    
    manager = LTENetworkManager()
    
    # Check status
    status = manager.check_lte_status()
    print(f"LTE Status: {status}")
    
    # Test connection
    sock = manager.connect_to_cloud(port=443)
    if sock:
        print("Successfully connected to cloud over LTE!")
        sock.close()
    else:
        print("Failed to connect to cloud")
