# Pico W Bluetooth Controller Setup Guide

This guide explains how to set up and use the custom Raspberry Pi Pico W firmware to control a Nintendo Switch via Bluetooth.

## Overview

The custom firmware turns a Raspberry Pi Pico W into a Nintendo Switch Pro Controller that:
- Connects to the Switch via Bluetooth 
- Receives commands from your computer via USB serial
- Executes those commands as controller inputs on the Switch

This provides a more reliable and portable alternative to the Linux-based Joycontrol solution.

## Hardware Requirements

- **Raspberry Pi Pico W** (the W variant with WiFi/Bluetooth is required)
- USB cable (USB-A to Micro-USB)
- Computer running the Autoshine application

## Firmware Setup

### 1. Build the Firmware

First, you need to build the custom firmware:

```bash
# Set up Pico SDK (if not already done)
export PICO_SDK_PATH=/path/to/pico-sdk

# Navigate to firmware directory
cd firmware

# Create build directory and compile
mkdir build
cd build
cmake ..
make
```

This creates `autoshine_pico_firmware.uf2` in the build directory.

### 2. Flash the Firmware

1. **Enter bootloader mode**: Hold down the BOOTSEL button on your Pico W while connecting it to your computer via USB
2. **Flash firmware**: The Pico will appear as a USB drive called "RPI-RP2". Copy the `autoshine_pico_firmware.uf2` file to this drive
3. **Automatic reboot**: The Pico will automatically reboot with the new firmware

### 3. Verify Installation

After flashing, the Pico should:
- Show up as a new serial device on your computer (e.g., `/dev/ttyACM0` on Linux, `COM3` on Windows)
- Start broadcasting as "Pro Controller" for Bluetooth pairing
- Accept commands via the serial connection

## Nintendo Switch Setup

### Pairing with Switch

1. **Prepare your Switch**: Go to System Settings → Controllers and Sensors → Change Grip/Order
2. **Power on Pico**: Make sure your Pico W is powered and running the firmware
3. **Automatic pairing**: The Switch should detect "Pro Controller" and pair automatically
4. **Confirm connection**: The Switch should show the controller as connected

### Troubleshooting Pairing

- If pairing fails, power cycle the Pico W and try again
- Ensure the Switch is in pairing mode before the Pico starts up
- Check that no other Pro Controllers are connected to the Switch

## Software Setup

### Install Dependencies

Install the required Python package for serial communication:

```bash
pip install pyserial>=3.5
```

### Test the Connection

Use the test script to verify everything is working:

```bash
python test_pico.py
```

This will:
- Automatically find and connect to your Pico W
- Send test commands (button presses and stick movements)
- Display any errors

### Run Macros with Pico Adapter

Use the flexible CLI script to run macros with the Pico adapter:

```bash
# Run a single macro
python cli_flexible.py --adapter pico --macro data/macros/plza_travel_cafe.txt

# Run with setup macro first
python cli_flexible.py --adapter pico --setup-only --macro data/macros/plza_travel_cafe.txt

# Run in continuous loop
python cli_flexible.py --adapter pico --loop --macro data/macros/plza_travel_cafe.txt
```

## Command Reference

The Pico firmware accepts the same commands as the main Autoshine application:

### Button Commands
```
PRESS <button>      # Press and immediately release a button
RELEASE <button>    # Release a specific button
```

**Available buttons:**
- `a`, `b`, `x`, `y` - Face buttons
- `l`, `r`, `zl`, `zr` - Shoulder buttons  
- `plus`, `minus` - System buttons
- `home`, `capture` - Special buttons
- `l_stick`, `r_stick` - Analog stick click buttons
- `dpad_up`, `dpad_down`, `dpad_left`, `dpad_right` - D-pad directions

### Analog Stick Commands
```
STICK <stick> <h> <v>   # Set stick position
CENTER_STICKS           # Center both sticks
```

**Stick names:** `l_stick`, `r_stick`  
**Coordinates:** `-1.0` to `1.0` for both horizontal (h) and vertical (v) axes

### Utility Commands
```
SLEEP <seconds>     # Wait for specified duration
RELEASE_ALL         # Release all buttons
# comment           # Comment lines (ignored)
```

### Example Macro
```
# Open game from home screen
PRESS home
SLEEP 0.5
PRESS a
SLEEP 2.0

# Move character
STICK l_stick 0.8 0.0
SLEEP 1.0
STICK l_stick 0.0 0.0
```

## Advantages Over Joycontrol

### Reliability
- **No Bluetooth stack issues**: Uses dedicated Bluetooth hardware
- **No Linux dependencies**: Works on Windows, Mac, and Linux
- **Consistent timing**: Hardware-based timing for precise macro execution

### Portability  
- **Plug-and-play**: Just connect the Pico W via USB
- **Cross-platform**: Works with any OS that supports USB serial
- **No root privileges**: Doesn't require administrator access

### Performance
- **Lower latency**: Direct hardware communication
- **Better stability**: Dedicated microcontroller for controller functions
- **No interference**: Isolated from host OS Bluetooth issues

## Troubleshooting

### Serial Connection Issues

**Problem**: Cannot find Pico W device
- Verify the firmware is flashed correctly
- Check that the USB cable supports data (not just power)
- Try a different USB port

**Problem**: Commands not working
- Check serial output for error messages
- Verify the Switch is properly paired
- Ensure macro syntax is correct

### Bluetooth Issues

**Problem**: Pico won't pair with Switch
- Power cycle the Pico W
- Clear Bluetooth cache on Switch (unpair all controllers)
- Ensure Switch is in pairing mode first

**Problem**: Connection drops during use  
- Check USB cable connection
- Ensure Pico W has stable power
- Avoid interference from other Bluetooth devices

### Performance Issues

**Problem**: Delayed or missed inputs
- Reduce command frequency in macros
- Check for USB interference 
- Use shorter USB cables if possible

**Problem**: Inconsistent macro timing
- Adjust `SLEEP` durations in macros
- Account for game loading times
- Test timing with manual execution first

## Technical Details

### Communication Protocol
- **Baud rate**: 115200
- **Data format**: 8 data bits, no parity, 1 stop bit
- **Flow control**: None
- **Line ending**: `\n` (newline)

### Bluetooth Implementation
- **Profile**: HID (Human Interface Device)
- **Device name**: "Pro Controller"
- **Vendor ID**: 0x057E (Nintendo)
- **Product ID**: 0x2009 (Pro Controller)

### Hardware Resources Used
- **Bluetooth**: CYW43 chip on Pico W
- **USB**: Native USB device capability
- **Memory**: ~100KB flash, ~20KB RAM
- **GPIO**: None (all communication via USB/Bluetooth)

This setup provides a robust, cross-platform solution for Nintendo Switch automation using your existing Autoshine macros.