"""Thin CLI launcher that delegates to `cli.main` implementation."""

import asyncio
import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from cli.main import main


if __name__ == '__main__':
    asyncio.run(main())
