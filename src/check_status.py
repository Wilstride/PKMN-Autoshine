#!/usr/bin/env python3
"""Adapter status checker and diagnostic tool for PKMN-Autoshine.

This script provides comprehensive diagnostics for Nintendo Switch controller
adapter connectivity and dependencies. It helps troubleshoot common issues
with both Pico W firmware and joycontrol Bluetooth adapters.

The tool performs:
    - Dependency availability checks
    - Hardware device detection
    - Adapter connectivity testing
    - Configuration validation

Example:
    Run diagnostics::
    
        $ python check_status.py
        
    Check specific adapter::
    
        $ python check_status.py --adapter pico
        $ python check_status.py --adapter joycontrol

Typical usage:
    Run this script when experiencing connection issues or setting up
    the system for the first time to verify all components are working.
"""

import argparse
import asyncio
import sys
from typing import Tuple


def check_dependencies() -> Tuple[bool, bool]:
    """Check availability of adapter dependencies.
    
    Verifies that required Python packages are installed for each
    adapter type and provides installation guidance if missing.
    
    Returns:
        Tuple of (pico_available, joycontrol_available) indicating
        which adapters have their dependencies satisfied.
        
    Example:
        Check what adapters are available::
        
            pico_ok, joy_ok = check_dependencies()
            if not pico_ok and not joy_ok:
                print("No adapters available!")
    """
    print("=== Dependency Check ===")
    
    # Check pyserial package for Pico adapter support
    try:
        import serial
        import serial.tools.list_ports
        print("✓ PySerial installed (Pico adapter available)")
        pico_available = True
    except ImportError:
        print("✗ PySerial not installed (Pico adapter unavailable)")
        print("  Install with: pip install pyserial")
        pico_available = False
    
    # Check joycontrol package for Bluetooth adapter support
    try:
        import joycontrol
        print("✓ Joycontrol installed (Joycontrol adapter available)")
        joycontrol_available = True
    except ImportError:
        print("✗ Joycontrol not installed (Joycontrol adapter unavailable)")
        print("  Install with joycontrol setup instructions")
        joycontrol_available = False
    
    return pico_available, joycontrol_available

def check_hardware() -> bool:
    """Detect and validate connected Pico W hardware devices.
    
    Scans USB serial ports for Raspberry Pi Pico devices that could
    be running the PKMN-Autoshine firmware. Uses vendor/product IDs
    and device descriptions to identify potential Pico devices.
    
    Returns:
        True if at least one Pico device is detected, False otherwise.
        
    Example:
        Check for Pico hardware::
        
            if check_hardware():
                print("Pico devices available")
            else:
                print("No Pico devices found")
                
    Note:
        This only detects the hardware presence, not whether the correct
        firmware is loaded. Use test_connectivity() for full validation.
    """
    print("\n=== Hardware Check ===")
    
    try:
        import serial.tools.list_ports
        
        ports = serial.tools.list_ports.comports()
        pico_ports = []
        
        for port in ports:
            # Check for official Raspberry Pi Foundation vendor ID
            if port.vid == 0x2E8A:  # Raspberry Pi Foundation VID
                pico_ports.append(port)
                print(f"✓ Pico device found: {port.device}")
                print(f"  Description: {port.description}")
                print(f"  VID:PID: {port.vid:04X}:{port.pid:04X}")
            elif any(keyword in (port.description or "").lower() 
                    for keyword in ["pico", "rp2040", "raspberry"]):
                # Check for devices that might be Picos with different IDs
                pico_ports.append(port)
                print(f"? Possible Pico device: {port.device}")
                print(f"  Description: {port.description}")
        
        if not pico_ports:
            print("✗ No Pico W devices detected")
            print("  Make sure firmware is flashed and device is connected")
            return False
        
        return True
        
    except ImportError:
        print("✗ Cannot check hardware (pyserial not installed)")
        return False


async def test_connectivity() -> bool:
    """Test actual connectivity to available adapters.
    
    Attempts to create and connect to each available adapter type to
    verify they are not just dependency-available but actually functional.
    This provides the most accurate assessment of adapter readiness.
    
    Returns:
        True if at least one adapter connects successfully, False if
        all adapters fail to connect.
        
    Example:
        Test adapter connectivity::
        
            if await test_connectivity():
                print("Ready to run macros")
            else:
                print("Connection issues need resolution")
                
    Note:
        This performs actual connection attempts which may be slow and
        could temporarily interfere with other applications using the
        same hardware devices.
    """
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


async def main() -> None:
    """Run comprehensive diagnostic checks for adapter status.
    
    Performs a complete diagnostic sequence including dependency checks,
    hardware detection, and connectivity testing. Provides detailed
    feedback and guidance for any issues found.
    
    The diagnostic sequence:
        1. Check Python package dependencies
        2. Scan for Pico W hardware devices  
        3. Test actual adapter connectivity
        4. Provide summary and recommendations
        
    Exits with status code 1 if no working adapters are found.
    """
    print("PKMN-Autoshine Adapter Status Checker")
    print("=" * 40)
    
    # Check package dependencies first
    pico_deps, joycontrol_deps = check_dependencies()
    
    # Check for Pico hardware if dependencies are available
    pico_hardware = check_hardware() if pico_deps else False
    
    # Test actual connectivity to available adapters
    connectivity = await test_connectivity()
    
    # Provide summary and recommendations
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
        print("\nYou can now run: python cli.py <macro_file>")
    else:
        print("✗ No adapters could connect")
        print("\nTroubleshooting needed before running automation")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())