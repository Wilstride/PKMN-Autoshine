"""Multi-device Pico manager."""
from __future__ import annotations

import serial.tools.list_ports
from typing import Dict, List, Optional

from .pico_device import PicoDevice


class PicoManager:
    """Manages multiple Pico devices."""
    
    def __init__(self, logger=None):
        self.devices: Dict[str, PicoDevice] = {}  # port -> PicoDevice
        self.logger = logger or print
    
    def discover_devices(self) -> List[str]:
        """Discover all available Pico devices."""
        ports = serial.tools.list_ports.comports()
        pico_ports = []
        
        for port in ports:
            # Check if it's a Pico (Raspberry Pi Foundation VID or description)
            if port.vid == 0x2E8A or 'pico' in (port.description or '').lower():
                pico_ports.append(port.device)
                self.logger(f"Found Pico device: {port.device} ({port.description})")
        
        return pico_ports
    
    def connect_all(self) -> int:
        """Discover and connect to all available Pico devices."""
        discovered = self.discover_devices()
        connected_count = 0
        
        for port in discovered:
            if port not in self.devices:
                device = PicoDevice(port)
                if device.connect():
                    self.devices[port] = device
                    connected_count += 1
                    self.logger(f"✓ Connected to Pico: {device.name} ({port})")
                else:
                    self.logger(f"✗ Failed to connect to: {port}")
            else:
                # Try to reconnect if disconnected
                device = self.devices[port]
                if not device.connected:
                    if device.connect():
                        connected_count += 1
                        self.logger(f"✓ Reconnected to Pico: {device.name} ({port})")
        
        return connected_count
    
    def get_device(self, port: str) -> Optional[PicoDevice]:
        """Get a specific Pico device by port."""
        return self.devices.get(port)
    
    def get_all_devices(self) -> List[PicoDevice]:
        """Get list of all connected devices."""
        return list(self.devices.values())
    
    def get_connected_devices(self) -> List[PicoDevice]:
        """Get list of only connected devices."""
        return [d for d in self.devices.values() if d.connected]
    
    def disconnect_all(self) -> None:
        """Disconnect from all Pico devices."""
        for device in self.devices.values():
            device.disconnect()
        self.devices.clear()
        self.logger("All devices disconnected")
    
    def send_command_to_all(self, command: str) -> int:
        """Send command to all connected devices. Returns number of successful sends."""
        success_count = 0
        for device in self.get_connected_devices():
            if device.send_command(command):
                success_count += 1
        return success_count
    
    def upload_macro_to_all(self, macro_content: str) -> int:
        """Upload macro to all connected devices. Returns number of successful uploads."""
        success_count = 0
        for device in self.get_connected_devices():
            if device.send_macro(macro_content):
                success_count += 1
        return success_count
    
    def poll_all_devices(self) -> None:
        """Poll all connected devices to read and process their serial buffers."""
        for device in self.get_connected_devices():
            device.poll_serial_buffer()
