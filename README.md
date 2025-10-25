# PKMN-Autoshine

A Pokemon automation tool that bridges USB serial commands from a host application to Nintendo Switch Bluetooth controller input via Raspberry Pi Pico W firmware.

## Overview

PKMN-Autoshine consists of two main components:

1. **Host Application**: Python-based automation scripts that send controller commands over USB serial
2. **Pico W Firmware**: Custom firmware that receives USB serial commands and emulates a Nintendo Switch Pro Controller via Bluetooth

## Architecture

```
Python Automation Scripts → USB Serial → Pico W Firmware → Bluetooth → Nintendo Switch
```

The Pico W acts as a bridge, converting USB serial commands into authentic Nintendo Switch Pro Controller Bluetooth HID reports.

## Features

- **USB Serial Interface**: Send commands from any host system via standard serial communication
- **Bluetooth Controller Emulation**: Full Nintendo Switch Pro Controller compatibility via Bluetooth
- **Command Language**: Simple text-based command format for buttons, sticks, timing, and loops
- **Loop Support**: Repeat command sequences with `LOOP <count>` / `ENDLOOP` syntax
- **Setup Macro Support**: Configure one-time initialization macros that run before your main automation loop
- **Real-time Processing**: Low-latency command execution for responsive automation
- **Cross-platform Host**: Works with any system that supports USB serial (Linux, Windows, macOS)

## Hardware Requirements

- **Raspberry Pi Pico W** (for Bluetooth and USB capabilities)
- **Nintendo Switch** (with Bluetooth enabled)
- **Host Computer** (with USB port and Python support)

## Quick Start

PKMN-Autoshine automatically detects and uses the best available adapter:

1. **Pico W Adapter** (preferred) - Hardware-based, reliable, cross-platform
2. **Joycontrol Adapter** (fallback) - Software-based, Linux-only

### Option A: Pico W Setup (Recommended)

#### 1. Flash Firmware

1. Hold the BOOTSEL button on your Pico W and plug it into USB
2. Copy `firmware/build/src/autoshine_pico_firmware.uf2` to the RPI-RP2 drive
3. The Pico W will reboot and appear as a USB serial device (e.g., `/dev/ttyACM0`)

#### 2. Pair with Nintendo Switch

1. Go to Switch Settings → Controllers and Sensors → Change Grip/Order
2. Press and hold the SYNC button (or use the firmware's pairing mode)
3. The Switch should detect and connect to the "Pro Controller"

#### 3. Run Automation

```bash
# Check adapter status first (recommended)
python src/check_status.py

# Run automation with a main macro (automatically detects and uses Pico W)
python cli.py plza_travel_cafe.txt

# Run automation with setup and main macro
python cli.py plza_travel_cafe.txt --setup system_open_game.txt

# Run with specific TTY port for Pico adapter (useful for multiple instances)
python cli.py plza_travel_cafe.txt --adapter-port /dev/ttyACM0

# The setup macro runs once before the main macro starts repeating
```

### Option B: Joycontrol Fallback (Linux Only)

If no Pico W is detected, the system automatically falls back to joycontrol:

1. Install dependencies: `sudo apt install python3-dbus libhidapi-hidraw0 libbluetooth-dev bluez`
2. Configure Bluetooth as per [joycontrol documentation](https://github.com/Poohl/joycontrol)
3. Run: `python cli.py main_macro.txt` (will automatically use joycontrol if Pico W unavailable)

### Manual Adapter Selection

You can force specific adapters if needed:

```bash
# Force Pico W adapter with setup macro
python cli.py plza_travel_cafe.txt --setup system_open_game.txt

# Force joycontrol adapter  
python cli.py plza_travel_cafe.txt --adapter joycontrol

# Use specific TTY port for Pico adapter
python cli.py plza_travel_cafe.txt --adapter-port /dev/ttyACM1

# Combine setup macro with specific adapter port
python cli.py plza_travel_cafe.txt --setup system_open_game.txt --adapter-port /dev/ttyACM1
```

### Running Multiple Instances

You can run multiple instances of PKMN-Autoshine on the same system by using different TTY ports for each Pico W device:

#### Hardware Setup
1. Connect multiple Pico W boards to different USB ports
2. Each will appear as a separate TTY device (e.g., `/dev/ttyACM0`, `/dev/ttyACM1`)
3. Pair each Pico W with different Nintendo Switch consoles

#### Software Configuration

**Web Interface (Different Ports)**
```bash
# Instance 1: First Pico W on default web port
python web.py --adapter-port /dev/ttyACM0 --port 8080

# Instance 2: Second Pico W on different web port  
python web.py --adapter-port /dev/ttyACM1 --port 8081

# Access web interfaces at:
# http://localhost:8080 (Instance 1)
# http://localhost:8081 (Instance 2)
```

**CLI (Different TTY Ports)**
```bash
# Terminal 1: First Pico W
python cli.py plza_travel_cafe.txt --adapter-port /dev/ttyACM0

# Terminal 2: Second Pico W  
python cli.py plza_travel_wild_area.txt --adapter-port /dev/ttyACM1
```

This allows automation of multiple Nintendo Switch consoles simultaneously from the same host system.

## Adapter Integration Details

### Automatic Adapter Selection

The system uses the following priority order:
1. **Pico W**: If a compatible device is detected and responsive
2. **Joycontrol**: If Bluetooth and sudo access are available
3. **Error**: If no adapters are available

The adapter factory provides seamless fallback functionality, automatically detecting the best available option.

### Web Interface Integration

The web interface supports full adapter management:

```bash
# Start web server with automatic adapter selection
python web.py

# Start with specific adapter preference  
python web.py --adapter pico
python web.py --adapter joycontrol

# Start with specific TTY port for Pico adapter (useful for multiple instances)
python web.py --adapter-port /dev/ttyACM0
python web.py --adapter-port /dev/ttyACM1

# Combine adapter preference with specific port
python web.py --adapter pico --adapter-port /dev/ttyACM1

# Access web interface at http://localhost:8080
```

#### Web UI Features
- **Adapter Status Display**: Shows current adapter preference and connectivity
- **Adapter Selection**: Dropdown to choose preferred adapter:
  - "Auto-detect (Pico first)" - Default behavior
  - "Pico W (USB Serial)" - Force Pico adapter
  - "Joycontrol (Bluetooth)" - Force joycontrol adapter
- **Macro Selection**: Choose both setup and main macros:
  - "Setup Macro (runs once)" - Optional initialization macro
  - "Main Macro (repeats)" - Required repeating automation macro
- **Test Connectivity**: Button to test which adapters are available
- **Real-time Updates**: Status updates every 5 seconds

#### API Endpoints

**GET /api/adapters**
Returns list of available adapter types.
Response: `["pico", "joycontrol"]`

**GET /api/adapters/status**
Returns current adapter preference and connectivity status.
Response:
```json
{
  "preferred": null,
  "connectivity": {
    "pico": false,
    "joycontrol": true
  }
}
```

**POST /api/adapters/select**
Sets the preferred adapter type.
Request: `{"adapter": "pico"}`
Response: `{"preferred": "pico", "message": "Adapter preference updated..."}`

### Status Checking and Diagnostics

Use the diagnostic tool to check your system:

```bash
python src/check_status.py
```

This comprehensive tool shows:
- Available adapters and their dependencies
- Hardware detection results
- Bluetooth capability assessment
- Connectivity test results
- Specific recommendations for setup

### Troubleshooting by Adapter Type

#### Pico W Issues
- Ensure Pico W is flashed with retro-pico-switch firmware
- Check USB connection and permissions
- Verify device appears in system USB devices (`lsusb`)
- Try different USB ports/cables
- **Permission fix**: `sudo usermod -a -G dialout $USER` (then logout/login)
- Install dependencies: `pip install pyserial`

#### Joycontrol Issues
- Install BlueZ: `sudo apt install bluez python3-dbus libhidapi-hidraw0 libbluetooth-dev`
- Check Bluetooth adapter: `hciconfig`
- Ensure sudo access for the user
- Pair and trust the Switch before use
- Switch must be in pairing mode (Change Grip/Order)

#### General Issues
- Run `python src/check_status.py` for detailed diagnostics
- Check Python dependencies: `pip install aiohttp pyserial`
- Verify all adapter modules are importable
- Use verbose logging for debugging: add logging configuration

### 4. Send Commands

Using Python with PySerial:

```python
import serial
import time

# Open serial connection (adjust port as needed)
ser = serial.Serial('/dev/ttyACM0', 115200)
time.sleep(1)

# Send button commands
ser.write(b'PRESS a\n')
time.sleep(0.1)
ser.write(b'RELEASE a\n')

# Send stick commands (values from -1.0 to 1.0)
ser.write(b'STICK left_stick 0.8 0.5\n')

# Sleep command
ser.write(b'SLEEP 2.0\n')

# Utility commands
ser.write(b'CENTER_STICKS\n')
ser.write(b'RELEASE_ALL\n')

ser.close()
```

## Command Reference

### Button Commands
- `PRESS <button>` - Press and hold a button
- `RELEASE <button>` - Release a button

**Available buttons**: `a`, `b`, `x`, `y`, `l`, `r`, `zl`, `zr`, `plus`, `minus`, `home`, `capture`, `l_stick`, `r_stick`, `dpad_up`, `dpad_down`, `dpad_left`, `dpad_right`

### Stick Commands
- `STICK <stick> <horizontal> <vertical>` - Set analog stick position
  - `<stick>`: `left_stick` or `right_stick`  
  - `<horizontal>`, `<vertical>`: Float values from -1.0 to 1.0

### Utility Commands
- `SLEEP <seconds>` - Sleep for specified duration (float)
- `CENTER_STICKS` - Center both analog sticks to neutral position
- `RELEASE_ALL` - Release all pressed buttons
- `# comment` - Comment lines (ignored)

## Project Structure

```
PKMN-Autoshine/
├── README.md                 # This file - comprehensive documentation
├── LICENSE                   # GPL-3.0 license file
├── requirements.txt          # Python dependencies
├── cli.py                    # Main CLI launcher (auto-detects adapter)
├── web.py                    # Web interface launcher
├── src/                      # Python source code directory
│   ├── check_status.py       # Adapter status diagnostics
│   ├── macro_parser.py       # Legacy compatibility wrapper
│   ├── adapter/              # Python adapter classes
│   │   ├── base.py           # Abstract adapter interface
│   │   ├── pico.py           # Pico W USB serial adapter
│   │   ├── joycontrol.py     # Joycontrol Bluetooth adapter
│   │   └── factory.py        # Adapter selection and fallback
│   ├── cli/                  # Command-line interface implementation
│   ├── macros/               # Python macro parsing and execution
│   └── webapp/               # Web interface implementation
├── data/                     # Application data
│   └── macros/               # Macro script files
└── PicoSwitchController/     # Pico W firmware source (submodule)
    ├── src/                  # C++ source files
    ├── include/              # Header files  
    ├── build/                # Build artifacts
    └── README.md             # Firmware documentation
```

## Architecture Details

### Key Components
- `adapter/factory.py`: Central adapter selection and creation logic
- `adapter/pico.py`: Pico W adapter implementation with USB serial communication
- `adapter/joycontrol.py`: Joycontrol adapter wrapper for Bluetooth HID
- `src/check_status.py`: Comprehensive system diagnostics tool
- `cli/main.py`: Updated CLI with automatic adapter selection
- `webapp/`: Web interface with real-time adapter status display

### Adapter Selection Flow
1. System detects available adapters and their dependencies
2. Tests connectivity for each adapter in priority order
3. Selects best available adapter automatically (Pico W preferred)
4. Falls back gracefully if primary adapter fails
5. Provides detailed user feedback and status information
6. Maintains connection state and handles reconnection

### Configuration Options

#### Web Server Settings
- Default host: `0.0.0.0` (all interfaces)
- Default port: `8080`
- Adapter preference: `auto` (can be `pico`, `joycontrol`, or `auto`)

#### CLI Settings
- Adapter preference: `auto` (can be overridden with --adapter flag)
- Macro file: Required argument for automation scripts
- Verbose output available through status checking tools

## Migration from Previous Versions

If you were using the old hardcoded joycontrol system:
1. Your existing setup will continue to work as a fallback option
2. Add Pico W hardware for improved performance and reliability
3. Use `python src/check_status.py` to verify new functionality works correctly
4. Update any custom scripts to use the new CLI interface and adapter system
5. The system is fully backward compatible while providing enhanced functionality

## Adapter Status and Troubleshooting

### Check Adapter Availability

```python
from adapter.factory import get_available_adapters, test_adapter_connectivity
import asyncio

# Check which adapters have their dependencies installed
available = get_available_adapters()
print(f"Available adapters: {available}")

# Test actual connectivity
async def check_connectivity():
    status = await test_adapter_connectivity()
    for adapter, connected in status.items():
        print(f"{adapter}: {'✓ Connected' if connected else '✗ Failed'}")

asyncio.run(check_connectivity())
```

### Troubleshooting Connection Issues

**Pico W Issues:**
- Ensure firmware is properly flashed
- Check that `/dev/ttyACM0` (or similar) appears after connecting
- **Permission fix**: `sudo usermod -a -G dialout $USER` (then logout/login)
- Or run with sudo: `sudo python cli.py`
- Try `sudo dmesg | tail` to see USB enumeration messages
- Install pyserial: `pip install pyserial`

**Joycontrol Issues:**
- Ensure Bluetooth is properly configured (see joycontrol docs)
- Switch must be in pairing mode (Change Grip/Order)  
- Run with `sudo` if needed for Bluetooth access
- Check that required packages are installed

## Development

### Building Firmware

Requirements:
- Raspberry Pi Pico SDK
- CMake 3.25+
- GCC ARM toolchain

```bash
cd firmware
mkdir build && cd build
cmake ..
make -j4
```

### Python Environment

```bash
# Install dependencies
pip install pyserial  # For Pico adapter

# For joycontrol fallback (Linux only):
sudo apt install python3-dbus libhidapi-hidraw0 libbluetooth-dev bluez
sudo pip install aioconsole hid crc8

# Run automation scripts
python cli.py  # Auto-selects best adapter
```

## Macro Language

PKMN-Autoshine uses a simple text-based macro language for defining automation sequences. Macros support basic commands and control structures like loops.

### Basic Commands

```
# Comments start with # and are ignored
PRESS <button>      # Press and release a button (a, b, x, y, home, plus, etc.)
HOLD <button>       # Hold a button down (without releasing)
RELEASE <button>    # Release a button that was held
STICK <stick> <h> <v>  # Move analog stick (l/r stick, horizontal, vertical)
SLEEP <seconds>     # Wait for specified number of seconds
```

### Loop Structure

Use loops to repeat sequences of commands:

```
LOOP <count>
    # Commands to repeat
    PRESS a
    SLEEP 1
ENDLOOP
```

### Example Macro

```
# Press A button
PRESS a
SLEEP 2

# Hold R button down while doing other actions
HOLD r
PRESS a
SLEEP 1
PRESS b
RELEASE r  # Release the R button

# Repeat the following actions 5 times
LOOP 5
    # Move forward
    STICK l 0.0 1.0
    SLEEP 1.3
    # Stop
    STICK l 0.0 0.0
    SLEEP 1.3
ENDLOOP

# Final action
PRESS b
```

### Features

- **Case insensitive**: Commands can be written in any case
- **Comments**: Lines starting with `#` are ignored
- **Error validation**: Parser catches syntax errors and missing ENDLOOP statements
- **Nested loops**: Loops can be nested inside other loops (though not commonly needed)
- **Backward compatibility**: All existing macros continue to work unchanged

### Button Names

Common button names include: `a`, `b`, `x`, `y`, `l`, `r`, `zl`, `zr`, `plus`, `minus`, `home`, `capture`, `lclick`, `rclick`

### Stick Controls

- Stick names: `l` (left stick), `r` (right stick)  
- Coordinates: `-1.0` to `1.0` for both horizontal and vertical axes
- Center position: `0.0 0.0`

## Acknowledgments

This project builds upon excellent existing work in Nintendo Switch controller emulation:

- **[Poohl/joycontrol](https://github.com/Poohl/joycontrol)**: Pioneering Nintendo Switch Bluetooth controller emulation library. The Bluetooth HID implementation and Pro Controller protocol understanding in our firmware is based on their research and code.

- **[DavidPagels/retro-pico-switch](https://github.com/DavidPagels/retro-pico-switch)**: Raspberry Pi Pico-based Nintendo Switch controller adapter. Our firmware architecture, BTStack integration, and Pico W Bluetooth implementation leverages their foundation for embedded Switch controller emulation.

Special thanks to these projects for making Nintendo Switch automation accessible and providing the technical foundation that made this project possible.

## License

This project is released under the **GNU General Public License v3.0 (GPL-3.0)** due to its incorporation of concepts and implementations from GPL-3.0 licensed projects.

## Disclaimer

This tool is for educational and personal use. Please respect game terms of service and use automation responsibly.