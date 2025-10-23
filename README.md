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
- **Command Language**: Simple text-based command format for buttons, sticks, and timing
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
python check_status.py

# Run automation (automatically detects and uses Pico W)
python cli.py
```

### Option B: Joycontrol Fallback (Linux Only)

If no Pico W is detected, the system automatically falls back to joycontrol:

1. Install dependencies: `sudo apt install python3-dbus libhidapi-hidraw0 libbluetooth-dev bluez`
2. Configure Bluetooth as per [joycontrol documentation](https://github.com/Poohl/joycontrol)
3. Run: `python cli.py` (will automatically use joycontrol if Pico W unavailable)

### Manual Adapter Selection

Use the flexible CLI for explicit adapter control:

```bash
# Force Pico W adapter
python cli_flexible.py --adapter pico --macro data/macros/plza_travel_cafe.txt

# Force joycontrol adapter  
python cli_flexible.py --adapter joycontrol --macro data/macros/plza_travel_cafe.txt --loop
```

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
├── README.md                 # This file  
├── cli.py                    # Main CLI (auto-detects adapter)
├── cli_flexible.py           # CLI with manual adapter selection
├── check_status.py           # Adapter status diagnostics
├── firmware/                 # Pico W firmware source
│   ├── src/                  # C++ source files
│   ├── include/              # Header files  
│   ├── build/                # Build artifacts
│   └── README.md             # Firmware documentation
├── adapter/                  # Python adapter classes
│   ├── base.py               # Abstract adapter interface
│   ├── pico.py               # Pico W USB serial adapter
│   ├── joycontrol.py         # Joycontrol Bluetooth adapter
│   └── factory.py            # Adapter selection and fallback
├── cli/                      # Command-line interface implementation
├── data/macros/              # Macro script files
├── macros/                   # Python macro system
└── webapp/                   # Web interface (optional)
```

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

## Acknowledgments

This project builds upon excellent existing work in Nintendo Switch controller emulation:

- **[Poohl/joycontrol](https://github.com/Poohl/joycontrol)**: Pioneering Nintendo Switch Bluetooth controller emulation library. The Bluetooth HID implementation and Pro Controller protocol understanding in our firmware is based on their research and code.

- **[DavidPagels/retro-pico-switch](https://github.com/DavidPagels/retro-pico-switch)**: Raspberry Pi Pico-based Nintendo Switch controller adapter. Our firmware architecture, BTStack integration, and Pico W Bluetooth implementation leverages their foundation for embedded Switch controller emulation.

Special thanks to these projects for making Nintendo Switch automation accessible and providing the technical foundation that made this project possible.

## License

This project is released under the **GNU General Public License v3.0 (GPL-3.0)** due to its incorporation of concepts and implementations from GPL-3.0 licensed projects.

## Disclaimer

This tool is for educational and personal use. Please respect game terms of service and use automation responsibly.