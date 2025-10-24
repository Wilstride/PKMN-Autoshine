"""Pico W Bluetooth adapter for Nintendo Switch controller emulation.

This module provides a Pico W adapter that communicates with custom firmware
running on a Raspberry Pi Pico W board. The firmware emulates a Nintendo Switch
Pro Controller over Bluetooth while receiving commands via USB serial.

The adapter handles:
    - Automatic Pico W device detection
    - USB serial communication with the firmware
    - Command translation from high-level API to firmware protocol
    - Error handling and connection management

Example:
    Basic usage::
    
        adapter = PicoAdapter()
        await adapter.connect()
        await adapter.press(Button.A, duration=0.5)
        await adapter.stick(Stick.L_STICK, h=0.5, v=-0.5)
        
    Manual port specification::
    
        adapter = PicoAdapter(port="/dev/ttyACM0")
        await adapter.connect()

Hardware Requirements:
    - Raspberry Pi Pico W with PKMN-Autoshine firmware flashed
    - USB cable connection to host computer
    - Firmware must be built and flashed (see PicoSwitchController/README.md)

Protocol:
    The adapter sends simple text commands over USB serial that the firmware
    translates into Bluetooth HID reports for the Nintendo Switch.
"""
from __future__ import annotations

import asyncio
import logging
import serial
import serial.tools.list_ports
from typing import Optional, Union

from adapter.base import BaseAdapter, Button, Stick

logger = logging.getLogger(__name__)


class PicoAdapter(BaseAdapter):
    """Adapter for communicating with Pico W firmware via USB serial.
    
    This adapter connects to a Raspberry Pi Pico W running the PKMN-Autoshine
    firmware and translates high-level controller commands into the simple
    text protocol the firmware expects.
    
    The adapter automatically detects Pico W devices if no port is specified,
    handles connection management, and provides error handling for common
    issues like device disconnection.
    
    Attributes:
        port: Serial port path (auto-detected if None)
        baud: Serial communication baud rate
        timeout: Timeout for serial operations in seconds
        serial: Active serial connection object
    """

    def __init__(
        self, 
        port: Optional[str] = None, 
        baud: int = 115200, 
        timeout: float = 1.0
    ) -> None:
        """Initialize the Pico adapter with connection parameters.
        
        Args:
            port: Serial port path (e.g., "/dev/ttyACM0", "COM3"). If None,
                  will attempt automatic detection of Pico W devices.
            baud: Baud rate for serial communication. Must match firmware
                  configuration (default: 115200).
            timeout: Timeout in seconds for serial read/write operations.
                    Increase for slower operations, decrease for responsiveness.
                    
        Example:
            Auto-detect Pico::
            
                adapter = PicoAdapter()
                
            Specify port manually::
            
                adapter = PicoAdapter(port="/dev/ttyACM0")
                adapter = PicoAdapter(port="COM3")  # Windows
        """
        super().__init__()
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.serial: Optional[serial.Serial] = None

    async def connect(self) -> None:
        """Establish connection to the Pico W firmware via USB serial.
        
        Attempts to connect to the specified port or auto-detects a Pico W
        device if no port was specified. Validates the connection and prepares
        the adapter for command transmission.
        
        Raises:
            RuntimeError: If no Pico W device can be found or connected
            serial.SerialException: If the serial connection fails
            OSError: If the specified port is not accessible
            
        Example:
            Connect to auto-detected device::
            
                adapter = PicoAdapter()
                await adapter.connect()  # Auto-detects port
                
            Connect to specific port::
            
                adapter = PicoAdapter(port="/dev/ttyACM0") 
                await adapter.connect()  # Uses specified port
                
        Note:
            This method must be called before any controller commands.
            The connection will block briefly while establishing communication.
        """
        if self.port is None:
            self.port = self._find_pico_port()
            if self.port is None:
                raise RuntimeError(
                    "Could not find Pico W device. Ensure:\n"
                    "1. Pico W is connected via USB\n"
                    "2. PKMN-Autoshine firmware is flashed and running\n"
                    "3. Device appears as /dev/ttyACM* (Linux) or COM* (Windows)"
                )
        
        logger.info(f"Connecting to Pico W on {self.port}")
        
        # Open serial connection in executor to avoid blocking event loop
        loop = asyncio.get_event_loop()
        try:
            self.serial = await loop.run_in_executor(
                None, 
                lambda: serial.Serial(self.port, self.baud, timeout=self.timeout)
            )
        except serial.SerialException as e:
            raise RuntimeError(f"Failed to open serial port {self.port}: {e}")
        except OSError as e:
            raise RuntimeError(f"Cannot access port {self.port}: {e}")
        
        # Allow firmware time to stabilize after connection
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