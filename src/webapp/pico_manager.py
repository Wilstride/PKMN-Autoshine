"""Pico device manager for handling multiple Pico controllers.

This module provides the PicoManager class which handles:
- Discovery and management of multiple Pico devices
- Macro loading and execution on selected devices
- Progress monitoring and iteration tracking
- Device status monitoring
"""
from __future__ import annotations

import asyncio
import logging
import serial.tools.list_ports
from typing import Dict, List, Optional, Set, Callable
from pathlib import Path

from adapter.pico import PicoAdapter

logger = logging.getLogger(__name__)


class PicoDevice:
    """Represents a single Pico device with its adapter and status."""
    
    def __init__(self, port: str, adapter: PicoAdapter):
        self.port = port
        self.adapter = adapter
        self.connected = False
        self.running_macro = False
        self.current_macro = None
        self.iteration_count = 0
        self.last_response_time = 0


class PicoManager:
    """Manages multiple Pico devices and coordinates macro execution."""
    
    def __init__(self):
        self.devices: Dict[str, PicoDevice] = {}
        self.response_callback: Optional[Callable[[str, str], None]] = None
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
    
    def set_response_callback(self, callback: Callable[[str, str], None]) -> None:
        """Set callback for receiving device responses.
        
        Args:
            callback: Function called with (device_port, response_line)
        """
        self.response_callback = callback
    
    async def discover_devices(self) -> List[str]:
        """Discover available Pico devices.
        
        Returns:
            List of port names for detected Pico devices.
        """
        ports = serial.tools.list_ports.comports()
        pico_ports = []
        
        for port in ports:
            # Look for Pico device characteristics
            if port.vid == 0x2E8A:  # Raspberry Pi Foundation VID
                pico_ports.append(port.device)
            elif any(keyword in (port.description or "").lower() 
                    for keyword in ["pico", "rp2040", "raspberry"]):
                pico_ports.append(port.device)
        
        logger.info(f"Discovered {len(pico_ports)} Pico devices: {pico_ports}")
        return pico_ports
    
    async def connect_device(self, port: str) -> bool:
        """Connect to a Pico device.
        
        Args:
            port: Port name to connect to.
            
        Returns:
            True if connection successful.
        """
        if port in self.devices and self.devices[port].connected:
            return True
        
        try:
            adapter = PicoAdapter(port=port)
            await adapter.connect()
            
            device = PicoDevice(port, adapter)
            device.connected = True
            self.devices[port] = device
            
            logger.info(f"Connected to Pico device on {port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Pico on {port}: {e}")
            return False
    
    async def disconnect_device(self, port: str) -> None:
        """Disconnect from a Pico device.
        
        Args:
            port: Port name to disconnect from.
        """
        if port in self.devices:
            device = self.devices[port]
            if device.running_macro:
                await device.adapter.stop_macro()
            device.adapter.close()
            device.connected = False
            logger.info(f"Disconnected from Pico device on {port}")
    
    async def connect_all_devices(self) -> int:
        """Connect to all discovered Pico devices.
        
        Returns:
            Number of devices successfully connected.
        """
        ports = await self.discover_devices()
        connected_count = 0
        
        for port in ports:
            if await self.connect_device(port):
                connected_count += 1
        
        return connected_count
    
    async def load_macro(self, macro_content: str, device_ports: Optional[List[str]] = None) -> Dict[str, bool]:
        """Load a macro to specified devices.
        
        Args:
            macro_content: The macro content as a string.
            device_ports: List of device ports to load to. If None, loads to all connected devices.
            
        Returns:
            Dict mapping port to success status.
        """
        if device_ports is None:
            device_ports = [port for port, device in self.devices.items() if device.connected]
        
        results = {}
        
        for port in device_ports:
            if port not in self.devices or not self.devices[port].connected:
                results[port] = False
                continue
            
            try:
                device = self.devices[port]
                await device.adapter.load_macro_file(macro_content)
                device.current_macro = macro_content
                results[port] = True
                logger.info(f"Loaded and preprocessed macro to device {port}")
            except Exception as e:
                logger.error(f"Failed to load macro to device {port}: {e}")
                results[port] = False
        
        return results
    
    async def start_macro(self, device_ports: Optional[List[str]] = None) -> Dict[str, bool]:
        """Start macro execution on specified devices.
        
        Args:
            device_ports: List of device ports to start. If None, starts on all connected devices.
            
        Returns:
            Dict mapping port to success status.
        """
        if device_ports is None:
            device_ports = [port for port, device in self.devices.items() if device.connected]
        
        results = {}
        
        for port in device_ports:
            if port not in self.devices or not self.devices[port].connected:
                results[port] = False
                continue
            
            try:
                device = self.devices[port]
                await device.adapter.start_macro()
                device.running_macro = True
                device.iteration_count = 0
                results[port] = True
                logger.info(f"Started macro on device {port}")
            except Exception as e:
                logger.error(f"Failed to start macro on device {port}: {e}")
                results[port] = False
        
        return results
    
    async def stop_macro(self, device_ports: Optional[List[str]] = None) -> Dict[str, bool]:
        """Stop macro execution on specified devices.
        
        Args:
            device_ports: List of device ports to stop. If None, stops on all connected devices.
            
        Returns:
            Dict mapping port to success status.
        """
        if device_ports is None:
            device_ports = [port for port, device in self.devices.items() if device.connected]
        
        results = {}
        
        for port in device_ports:
            if port not in self.devices or not self.devices[port].connected:
                results[port] = False
                continue
            
            try:
                device = self.devices[port]
                await device.adapter.stop_macro()
                device.running_macro = False
                results[port] = True
                logger.info(f"Stopped macro on device {port}")
            except Exception as e:
                logger.error(f"Failed to stop macro on device {port}: {e}")
                results[port] = False
        
        return results
    
    def get_device_status(self) -> Dict[str, Dict]:
        """Get status of all devices.
        
        Returns:
            Dict mapping port to device status dict.
        """
        status = {}
        for port, device in self.devices.items():
            status[port] = {
                'connected': device.connected,
                'running_macro': device.running_macro,
                'current_macro': device.current_macro is not None,
                'iteration_count': device.iteration_count
            }
        return status
    
    async def start_monitoring(self) -> None:
        """Start monitoring device responses."""
        if self._monitor_task is not None:
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_responses())
        logger.info("Started device monitoring")
    
    async def stop_monitoring(self) -> None:
        """Stop monitoring device responses."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        logger.info("Stopped device monitoring")
    
    async def _monitor_responses(self) -> None:
        """Monitor responses from all connected devices."""
        while self._running:
            try:
                for port, device in self.devices.items():
                    if not device.connected:
                        continue
                    
                    try:
                        responses = await device.adapter.read_responses()
                        for response in responses:
                            await self._handle_device_response(port, response)
                    except Exception as e:
                        logger.warning(f"Error reading from device {port}: {e}")
                
                # Check every 100ms
                await asyncio.sleep(0.1)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in device monitoring: {e}")
                await asyncio.sleep(1)
    
    async def _handle_device_response(self, port: str, response: str) -> None:
        """Handle a response from a device.
        
        Args:
            port: Device port that sent the response.
            response: Response string from device.
        """
        device = self.devices.get(port)
        if not device:
            return
        
        # Parse iteration completion messages
        if response.startswith("ITERATION_COMPLETE:"):
            try:
                iteration_num = int(response.split(":", 1)[1])
                device.iteration_count = iteration_num
                logger.info(f"Device {port} completed iteration {iteration_num}")
            except ValueError:
                pass
        
        # Forward response to callback if set
        if self.response_callback:
            try:
                self.response_callback(port, response)
            except Exception as e:
                logger.error(f"Error in response callback: {e}")
    
    async def cleanup(self) -> None:
        """Clean up all connections and stop monitoring."""
        await self.stop_monitoring()
        
        for port in list(self.devices.keys()):
            await self.disconnect_device(port)
        
        self.devices.clear()
        logger.info("PicoManager cleanup completed")