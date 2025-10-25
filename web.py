"""Web launcher for PKMN-Autoshine Pico Controller Management.

This launcher now uses the new Pico-based architecture where the web service
focuses on configuration and monitoring, while the PicoSwitchController
firmware handles macro execution directly.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from webapp.pico_server import start_pico_server
from webapp.server import start_server  # Keep old server available


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='PKMN-Autoshine Web Control Interface')
    parser.add_argument('--host', default='0.0.0.0', help='Host address to bind to')
    parser.add_argument('--port', type=int, default=8080, help='Port to listen on')
    parser.add_argument('--legacy', action='store_true', 
                        help='Use legacy server with macro execution (requires macro_file and adapter-port)')
    
    # Legacy mode arguments
    parser.add_argument('macro_file', nargs='?', default=None,
                        help='Initial macro file to load (legacy mode only)')
    parser.add_argument('--adapter-port', 
                        help='TTY port for Pico adapter in legacy mode (e.g., /dev/ttyACM0)')
    
    args = parser.parse_args()
    
    if args.legacy:
        print("Starting in legacy mode...")
        asyncio.run(start_server(args.macro_file, host=args.host, port=args.port, 
                                adapter_port=args.adapter_port))
    else:
        print("Starting Pico Controller Management Server...")
        print("This new architecture allows direct macro execution on Pico devices.")
        asyncio.run(start_pico_server(host=args.host, port=args.port))