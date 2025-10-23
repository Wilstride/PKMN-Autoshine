"""CLI entrypoint implementation.

Moved heavy logic from top-level `cli.py` into this module so the launcher
stays small and easier to trace/debug.
"""
from __future__ import annotations

import logging
import asyncio
import time
import sys
from adapter.base import Button, Stick
from macro_parser import parse_macro, run_macro

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] %(name)s: %(message)s'
)


async def _create_adapter():
    """Create adapter with automatic fallback: Pico W first, then joycontrol."""
    from adapter.factory import create_adapter
    
    try:
        return await create_adapter()
    except RuntimeError as e:
        print(f"\nERROR: {e}")
        sys.exit(1)


async def main():
    adapter = await _create_adapter()

    try:
        # Run setup macro
        print("\nRunning setup macro (system_open_game.txt)...")
        with open('data/macros/system_open_game.txt') as text:
            commands = parse_macro(text.read())
        await run_macro(adapter, commands)
        print("✓ Setup macro completed")

        # Run main macro in loop
        print("\nStarting main macro loop (plza_travel_cafe.txt)...")
        with open('data/macros/plza_travel_cafe.txt') as text:
            commands = parse_macro(text.read())

        print(f"Loaded {len(commands)} commands from macro file")
        count = 0
        start = time.time()
        
        try:
            while True:
                print(f"\n--- Starting cycle {count + 1} ---")
                await run_macro(adapter, commands)
                count = count + 1
                elapsed = time.time() - start
                avg_time = elapsed / count
                print(f"✓ Completed cycle {count} after {elapsed:.2f}s (avg: {avg_time:.2f}s per cycle)")
                
        except KeyboardInterrupt:
            print(f"\n\n✓ Stopped after {count} cycles ({elapsed:.2f}s total)")
            
    finally:
        # Clean up adapter connection
        if hasattr(adapter, 'close'):
            adapter.close()
            print("✓ Adapter connection closed")
