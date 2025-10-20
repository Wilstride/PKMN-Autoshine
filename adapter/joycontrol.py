# Compatibility function for Poohl/joycontrol commit 3e80cb315dab8c2e2daedc80d447836b7d4d85f7
import asyncio
from typing import Union

from .base import BaseAdapter, Button

from joycontrol.protocol import controller_protocol_factory
from joycontrol.server import create_hid_server
from joycontrol.controller import Controller


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

    async def _apply_stick_calibration(self) -> None:
        """Apply a `_StickCalibration` to the chosen stick and optionally set center."""

        self._stick_mid = 0x0800
        self._stick_max_half = 0x07FF
        calibration = _StickCalibration(
            h_center=self._stick_mid,
            v_center=self._stick_mid,
            h_max_above_center=self._stick_max_half,
            v_max_above_center=self._stick_max_half,
            h_max_below_center=self._stick_max_half,
            v_max_below_center=self._stick_max_half,
        )

        self._ctrl.l_stick_state.set_calibration(calibration)
        self._ctrl.r_stick_state.set_calibration(calibration)

        # Apply by sending a report so the controller state updates
        await self._ctrl.send()

    async def _create_ctrl(self):
        factory = controller_protocol_factory(self.controller_type)
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
        await self._apply_stick_calibration()

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

    async def stick(self, stick: Stick = Stick.L_STICK, h: int = 0x07FF, v: int = 0x07FF) -> None:
        """Set chosen stick horizontal and vertical and send the report."""
        if self._ctrl is None:
            await self.connect()

        if stick == Stick.L_STICK:
            self._ctrl.l_stick_state.set_h(h)
            self._ctrl.l_stick_state.set_v(v)
        elif stick == Stick.R_STICK:
            self._ctrl.r_stick_state.set_h(h)
            self._ctrl.r_stick_state.set_v(v)
        else:
            raise ValueError('Unknown stick')

        await self._ctrl.send()
