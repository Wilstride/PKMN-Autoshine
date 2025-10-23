"""CLI entrypoint implementation.

Moved heavy logic from top-level `cli.py` into this module so the launcher
stays small and easier to trace/debug.
"""
from __future__ import annotations

import logging
import asyncio
import time
import sys
import argparse
from adapter.base import Button, Stick
from macro_parser import parse_macro, run_macro, MacroRunner

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
    parser = argparse.ArgumentParser(description='Run Pokemon macros with optional setup')
    parser.add_argument('main_macro', help='Main macro file to repeat (e.g., plza_travel_cafe.txt)')
    parser.add_argument('--setup', '-s', help='Setup macro to run once before main macro (e.g., system_open_game.txt)')
    
    args = parser.parse_args()
    
    adapter = await _create_adapter()

    try:
        runner = MacroRunner(adapter)
        
        # Load main macro
        try:
            with open(f'data/macros/{args.main_macro}') as f:
                main_commands = parse_macro(f.read())
            runner.set_commands(main_commands)
            print(f"Loaded main macro: {args.main_macro} ({len(main_commands)} commands)")
        except Exception as e:
            print(f"ERROR: Failed to load main macro '{args.main_macro}': {e}")
            sys.exit(1)
        
        # Load setup macro if specified
        if args.setup:
            try:
                with open(f'data/macros/{args.setup}') as f:
                    setup_commands = parse_macro(f.read())
                runner.set_setup_commands(setup_commands)
                print(f"Loaded setup macro: {args.setup} ({len(setup_commands)} commands)")
            except Exception as e:
                print(f"ERROR: Failed to load setup macro '{args.setup}': {e}")
                sys.exit(1)
        
        # Use the runner's built-in logging
        logs = runner.logs()
        
        # Start the runner
        print(f"\nStarting macro execution...")
        if args.setup:
            print(f"Setup: {args.setup} (runs once)")
        print(f"Main: {args.main_macro} (repeats)")
        print("Press Ctrl+C to stop\n")
        
        await runner.start()
        
        # Monitor logs and provide feedback
        count = 0
        start = time.time()
        
        try:
            while runner.is_running():
                try:
                    # Get log messages with a timeout
                    msg = await asyncio.wait_for(asyncio.to_thread(logs.get), timeout=1.0)
                    print(f"[LOG] {msg}")
                    
                    # Track iterations
                    if "iteration" in msg and "start" in msg:
                        count += 1
                        elapsed = time.time() - start
                        avg_time = elapsed / count if count > 0 else 0
                        print(f"✓ Starting cycle {count} after {elapsed:.2f}s (avg: {avg_time:.2f}s per cycle)")
                        
                except asyncio.TimeoutError:
                    # No logs available, continue
                    continue
                except Exception as e:
                    print(f"Error reading logs: {e}")
                    break
                    
        except KeyboardInterrupt:
            print(f"\n\n⏹ Stopping...")
            await runner.stop()
            elapsed = time.time() - start
            print(f"✓ Stopped after {count} cycles ({elapsed:.2f}s total)")
            
    finally:
        # Clean up adapter connection
        if hasattr(adapter, 'close'):
            adapter.close()
            print("✓ Adapter connection closed")
