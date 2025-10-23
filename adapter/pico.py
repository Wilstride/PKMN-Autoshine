"""Pico Bluetooth adapter for Autoshine.

This adapter communicates with the Pico W firmware over USB serial to send
commands to a Nintendo Switch via Bluetooth.
"""
from __future__ import annotations

import asyncio
import serial
import serial.tools.list_ports
import logging
from typing import Union
from adapter.base import BaseAdapter, Button, Stick

logger = logging.getLogger(__name__)


class PicoAdapter(BaseAdapter):
    """Adapter that sends commands to Pico W firmware via USB serial."""

    def __init__(self, port: str = None, baud: int = 115200, timeout: float = 1.0) -> None:
        """Initialize the Pico adapter.
        
        Args:
            port: Serial port to connect to. If None, will auto-detect.
            baud: Baud rate for serial communication.
            timeout: Timeout for serial operations.
        """
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.serial = None

    async def connect(self) -> None:
        """Connect to the Pico W firmware via USB serial."""
        if self.port is None:
            self.port = self._find_pico_port()
            if self.port is None:
                raise RuntimeError("Could not find Pico W device. Make sure it's connected and firmware is running.")
        
        logger.info(f"Connecting to Pico W on {self.port}")
        
        # Open serial connection in a thread to avoid blocking
        loop = asyncio.get_event_loop()
        self.serial = await loop.run_in_executor(
            None, 
            lambda: serial.Serial(self.port, self.baud, timeout=self.timeout)
        )
        
        # Wait a moment for the device to be ready
        await asyncio.sleep(1.0)
        
        # Send a test command to verify connection
        await self._send_command("# Connection test")
        logger.info("Successfully connected to Pico W firmware")

    def _find_pico_port(self) -> str | None:
        """Auto-detect the Pico W serial port."""
        ports = serial.tools.list_ports.comports()
        
        for port in ports:
            # Look for Pico device characteristics
            if port.vid == 0x2E8A:  # Raspberry Pi Foundation VID
                return port.device
                
            # Alternative: look for common Pico device descriptions
            if any(keyword in (port.description or "").lower() 
                   for keyword in ["pico", "rp2040", "raspberry"]):
                return port.device
        
        return None

    async def _send_command(self, command: str) -> None:
        """Send a command to the Pico firmware.
        
        Args:
            command: Command string to send.
        """
        if self.serial is None:
            raise RuntimeError("Not connected to Pico. Call connect() first.")
        
        command_bytes = (command + '\n').encode('utf-8')
        logger.debug(f"Sending command: {command}")
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self.serial.write, command_bytes)
        
        # Small delay to allow command processing
        await asyncio.sleep(0.01)

    async def press(self, btn: Button | str, duration: float = 0.1) -> None:
        """Press a button for the specified duration.
        
        Args:
            btn: Button to press (Button enum or string).
            duration: Duration to hold the button in seconds.
        """
        if isinstance(btn, Button):
            btn_str = btn.value
        else:
            btn_str = str(btn)
        
        await self._send_command(f"PRESS {btn_str}")
        await asyncio.sleep(duration)
        await self._send_command(f"RELEASE {btn_str}")

    async def stick(self, stick: Stick | str = Stick.L_STICK, h: Union[int, float] = 0x0800, v: Union[int, float] = 0x0800) -> None:
        """Move an analog stick to the specified position.
        
        Args:
            stick: Which stick to move (Stick enum or string).
            h: Horizontal position (raw 12-bit int or normalized float [-1.0, 1.0]).
            v: Vertical position (raw 12-bit int or normalized float [-1.0, 1.0]).
        """
        if isinstance(stick, Stick):
            stick_str = stick.value
        else:
            stick_str = str(stick)
        
        # Convert from raw 12-bit values to normalized floats if needed
        if isinstance(h, int):
            h = (h - 0x800) / 0x800  # Convert 0x000-0xFFF to -1.0 to 1.0
        if isinstance(v, int):
            v = (v - 0x800) / 0x800  # Convert 0x000-0xFFF to -1.0 to 1.0
        
        # Clamp values to valid range
        h = max(-1.0, min(1.0, h))
        v = max(-1.0, min(1.0, v))
        
        await self._send_command(f"STICK {stick_str} {h} {v}")

    async def release_all_buttons(self) -> None:
        """Release all buttons."""
        await self._send_command("RELEASE_ALL")

    async def center_sticks(self) -> None:
        """Center both analog sticks."""
        await self._send_command("CENTER_STICKS")

    async def sleep(self, duration: float) -> None:
        """Sleep for the specified duration.
        
        Args:
            duration: Sleep duration in seconds.
        """
        await self._send_command(f"SLEEP {duration}")

    def close(self) -> None:
        """Close the serial connection."""
        if self.serial:
            self.serial.close()
            self.serial = None

    def __del__(self):
        """Ensure serial connection is closed."""
        self.close()