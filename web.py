"""Web launcher for PKMN-Autoshine Pico Controller.

Clean, minimal server for:
- Macro file management
- Multi-Pico device management
- Uploading macros to Pico devices
- Sending control commands
"""

import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from webapp.core.server import start_server


if __name__ == '__main__':
    try:
        # Parse optional port argument
        port = 8080
        if len(sys.argv) > 1:
            try:
                port = int(sys.argv[1])
            except ValueError:
                print(f"Invalid port: {sys.argv[1]}")
                sys.exit(1)
        
        # Start the server
        start_server(port=port)
    except KeyboardInterrupt:
        print("\n\n✓ Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Server error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
