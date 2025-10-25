"""Thin launcher that delegates to the refactored webapp.server module."""

import argparse
import asyncio
import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from webapp.server import start_server


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('macro_file', nargs='?', default=None)
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--adapter-port', help='TTY port for Pico adapter (e.g., /dev/ttyACM0, /dev/ttyACM1)')
    args = parser.parse_args()
    asyncio.run(start_server(args.macro_file, host=args.host, port=args.port, adapter_port=args.adapter_port))