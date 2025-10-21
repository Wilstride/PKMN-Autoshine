"""CLI entrypoint implementation.

Moved heavy logic from top-level `cli.py` into this module so the launcher
stays small and easier to trace/debug.
"""
from __future__ import annotations

import logging
import asyncio
import time
from adapter.joycontrol import JoycontrolAdapter
from adapter.base import Button, Stick
from macro_parser import parse_macro, run_macro

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] %(name)s: %(message)s'
)


async def _create_adapter():
    adapter = JoycontrolAdapter()
    await adapter.connect()
    return adapter


async def main():
    adapter = await _create_adapter()

    with open('data/macros/system_open_game.txt') as text:
        commands = parse_macro(text.read())
    await run_macro(adapter, commands)

    with open('data/macros/plza_travel_cafe.txt') as text:
        commands = parse_macro(text.read())

    print(commands)
    count = 0
    start = time.time()
    while True:
        await run_macro(adapter, commands)
        count = count + 1
        elapsed = time.time() - start
        print(f"Reset {count} after {round(elapsed, 2)} seconds ({round(elapsed/count, 2)} spr)")
