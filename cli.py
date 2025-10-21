"""Thin CLI launcher that delegates to `cli.main` implementation."""

import asyncio

from cli.main import main


if __name__ == '__main__':
    asyncio.run(main())
