"""Joycontrol Bluetooth adapter for Nintendo Switch controller emulation.

This module provides a joycontrol-based adapter that emulates a Nintendo Switch
Pro Controller over Bluetooth. It uses the joycontrol library to handle the
complex Bluetooth HID protocol and controller state management.

The adapter provides:
    - Bluetooth HID device emulation as Nintendo Switch Pro Controller
    - Direct connection to Nintendo Switch console
    - Full controller state management including buttons and analog sticks
    - Compatibility with the joycontrol library ecosystem

Example:
    Basic usage::
    
        adapter = JoycontrolAdapter()
        await adapter.connect()  # Waits for Switch to pair
        await adapter.press(Button.A, duration=0.5)
        await adapter.stick(Stick.L_STICK, h=0.5, v=-0.5)

Hardware Requirements:
    - Bluetooth adapter supporting HID device mode
    - Linux system with proper Bluetooth stack configuration
    - Nintendo Switch in controller pairing mode

Dependencies:
    This adapter requires the joycontrol library and its dependencies.
    Install with the instructions in the joycontrol documentation.

Protocol:
    Uses the joycontrol library which implements the full Nintendo Switch
    Pro Controller Bluetooth HID protocol including pairing, authentication,
    and report transmission.
"""

import asyncio
from typing import Optional, Union

from adapter.base import BaseAdapter, Button, Stick

# joycontrol imports - these may not be available on all systems
from joycontrol.controller import Controller
from joycontrol.memory import FlashMemory
from joycontrol.protocol import controller_protocol_factory
from joycontrol.server import create_hid_server

class JoycontrolAdapter(BaseAdapter):
    """Adapter implementing Nintendo Switch Pro Controller via joycontrol.

    This adapter uses the joycontrol library to emulate a Nintendo Switch
    Pro Controller over Bluetooth. It handles the complex HID protocol,
    controller state management, and Bluetooth pairing automatically.
    
    The adapter creates a virtual Pro Controller that the Nintendo Switch
    recognizes as an authentic controller, allowing full control over
    games and system navigation.
    
    Attributes:
        controller_type: Type of controller to emulate (default: PRO_CONTROLLER)
        _ctrl: Internal controller state object from joycontrol
        _transport: Bluetooth transport layer
        _protocol: Controller communication protocol
        _stick_mid: Cached middle position for analog sticks
        _stick_max_half: Cached maximum half-range for stick calculations
    """

    def __init__(self, controller_type: str = Controller.PRO_CONTROLLER) -> None:
        """Initialize the joycontrol adapter.
        
        Args:
            controller_type: Type of controller to emulate. Should be one of
                           the Controller constants from joycontrol.controller.
                           Default is PRO_CONTROLLER for full feature support.
                           
        Example:
            Create Pro Controller adapter::
            
                adapter = JoycontrolAdapter()
                
            Create Joy-Con adapter::
            
                from joycontrol.controller import Controller
                adapter = JoycontrolAdapter(Controller.JOYCON_L)
                
        Note:
            The controller type affects available buttons and features.
            PRO_CONTROLLER provides the most complete button set.
        """
        super().__init__()
        self.controller_type = controller_type
        self._ctrl: Optional[object] = None
        self._transport: Optional[object] = None
        self._protocol: Optional[object] = None

        # Stick position caching for coordinate calculations
        self._stick_mid: Optional[int] = None
        self._stick_max_half: Optional[int] = None

    async def _create_ctrl(self) -> None:
        """Create and initialize the joycontrol controller objects.
        
        Sets up the controller protocol, HID server, and transport layer
        required for Bluetooth communication with the Nintendo Switch.
        
        Raises:
            RuntimeError: If joycontrol components fail to initialize
            OSError: If Bluetooth adapter is not available or accessible
        """
        spi_flash = FlashMemory()
        factory = controller_protocol_factory(self.controller_type, spi_flash=spi_flash)
        transport, protocol = await create_hid_server(factory)
        ctrl = protocol.get_controller_state()
        self._transport = transport
        self._protocol = protocol
        self._ctrl = ctrl

    async def connect(self) -> None:
        """Establish Bluetooth connection and wait for Nintendo Switch pairing.
        
        Creates the controller objects if needed, then initiates Bluetooth
        pairing mode and waits for a Nintendo Switch to connect. The Switch
        must be in controller pairing mode for this to succeed.
        
        Raises:
            RuntimeError: If controller objects cannot be created
            ConnectionError: If Bluetooth pairing fails or times out
            OSError: If Bluetooth adapter is not available
            
        Example:
            Connect and wait for Switch::
            
                adapter = JoycontrolAdapter()
                await adapter.connect()  # Waits for Switch to pair
                print("Connected to Nintendo Switch!")
                
        Note:
            This method blocks until a Switch successfully pairs with the
            controller. Ensure the Switch is in pairing mode before calling.
        """
        if self._ctrl is None:
            await self._create_ctrl()

        # Wait for Nintendo Switch to connect and complete pairing
        await self._ctrl.connect()
    
    async def press(self, btn: Button, duration: float = 0.1) -> None:
        """Press and release a controller button.
        
        Simulates pressing a button for the specified duration. The button
        state is set to pressed, a report is sent, then after the duration
        the button is released and another report is sent.
        
        Args:
            btn: Button to press (Button enum value or compatible string)
            duration: Time to hold the button in seconds (default: 0.1)
            
        Raises:
            RuntimeError: If the adapter is not connected
            ValueError: If the button identifier is invalid
            
        Example:
            Press A button briefly::
            
                await adapter.press(Button.A)
                
            Hold B button for 1 second::
            
                await adapter.press(Button.B, duration=1.0)
                
        Note:
            Button names should match those supported by joycontrol.
            The adapter automatically handles report transmission.
        """
        if self._ctrl is None:
            await self.connect()

        self._ctrl.button_state.set_button(btn.value, True)
        await self._ctrl.send()
        await asyncio.sleep(duration)
        self._ctrl.button_state.set_button(btn.value, False)
        await self._ctrl.send()

    async def release_all_buttons(self) -> None:
        """Release all buttons known in the Button enum and send a report."""
        if self._ctrl is None:
            # nothing to do if not connected
            return
        # button_state exposes set_button(name, bool)
        for b in [
            'a','b','x','y','l','r','zl','zr','plus','minus','home','capture',
            'dpad_up','dpad_down','dpad_left','dpad_right','l_stick','r_stick'
        ]:
            try:
                self._ctrl.button_state.set_button(b, False)
            except Exception:
                pass
        await self._ctrl.send()

    async def center_sticks(self) -> None:
        """Center both sticks using calibration centers (or 0x0800 default)."""
        if self._ctrl is None:
            return
        try:
            l = getattr(self._ctrl, 'l_stick_state', None)
            r = getattr(self._ctrl, 'r_stick_state', None)
            if l is not None:
                # try to use calibration center if available
                try:
                    cal = l.get_calibration()
                    h_center = cal.h_center
                    v_center = cal.v_center
                except Exception:
                    h_center = 0x0800
                    v_center = 0x0800
                l.set_h(h_center)
                l.set_v(v_center)
            if r is not None:
                try:
                    cal = r.get_calibration()
                    h_center = cal.h_center
                    v_center = cal.v_center
                except Exception:
                    h_center = 0x0800
                    v_center = 0x0800
                r.set_h(h_center)
                r.set_v(v_center)
            await self._ctrl.send()
        except Exception:
            # swallow errors to keep this safe to call
            pass

    async def stick(self, stick: Stick = Stick.L_STICK, h: int = 0x0800, v: int = 0x0800) -> None:
        """Set chosen stick horizontal and vertical and send the report."""
        if self._ctrl is None:
            await self.connect()

        # allow h/v to be normalized floats in [-1.0, 1.0]
        def to_raw(axis_val, cal_center, cal_above, cal_below):
            # if user passed an int, assume it's already raw
            if isinstance(axis_val, int):
                raw = axis_val
                return max(0, min(0x0FFF, int(raw)))

            # clamp input percentage
            v_pct = float(axis_val)
            if v_pct < -1.0:
                v_pct = -1.0
            if v_pct > 1.0:
                v_pct = 1.0

            # cal_above and cal_below are positive spans
            if v_pct >= 0:
                raw = cal_center + v_pct * cal_above
            else:
                raw = cal_center + v_pct * cal_below  # v_pct negative -> subtract

            raw_i = int(round(raw))
            return max(0, min(0x0FFF, raw_i))

        if stick == Stick.L_STICK:
            s = getattr(self._ctrl, 'l_stick_state', None)
        elif stick == Stick.R_STICK:
            s = getattr(self._ctrl, 'r_stick_state', None)
        else:
            raise ValueError('Unknown stick')

        if s is None:
            raise ValueError('Requested stick not available on this controller')

        cal = None
        try:
            cal = s.get_calibration()
        except Exception:
            cal = None

        # horizontal calibration
        if cal is None:
            h_center = 0x0800
            h_above = 0x07FF
            h_below = 0x07FF
        else:
            h_center = cal.h_center
            h_above = cal.h_max_above_center
            h_below = cal.h_max_below_center

        # vertical calibration
        if cal is None:
            v_center = 0x0800
            v_above = 0x07FF
            v_below = 0x07FF
        else:
            v_center = cal.v_center
            v_above = cal.v_max_above_center
            v_below = cal.v_max_below_center

        raw_h = to_raw(h, h_center, h_above, h_below)
        raw_v = to_raw(v, v_center, v_above, v_below)

        # set and send
        s.set_h(raw_h)
        s.set_v(raw_v)
        await self._ctrl.send()

    def get_stick(self, stick: Stick = Stick.L_STICK):
        """Return current (h, v) tuple for the chosen stick, or None if not available."""
        if self._ctrl is None:
            return None

        if stick == Stick.L_STICK:
            s = getattr(self._ctrl, 'l_stick_state', None)
        else:
            s = getattr(self._ctrl, 'r_stick_state', None)

        if s is None:
            return None
        return (s.get_h(), s.get_v())

    def get_calibration(self, stick: Stick = Stick.L_STICK):
        """Return the calibration object applied to the stick, or None."""
        if self._ctrl is None:
            return None

        if stick == Stick.L_STICK:
            s = getattr(self._ctrl, 'l_stick_state', None)
        else:
            s = getattr(self._ctrl, 'r_stick_state', None)

        if s is None:
            return None
        try:
            return s.get_calibration()
        except Exception:
            return None

    def stick_bytes(self, stick: Stick = Stick.L_STICK):
        """Return the 3-byte packed representation for the chosen stick or None."""
        if self._ctrl is None:
            return None

        if stick == Stick.L_STICK:
            s = getattr(self._ctrl, 'l_stick_state', None)
        else:
            s = getattr(self._ctrl, 'r_stick_state', None)

        if s is None:
            return None
        try:
            return bytes(s)
        except Exception:
            return None
