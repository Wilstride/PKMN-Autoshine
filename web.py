"""Thin launcher that delegates to the refactored webapp.server module."""

import argparse
import asyncio

from webapp.server import start_server


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('macro_file', nargs='?', default=None)
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8080)
    args = parser.parse_args()
    asyncio.run(start_server(args.macro_file, host=args.host, port=args.port))