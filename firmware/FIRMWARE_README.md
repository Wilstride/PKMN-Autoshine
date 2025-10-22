# Autoshine Pico Firmware

Custom firmware for Raspberry Pi Pico W that acts as a Nintendo Switch Pro Controller via Bluetooth, taking commands over USB serial from the main Autoshine application.

## Features

- **Bluetooth Switch Controller Emulation**: Emulates a Nintendo Switch Pro Controller via Bluetooth
- **USB Serial Command Interface**: Receives commands from PC via USB serial connection
- **Comprehensive Button Support**: All Switch buttons including D-pad, face buttons, shoulder buttons, sticks, and system buttons
- **Analog Stick Control**: Full analog stick positioning with floating-point precision
- **Real-time Command Processing**: Immediate response to incoming commands

## Hardware Requirements

- Raspberry Pi Pico W (with CYW43 Bluetooth/WiFi chip)
- USB cable for programming and serial communication
- Nintendo Switch console

## Installation

### 1. Flash the Firmware

1. Hold the BOOTSEL button on your Pico W while connecting it to your computer
2. The Pico W will appear as a USB mass storage device called "RPI-RP2"
3. Copy `autoshine_pico_firmware.uf2` to this drive
4. The Pico W will automatically restart with the new firmware

### 2. Connect to Switch

1. Put your Nintendo Switch in controller pairing mode:
   - Go to System Settings → Controllers and Sensors → Pro Controller Wired Communication → OFF
   - Go to Controllers → Change Grip/Order → Press and hold the sync button on a Joy-Con
2. Power on the Pico W (it will automatically start advertising as a Pro Controller)
3. The Switch should detect and pair with the Pico W controller

## Usage

### Serial Communication

The firmware communicates via USB serial at **115200 baud**. You can use any serial terminal or the Python adapter provided in the main Autoshine application.

### Available Commands

#### Button Commands
```
PRESS <button>      # Press and hold a button
RELEASE <button>    # Release a button
```

Supported buttons:
- Face buttons: `a`, `b`, `x`, `y`
- D-pad: `dpad_up`, `dpad_down`, `dpad_left`, `dpad_right`
- Shoulder buttons: `l`, `r`, `zl`, `zr`
- Stick clicks: `l_stick`, `r_stick`
- System buttons: `plus`, `minus`, `home`, `capture`

#### Analog Stick Commands
```
STICK <stick> <horizontal> <vertical>
```
- `<stick>`: `left` or `right`
- `<horizontal>`: -1.0 (full left) to 1.0 (full right)
- `<vertical>`: -1.0 (full down) to 1.0 (full up)

#### Utility Commands
```
CENTER_STICKS       # Center both analog sticks (0.0, 0.0)
RELEASE_ALL         # Release all pressed buttons
SLEEP <seconds>     # Sleep for specified duration (floating-point)
# comment           # Comment line (ignored)
```

### Example Session
```
PRESS a             # Press A button
SLEEP 0.1           # Wait 100ms
RELEASE a           # Release A button
STICK left 0.8 0.0  # Move left stick right
STICK left 0.0 0.0  # Center left stick
PRESS home          # Press Home button
RELEASE_ALL         # Release everything
```

## Python Integration

The main Autoshine application includes a `PicoAdapter` class that automatically handles:
- USB serial port detection and connection
- Command formatting and transmission  
- Error handling and reconnection
- Integration with existing macro system

Example usage:
```python
from adapter.pico import PicoAdapter

# Create adapter (auto-detects Pico W)
adapter = PicoAdapter()

# Connect to device
if adapter.connect():
    # Send commands
    adapter.press_button('a')
    adapter.sleep(0.1)
    adapter.release_button('a')
    adapter.set_stick('left', 0.8, 0.0)
    adapter.disconnect()
```

## Technical Details

### Architecture
- **Main Application**: Command parsing and execution loop
- **SwitchBluetooth**: Bluetooth HID device implementation
- **CommandParser**: Text command parsing and validation
- **BTStack Integration**: Bluetooth protocol stack
- **TinyUSB**: USB serial communication

### Bluetooth Protocol
- Implements Nintendo Switch Pro Controller HID profile
- Uses Bluetooth Classic (not BLE)
- Sends HID reports at regular intervals
- Handles controller state management

### Performance
- Command processing latency: < 1ms
- Bluetooth report rate: 60 Hz (16.67ms intervals)
- USB serial communication: 115200 baud
- Memory usage: ~2MB flash, ~256KB RAM

## Building from Source

### Prerequisites
- Raspberry Pi Pico SDK
- CMake 3.13+
- ARM GCC toolchain
- BTStack library (included in Pico SDK)

### Build Steps
```bash
cd firmware
mkdir build && cd build
cmake ..
make -j4
```

The build will generate:
- `autoshine_pico_firmware.elf`: Executable image
- `autoshine_pico_firmware.uf2`: Flashable firmware file

### Configuration Files
- `btstack_config.h`: BTStack Bluetooth configuration
- `tusb_config.h`: TinyUSB configuration
- `lwipopts.h`: lwIP networking configuration

## Troubleshooting

### Connection Issues
- Ensure Pico W is powered and running firmware
- Check USB serial connection (115200 baud, 8N1)
- Verify Switch is in pairing mode
- Try restarting both devices

### Command Issues
- Check command syntax and spelling
- Ensure proper line endings (\\n or \\r\\n)
- Verify button names match supported list
- Check floating-point format for stick values

### Bluetooth Issues
- Ensure Switch Pro Controller wired communication is OFF
- Clear paired controllers on Switch if needed
- Check for interference from other Bluetooth devices
- Verify Pico W Bluetooth antenna is not obstructed

## Advanced Usage

### Macro Integration
The firmware works seamlessly with Autoshine's macro system. Macros are parsed and executed command-by-command, providing precise timing control for complex input sequences.

### Custom Commands
The command parser can be extended to support additional functionality:
- Compound movements (e.g., diagonal stick + button combos)
- Timing-based sequences
- Conditional logic based on controller state

### Performance Tuning
- Adjust Bluetooth report interval in SwitchBluetooth.cpp
- Modify command processing frequency in main loop
- Optimize memory usage for resource-constrained applications

## License

This firmware is part of the PKMN-Autoshine project and follows the same licensing terms as the main application.