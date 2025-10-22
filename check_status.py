#!/usr/bin/env python3
"""Adapter status checker for PKMN-Autoshine.

This script helps diagnose adapter connectivity and dependencies.
"""

import asyncio
import sys

def check_dependencies():
    """Check if adapter dependencies are installed."""
    print("=== Dependency Check ===")
    
    # Check pyserial for Pico adapter
    try:
        import serial
        import serial.tools.list_ports
        print("✓ PySerial installed (Pico adapter available)")
        pico_available = True
    except ImportError:
        print("✗ PySerial not installed (Pico adapter unavailable)")
        print("  Install with: pip install pyserial")
        pico_available = False
    
    # Check joycontrol dependencies
    try:
        import joycontrol
        print("✓ Joycontrol installed (Joycontrol adapter available)")
        joycontrol_available = True
    except ImportError:
        print("✗ Joycontrol not installed (Joycontrol adapter unavailable)")
        print("  Install with joycontrol setup instructions")
        joycontrol_available = False
    
    return pico_available, joycontrol_available

def check_hardware():
    """Check for connected Pico W devices."""
    print("\n=== Hardware Check ===")
    
    try:
        import serial.tools.list_ports
        
        ports = serial.tools.list_ports.comports()
        pico_ports = []
        
        for port in ports:
            # Check for Raspberry Pi Pico
            if port.vid == 0x2E8A:  # Raspberry Pi Foundation VID
                pico_ports.append(port)
                print(f"✓ Pico device found: {port.device}")
                print(f"  Description: {port.description}")
                print(f"  VID:PID: {port.vid:04X}:{port.pid:04X}")
            elif any(keyword in (port.description or "").lower() 
                    for keyword in ["pico", "rp2040", "raspberry"]):
                pico_ports.append(port)
                print(f"? Possible Pico device: {port.device}")
                print(f"  Description: {port.description}")
        
        if not pico_ports:
            print("✗ No Pico W devices detected")
            print("  Make sure firmware is flashed and device is connected")
        
        return len(pico_ports) > 0
        
    except ImportError:
        print("✗ Cannot check hardware (pyserial not installed)")
        return False

async def test_connectivity():
    """Test actual adapter connectivity."""
    print("\n=== Connectivity Test ===")
    
    try:
        from adapter.factory import test_adapter_connectivity
        
        results = await test_adapter_connectivity()
        
        for adapter_name, connected in results.items():
            if connected:
                print(f"✓ {adapter_name.title()} adapter: Connected successfully")
            else:
                print(f"✗ {adapter_name.title()} adapter: Connection failed")
        
        return any(results.values())
        
    except Exception as e:
        print(f"✗ Connectivity test failed: {e}")
        return False

async def main():
    """Run all diagnostic checks."""
    print("PKMN-Autoshine Adapter Status Checker")
    print("=" * 40)
    
    # Check dependencies
    pico_deps, joycontrol_deps = check_dependencies()
    
    # Check hardware
    pico_hardware = check_hardware() if pico_deps else False
    
    # Test connectivity
    connectivity = await test_connectivity()
    
    # Summary
    print("\n=== Summary ===")
    
    if pico_hardware:
        print("✓ Pico W adapter ready - this will be used by default")
    elif joycontrol_deps:
        print("✓ Joycontrol adapter available - will be used as fallback")
    else:
        print("✗ No adapters available!")
        print("  Install pyserial for Pico support or joycontrol for Bluetooth")
        sys.exit(1)
    
    if connectivity:
        print("✓ At least one adapter connected successfully")
        print("\nYou can now run: python cli.py")
    else:
        print("✗ No adapters could connect")
        print("\nTroubleshooting needed before running automation")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())