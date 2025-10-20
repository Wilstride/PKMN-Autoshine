# Compatibility function for Poohl/joycontrol commit 3e80cb315dab8c2e2daedc80d447836b7d4d85f7
import asyncio
import time
from typing import Optional

from .base import BaseAdapter

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

	async def _create_ctrl(self):
		factory = controller_protocol_factory(self.controller_type)
		transport, protocol = await create_hid_server(factory)
		ctrl = protocol.get_controller_state()
		self._transport = transport
		self._protocol = protocol
		self._ctrl = ctrl
		return ctrl

	async def connect(self) -> None:
		"""Create controller objects and wait for a Switch connection."""
		if self._ctrl is None:
			await self._create_ctrl()

		# The controller has its own connect method
		await self._ctrl.connect()

	async def press(self, btn: str, duration: float = 0.1) -> None:
		"""Press a button using the controller state and send the report."""
		if self._ctrl is None:
			await self.connect()

		self._ctrl.button_state.set_button(btn, True)
		await self._ctrl.send()
		await asyncio.sleep(duration)
		self._ctrl.button_state.set_button(btn, False)
		await self._ctrl.send()

	async def stick(self, h: int = 0, v: int = 0) -> None:
		"""Set left stick horizontal and vertical and send the report."""
		if self._ctrl is None:
			await self.connect()

		self._ctrl.l_stick_state.set_h(h)
		self._ctrl.l_stick_state.set_v(v)
		await self._ctrl.send()

# Compatibility function for Poohl/joycontrol commit 3e80cb315dab8c2e2daedc80d447836b7d4d85f7

