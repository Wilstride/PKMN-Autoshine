#!/usr/bin/env python3
"""Test script for multi-controller functionality.

This script demonstrates how to use the MultiPicoAdapter to control
multiple PicoSwitchController devices simultaneously.

Requirements:
- Multiple Raspberry Pi Pico W devices flashed with PicoSwitchController firmware
- Each device connected via USB serial (e.g., /dev/ttyACM0, /dev/ttyACM1, etc.)
- Each device paired with a separate Nintendo Switch console
"""

import asyncio
import sys
import logging
import time
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from adapter.pico import MultiPicoAdapter, PicoAdapter
from adapter.base import Button, Stick
from macros.parser import parse_macro
from macros.runner import run_macro

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


async def test_single_controller():
    """Test single controller functionality."""
    print("\n=== Testing Single Controller ===")
    
    try:
        adapter = PicoAdapter()
        await adapter.connect()
        print(f"✓ Connected to single Pico on {adapter.port}")
        
        # Test basic commands
        print("Testing basic button press...")
        await adapter.press(Button.A, 0.1)
        await asyncio.sleep(0.5)
        
        print("Testing stick movement...")
        await adapter.stick(Stick.L_STICK, 1.0, 0.0)
        await asyncio.sleep(1.0)
        await adapter.center_sticks()
        
        adapter.close()
        print("✓ Single controller test completed")
        
    except Exception as e:
        print(f"✗ Single controller test failed: {e}")


async def test_multi_controller():
    """Test multi-controller functionality."""
    print("\n=== Testing Multi-Controller ===")
    
    try:
        # Find all available Pico devices
        available_ports = PicoAdapter.find_all_pico_ports()
        print(f"Found {len(available_ports)} Pico devices: {available_ports}")
        
        if len(available_ports) < 2:
            print("⚠ Multi-controller test requires at least 2 Pico devices")
            if len(available_ports) == 1:
                print("Testing with single device in multi-controller mode...")
            else:
                print("No devices found, skipping test")
                return
        
        # Create multi-controller adapter
        adapter = MultiPicoAdapter()
        await adapter.connect()
        
        device_ids = adapter.get_device_ids()
        print(f"✓ Connected to {len(device_ids)} controllers: {device_ids}")
        
        # Test broadcasting to all devices
        print("Testing broadcast commands...")
        await adapter.press(Button.A, 0.1)  # Send to all devices
        await asyncio.sleep(0.5)
        
        # Test device-specific commands
        print("Testing device-specific commands...")
        for i, device_id in enumerate(device_ids):
            print(f"  Testing {device_id}...")
            # Different button for each device
            buttons = [Button.A, Button.B, Button.X, Button.Y]
            await adapter.press(buttons[i % len(buttons)], 0.1, device_id=device_id)
            await asyncio.sleep(0.3)
        
        # Test stick movements
        print("Testing coordinated stick movements...")
        for i, device_id in enumerate(device_ids):
            # Move sticks in different directions
            h = 1.0 if i % 2 == 0 else -1.0
            v = 0.0
            await adapter.stick(Stick.L_STICK, h, v, device_id=device_id)
        
        await asyncio.sleep(2.0)
        
        # Center all sticks
        print("Centering all sticks...")
        await adapter.center_sticks()
        
        adapter.close()
        print("✓ Multi-controller test completed")
        
    except Exception as e:
        print(f"✗ Multi-controller test failed: {e}")


async def test_macro_parsing():
    """Test multi-controller macro parsing."""
    print("\n=== Testing Multi-Controller Macro Parsing ===")
    
    try:
        # Test macro with device targeting
        macro_text = """
# Test macro with device targeting
PRESS A
pico_0:PRESS B
pico_1:STICK L 1.0 0.0
all:PRESS HOME
*:SLEEP 1
        """.strip()
        
        commands = parse_macro(macro_text)
        print("Parsed commands:")
        for cmd, args, device_id in commands:
            device_str = f" -> {device_id}" if device_id else " -> ALL"
            print(f"  {cmd} {' '.join(args)}{device_str}")
        
        print("✓ Macro parsing test completed")
        
    except Exception as e:
        print(f"✗ Macro parsing test failed: {e}")


async def test_demo_macro():
    """Test running the demo macro."""
    print("\n=== Testing Demo Macro ===")
    
    try:
        demo_macro_path = Path("data/macros/multi_controller_demo.txt")
        if not demo_macro_path.exists():
            print(f"⚠ Demo macro not found at {demo_macro_path}")
            return
        
        # Parse the demo macro
        macro_text = demo_macro_path.read_text()
        commands = parse_macro(macro_text)
        print(f"Loaded demo macro with {len(commands)} commands")
        
        # Try to run with multi-controller adapter
        try:
            adapter = MultiPicoAdapter()
            await adapter.connect()
            print(f"✓ Running demo on {len(adapter.get_device_ids())} controllers")
            
            # Run just the first few commands as a test
            test_commands = commands[:5]  # First 5 commands only
            await run_macro(adapter, test_commands)
            
            adapter.close()
            print("✓ Demo macro test completed")
            
        except Exception as e:
            print(f"⚠ Could not test with real hardware: {e}")
            print("✓ Demo macro parsing successful (dry run)")
        
    except Exception as e:
        print(f"✗ Demo macro test failed: {e}")


async def main():
    """Main test function."""
    print("PKMN-Autoshine Multi-Controller Test Suite")
    print("==========================================")
    
    # Run all tests
    await test_macro_parsing()
    await test_single_controller()
    await test_multi_controller()
    await test_demo_macro()
    
    print("\n=== Test Suite Complete ===")
    print("If all tests passed, your multi-controller setup is ready!")
    print("\nTo use multi-controller mode:")
    print("1. Connect multiple Pico W devices via USB")
    print("2. Set adapter preference to 'multi-pico' in the web UI")
    print("3. Use device targeting syntax in macros: device_id:COMMAND")
    print("4. Use 'all:' or '*:' prefix to broadcast to all devices")


if __name__ == "__main__":
    asyncio.run(main())