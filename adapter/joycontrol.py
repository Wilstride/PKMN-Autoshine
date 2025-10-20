# Compatibility function for Poohl/joycontrol commit 3e80cb315dab8c2e2daedc80d447836b7d4d85f7
import asyncio
from typing import Union

from .base import BaseAdapter, Button, Stick

from joycontrol.protocol import controller_protocol_factory
from joycontrol.server import create_hid_server
from joycontrol.controller import Controller
from joycontrol.memory import FlashMemory

class JoycontrolAdapter(BaseAdapter):
    """Adapter that implements controller actions using the bundled joycontrol.

    This provides async methods: connect, press, and stick which the main
    script can call without depending on concrete joycontrol internals.
    """

    def __init__(self, controller_type: str = Controller.PRO_CONTROLLER):
        self.controller_type = controller_type
        self._ctrl = None
        self._transport = None
        self._protocol = None

        self._stick_mid = None
        self._stick_max_half = None

    async def _create_ctrl(self):
        spi_flash = FlashMemory()
        factory = controller_protocol_factory(self.controller_type, spi_flash=spi_flash)
        transport, protocol = await create_hid_server(factory)
        ctrl = protocol.get_controller_state()
        self._transport = transport
        self._protocol = protocol
        self._ctrl = ctrl

    async def connect(self) -> None:
        """Create controller objects and wait for a Switch connection."""
        if self._ctrl is None:
            await self._create_ctrl()

        # The controller has its own connect method
        await self._ctrl.connect()
    
    async def press(self, btn: Button, duration: float = 0.1) -> None:
        """Press a button using the controller state and send the report.

        `btn` can be a `Button` enum member or a raw string accepted by
        `button_state.set_button`.
        """
        if self._ctrl is None:
            await self.connect()

        self._ctrl.button_state.set_button(btn.value, True)
        await self._ctrl.send()
        await asyncio.sleep(duration)
        self._ctrl.button_state.set_button(btn.value, False)
        await self._ctrl.send()

    async def stick(self, stick: Stick = Stick.L_STICK, h: int = 0x0800, v: int = 0x0800) -> None:
        """Set chosen stick horizontal and vertical and send the report."""
        if self._ctrl is None:
            await self.connect()

        # allow h/v to be normalized floats in [-1.0, 1.0]
        def to_raw(axis_val, cal_center, cal_above, cal_below):
            # if user passed an int, assume it's already raw
            if isinstance(axis_val, int):
                return axis_val
            # clamp
            v = float(axis_val)
            if v < -1.0:
                v = -1.0
            if v > 1.0:
                v = 1.0
            if v >= 0:
                return int(round(cal_center + v * cal_above))
            else:
                return int(round(cal_center + v * cal_below))

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

        # fallback symmetric center/mid if no calibration
        if cal is None:
            center = 0x0800
            above = 0x07FF
            below = -0x07FF
            # below should be negative to represent offset from center
            # Note: we store below as positive in calibration; convert
            cal_center = center
            cal_above = above
            cal_below = -above
        else:
            cal_center = cal.h_center
            cal_above = cal.h_max_above_center
            cal_below = -cal.h_max_below_center

        raw_h = to_raw(h, cal_center, cal_above, cal_below)
        raw_v = to_raw(v, cal_center, cal_above, cal_below)

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
