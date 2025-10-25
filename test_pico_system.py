#!/usr/bin/env python3
"""
Test script for the new Pico-based PKMN-Autoshine architecture.

This script demonstrates the new PicoManager functionality and tests
basic device operations without requiring the web interface.
"""

import asyncio
import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from webapp.pico_manager import PicoManager


async def test_pico_system():
    """Test the new Pico system functionality."""
    print("🚀 PKMN-Autoshine Pico System Test")
    print("=" * 50)
    
    # Initialize manager
    manager = PicoManager()
    
    # Set up response callback
    def response_handler(port, response):
        print(f"[{port}] {response}")
    
    manager.set_response_callback(response_handler)
    
    try:
        # Discover devices
        print("\n📡 Discovering Pico devices...")
        ports = await manager.discover_devices()
        
        if not ports:
            print("❌ No Pico devices found!")
            print("   Make sure:")
            print("   1. Pico devices are connected via USB")
            print("   2. New firmware is flashed")
            print("   3. Devices appear as /dev/ttyACM* (Linux) or COM* (Windows)")
            return
        
        print(f"✅ Found {len(ports)} Pico device(s): {', '.join(ports)}")
        
        # Connect to all devices
        print("\n🔌 Connecting to devices...")
        connected = await manager.connect_all_devices()
        print(f"✅ Connected to {connected}/{len(ports)} devices")
        
        if connected == 0:
            print("❌ Failed to connect to any devices!")
            return
        
        # Start monitoring
        print("\n👁️  Starting device monitoring...")
        await manager.start_monitoring()
        
        # Load test macro
        test_macro = """# Test macro for PKMN-Autoshine
PRESS a
SLEEP 1.0
PRESS b  
SLEEP 1.0
PRESS x
SLEEP 2.0"""
        
        print("\n📄 Loading test macro to devices...")
        load_results = await manager.load_macro(test_macro)
        success_count = sum(1 for success in load_results.values() if success)
        print(f"✅ Loaded macro to {success_count}/{len(load_results)} devices")
        
        if success_count == 0:
            print("❌ Failed to load macro to any devices!")
            return
        
        # Start macro execution
        print("\n▶️  Starting macro execution...")
        print("   (Will run for 10 seconds, then stop)")
        start_results = await manager.start_macro()
        success_count = sum(1 for success in start_results.values() if success)
        print(f"✅ Started macro on {success_count}/{len(start_results)} devices")
        
        # Monitor for a while
        print("\n📊 Monitoring execution (press Ctrl+C to stop early)...")
        try:
            await asyncio.sleep(10)  # Run for 10 seconds
        except KeyboardInterrupt:
            print("\n⏹️  Interrupted by user")
        
        # Stop execution
        print("\n🛑 Stopping macro execution...")
        stop_results = await manager.stop_macro()
        success_count = sum(1 for success in stop_results.values() if success)
        print(f"✅ Stopped macro on {success_count}/{len(stop_results)} devices")
        
        # Show final status
        print("\n📈 Final device status:")
        status = manager.get_device_status()
        for port, device_status in status.items():
            iterations = device_status.get('iteration_count', 0)
            running = device_status.get('running_macro', False)
            state = "running" if running else "stopped"
            print(f"   {port}: {iterations} iterations, {state}")
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        await manager.cleanup()
        print("✅ Cleanup completed")


if __name__ == "__main__":
    try:
        asyncio.run(test_pico_system())
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)