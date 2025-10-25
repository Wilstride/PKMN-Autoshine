"""Command-line interface implementation for macro execution.

This module provides the core CLI functionality for executing macro files
using either Pico W firmware or joycontrol Bluetooth adapters. It supports
single-file execution or interactive session mode with automatic adapter
detection and fallback.

The module was separated from the top-level cli.py launcher to keep the
entry point simple while providing comprehensive CLI functionality here.

Example:
    Single macro file execution::
    
        adapter = await _create_adapter()
        await run_single_file(adapter, Path("macro.txt"))
        
    Interactive session::
    
        adapter = await _create_adapter()
        await run_interactive_session(adapter)

Note:
    This module automatically tries Pico W adapter first, then falls back
    to joycontrol if the Pico is unavailable. Users can override this
    behavior by specifying a preferred adapter type.
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from pathlib import Path
from typing import Optional

from adapter.base import BaseAdapter, Button, Stick
from macro_parser import MacroRunner, parse_macro, run_macro

logging.basicConfig(
    level=logging.DEBUG,
    format='[%(levelname)s] %(name)s: %(message)s'
)


async def _create_adapter(port: Optional[str] = None) -> BaseAdapter:
    """Create adapter with automatic fallback: Pico W first, then joycontrol.
    
    Args:
        port: Optional TTY port for Pico adapter (e.g., '/dev/ttyACM1').
    
    Returns:
        Connected adapter instance ready for macro execution.
        
    Raises:
        SystemExit: If no adapter can be connected successfully.
    """
    from adapter.factory import create_adapter
    
    try:
        return await create_adapter(port=port)
    except RuntimeError as e:
        print(f"\nERROR: {e}")
        sys.exit(1)


async def main() -> None:
    """Main CLI entry point for macro execution.
    
    Parses command-line arguments to configure macro execution with optional
    setup sequences. Supports both one-time setup macros and repeating main
    macros with real-time progress monitoring.
    
    Command-line Arguments:
        main_macro: Path to main macro file that will repeat continuously
        --setup/-s: Optional setup macro that runs once before main macro
        
    The function:
        1. Parses command-line arguments for macro files
        2. Creates and connects to an adapter (Pico W or joycontrol)
        3. Loads and validates macro files from data/macros/ directory
        4. Executes setup macro once if provided
        5. Runs main macro in a loop with progress tracking
        6. Handles graceful shutdown on Ctrl+C
        
    Raises:
        SystemExit: If macro files cannot be loaded or adapter fails to connect
    """
    parser = argparse.ArgumentParser(
        description='Run Pokemon macros with optional setup',
        epilog='Use Ctrl+C to stop execution gracefully'
    )
    parser.add_argument(
        'main_macro', 
        help='Main macro file to repeat (e.g., plza_travel_cafe.txt)'
    )
    parser.add_argument(
        '--setup', '-s', 
        help='Setup macro to run once before main macro (e.g., system_open_game.txt)'
    )
    parser.add_argument(
        '--adapter-port', 
        help='TTY port for Pico adapter (e.g., /dev/ttyACM0, /dev/ttyACM1)'
    )
    
    args = parser.parse_args()
    
    # Create and connect adapter
    adapter = await _create_adapter(args.adapter_port)

    try:
        runner = MacroRunner(adapter)
        
        # Load and validate main macro file
        main_macro_path = Path('data/macros') / args.main_macro
        try:
            with main_macro_path.open('r', encoding='utf-8') as f:
                main_commands = parse_macro(f.read())
            runner.set_commands(main_commands)
            print(f"Loaded main macro: {args.main_macro} ({len(main_commands)} commands)")
        except FileNotFoundError:
            print(f"ERROR: Main macro file not found: {main_macro_path}")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: Failed to load main macro '{args.main_macro}': {e}")
            sys.exit(1)
        
        # Load and validate setup macro if specified
        if args.setup:
            setup_macro_path = Path('data/macros') / args.setup
            try:
                with setup_macro_path.open('r', encoding='utf-8') as f:
                    setup_commands = parse_macro(f.read())
                runner.set_setup_commands(setup_commands)
                print(f"Loaded setup macro: {args.setup} ({len(setup_commands)} commands)")
            except FileNotFoundError:
                print(f"ERROR: Setup macro file not found: {setup_macro_path}")
                sys.exit(1)
            except Exception as e:
                print(f"ERROR: Failed to load setup macro '{args.setup}': {e}")
                sys.exit(1)
        
        # Initialize logging and execution monitoring
        logs = runner.logs()
        
        # Display execution plan and start runner
        print(f"\nStarting macro execution...")
        if args.setup:
            print(f"Setup: {args.setup} (runs once)")
        print(f"Main: {args.main_macro} (repeats)")
        print("Press Ctrl+C to stop\n")
        
        await runner.start()
        
        # Monitor execution with progress tracking
        cycle_count = 0
        start_time = time.time()
        
        try:
            while runner.is_running():
                try:
                    # Process log messages for progress tracking
                    msg = logs.get_nowait()
                    print(f"[LOG] {msg}")
                    
                    # Track iteration cycles for user feedback
                    if (isinstance(msg, str) and 
                        "iteration" in msg and 
                        "start" in msg):
                        cycle_count += 1
                        elapsed_time = time.time() - start_time
                        avg_cycle_time = elapsed_time / cycle_count if cycle_count > 0 else 0
                        print(f"✓ Starting cycle {cycle_count} after {elapsed_time:.2f}s "
                              f"(avg: {avg_cycle_time:.2f}s per cycle)")
                except:
                    # No logs available, wait briefly before checking again
                    await asyncio.sleep(0.1)
                    continue
                        
        except KeyboardInterrupt:
            print(f"\n\n⏹ Stopping...")
            await runner.stop()
            elapsed_time = time.time() - start_time
            print(f"✓ Stopped after {cycle_count} cycles ({elapsed_time:.2f}s total)")
            
    finally:
        # Clean up adapter connection
        if hasattr(adapter, 'close'):
            adapter.close()
            print("✓ Adapter connection closed")
