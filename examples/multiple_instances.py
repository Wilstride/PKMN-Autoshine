#!/usr/bin/env python3
"""
Example script demonstrating how to run multiple PKMN-Autoshine instances.

This script shows how you would set up multiple instances to control
different Nintendo Switch consoles using different TTY ports.
"""

import subprocess
import sys
import time

def run_multiple_instances():
    """Example of running multiple instances with different adapter ports."""
    
    print("PKMN-Autoshine Multiple Instance Example")
    print("=" * 50)
    print()
    
    # Check available TTY devices
    print("Checking for available TTY devices...")
    try:
        result = subprocess.run(['ls', '/dev/ttyACM*'], 
                              capture_output=True, text=True, check=False)
        if result.returncode == 0:
            devices = result.stdout.strip().split('\n')
            print(f"Found TTY devices: {devices}")
        else:
            print("No TTY devices found (/dev/ttyACM*)")
            devices = []
    except Exception as e:
        print(f"Error checking TTY devices: {e}")
        devices = []
    
    print()
    
    # Example commands for multiple instances
    examples = [
        {
            'name': 'Web Interface Instance 1',
            'command': ['python3', 'web.py', '--adapter-port', '/dev/ttyACM0', '--port', '8080'],
            'description': 'Web interface on port 8080 using first Pico W'
        },
        {
            'name': 'Web Interface Instance 2', 
            'command': ['python3', 'web.py', '--adapter-port', '/dev/ttyACM1', '--port', '8081'],
            'description': 'Web interface on port 8081 using second Pico W'
        },
        {
            'name': 'CLI Instance 1',
            'command': ['python3', 'cli.py', 'plza_travel_cafe.txt', '--adapter-port', '/dev/ttyACM0'],
            'description': 'CLI automation using first Pico W'
        },
        {
            'name': 'CLI Instance 2',
            'command': ['python3', 'cli.py', 'plza_travel_wild_area.txt', '--adapter-port', '/dev/ttyACM1'],
            'description': 'CLI automation using second Pico W'
        }
    ]
    
    print("Example commands for running multiple instances:")
    print()
    
    for i, example in enumerate(examples, 1):
        print(f"{i}. {example['name']}")
        print(f"   Description: {example['description']}")
        print(f"   Command: {' '.join(example['command'])}")
        print()
    
    print("Usage Notes:")
    print("- Each Pico W device will appear as a separate TTY port (/dev/ttyACMX)")
    print("- Use different --port values for multiple web instances")
    print("- Use different --adapter-port values to specify which Pico W to use")
    print("- Each instance can control a different Nintendo Switch console")
    print("- Run instances in separate terminal windows/screens")
    print()
    
    if len(devices) >= 2:
        print("✓ You have multiple TTY devices available for testing!")
    elif len(devices) == 1:
        print("⚠ Only one TTY device found. Connect more Pico W devices for multiple instances.")
    else:
        print("⚠ No TTY devices found. Connect Pico W devices to test multiple instances.")


if __name__ == '__main__':
    run_multiple_instances()