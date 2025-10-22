"""Test script for Pico adapter.

This script demonstrates how to use the Pico adapter to send commands
to the Pico W firmware.
"""

import asyncio
import logging
from adapter.pico import PicoAdapter
from adapter.base import Button, Stick

logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(name)s: %(message)s'
)

async def test_pico_adapter():
    """Test the Pico adapter functionality."""
    adapter = PicoAdapter()
    
    try:
        # Connect to the Pico
        print("Connecting to Pico W...")
        await adapter.connect()
        print("Connected!")
        
        # Test basic button presses
        print("Testing button presses...")
        await adapter.press(Button.A, 0.1)
        await asyncio.sleep(0.5)
        
        await adapter.press(Button.B, 0.1)
        await asyncio.sleep(0.5)
        
        await adapter.press(Button.HOME, 0.1)
        await asyncio.sleep(0.5)
        
        # Test analog stick movement
        print("Testing analog stick movement...")
        await adapter.stick(Stick.L_STICK, 1.0, 0.0)  # Full right
        await asyncio.sleep(1.0)
        
        await adapter.stick(Stick.L_STICK, -1.0, 0.0)  # Full left
        await asyncio.sleep(1.0)
        
        await adapter.stick(Stick.L_STICK, 0.0, 1.0)  # Full up
        await asyncio.sleep(1.0)
        
        await adapter.stick(Stick.L_STICK, 0.0, -1.0)  # Full down
        await asyncio.sleep(1.0)
        
        # Center sticks
        print("Centering sticks...")
        await adapter.center_sticks()
        
        print("Test completed successfully!")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        adapter.close()

if __name__ == '__main__':
    asyncio.run(test_pico_adapter())