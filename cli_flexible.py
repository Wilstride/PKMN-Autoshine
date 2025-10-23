"""CLI script that can use either Joycontrol or Pico adapter.

This script allows you to choose between the existing Joycontrol adapter
(which requires Linux and Bluetooth setup) or the new Pico adapter
(which uses a Pico W with custom firmware).
"""

import asyncio
import argparse
import logging
import time
from macro_parser import parse_macro, run_macro

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(name)s: %(message)s'
)

async def create_adapter(adapter_type: str):
    """Create the specified adapter type."""
    if adapter_type == 'joycontrol':
        from adapter.joycontrol import JoycontrolAdapter
        adapter = JoycontrolAdapter()
    elif adapter_type == 'pico':
        from adapter.pico import PicoAdapter
        adapter = PicoAdapter()
    else:
        raise ValueError(f"Unknown adapter type: {adapter_type}")
    
    await adapter.connect()
    return adapter

async def main():
    parser = argparse.ArgumentParser(description='Autoshine CLI with adapter selection')
    parser.add_argument('--adapter', choices=['joycontrol', 'pico'], default='pico',
                       help='Adapter to use for controller communication')
    parser.add_argument('--macro', required=True,
                       help='Path to macro file to run')
    parser.add_argument('--loop', action='store_true',
                       help='Run the macro in a continuous loop')
    parser.add_argument('--setup-only', action='store_true',
                       help='Run setup macro once, then start main macro')
    
    args = parser.parse_args()
    
    print(f"Using {args.adapter} adapter")
    adapter = await create_adapter(args.adapter)
    
    try:
        if args.setup_only:
            # Run setup macro first
            print("Running setup macro...")
            with open('data/macros/system_open_game.txt') as f:
                setup_commands = parse_macro(f.read())
            await run_macro(adapter, setup_commands)
            print("Setup completed")
        
        # Load main macro
        print(f"Loading macro: {args.macro}")
        with open(args.macro) as f:
            commands = parse_macro(f.read())
        
        if args.loop:
            print("Running macro in loop mode...")
            count = 0
            start = time.time()
            while True:
                await run_macro(adapter, commands)
                count += 1
                elapsed = time.time() - start
                print(f"Completed cycle {count} after {elapsed:.2f}s ({elapsed/count:.2f}s per cycle)")
        else:
            print("Running macro once...")
            await run_macro(adapter, commands)
            print("Macro completed")
            
    finally:
        if hasattr(adapter, 'close'):
            adapter.close()

if __name__ == '__main__':
    asyncio.run(main())