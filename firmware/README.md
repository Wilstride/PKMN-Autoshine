# Autoshine Pico Firmware

Custom firmware that turns a Raspberry Pi Pico W into a Nintendo Switch Pro Controller bridge, receiving commands via USB serial and executing them over Bluetooth HID.

This firmware enables the Pico W to act as an authentic Nintendo Switch Pro Controller while being controlled remotely via USB serial commands from a host computer.

## Features

- Connects to Nintendo Switch via Bluetooth as a Pro Controller
- Receives commands over USB serial from the host computer
- Supports all Switch Pro Controller buttons and analog sticks
- Compatible with existing Autoshine macro format

## Building

1. Set up the Pico SDK environment:
   ```bash
   export PICO_SDK_PATH=/path/to/pico-sdk
   ```

2. Create build directory and compile:
   ```bash
   cd firmware
   mkdir build
   cd build
   cmake ..
   make
   ```

3. The firmware will be built as `autoshine_pico_firmware.uf2`

## Installing

1. Hold down the BOOTSEL button on your Pico W while connecting it to USB
2. Copy the `autoshine_pico_firmware.uf2` file to the RPI-RP2 drive that appears
3. The Pico will automatically reboot with the new firmware

## Usage

Once flashed, the Pico W will:

1. Start a Bluetooth HID device that appears as "Pro Controller"
2. Accept commands via USB serial at 115200 baud
3. Execute commands as Switch controller inputs

### Command Format

The firmware accepts the same command format as the main Autoshine application:

- `PRESS <button>` - Press a button
- `RELEASE <button>` - Release a button  
- `STICK <stick> <h> <v>` - Set analog stick position
- `SLEEP <seconds>` - Sleep for specified duration
- `CENTER_STICKS` - Center both analog sticks
- `RELEASE_ALL` - Release all buttons
- `# comment` - Comment lines are ignored

### Supported Buttons

- `a`, `b`, `x`, `y`
- `l`, `r`, `zl`, `zr`
- `plus`, `minus`, `home`, `capture`
- `l_stick`, `r_stick` (stick click buttons)
- `dpad_up`, `dpad_down`, `dpad_left`, `dpad_right`

### Analog Sticks

- `l_stick` - Left analog stick
- `r_stick` - Right analog stick

Stick coordinates range from -1.0 to 1.0 for both horizontal (h) and vertical (v) axes.

## Pairing with Switch

1. Flash and power on the Pico W
2. On your Switch, go to System Settings > Controllers and Sensors > Change Grip/Order
3. The Pico should appear as "Pro Controller" and pair automatically

## Troubleshooting

- If pairing fails, power cycle the Pico W and try again
- Ensure the Switch is in pairing mode before powering on the Pico
- Check serial output for error messages when sending commands
- Verify `/dev/ttyACM0` (or similar) appears after flashing firmware
- Use `sudo dmesg` to check for USB enumeration issues

## Technical Details

### Architecture
- **BTStack**: Bluetooth protocol stack for embedded systems
- **TinyUSB**: USB device stack for CDC serial communication  
- **Pico SDK**: Raspberry Pi Pico development framework
- **CYW43**: Wireless chip driver for Bluetooth and WiFi functionality

### Memory Layout
- **Flash**: ~850KB firmware image
- **RAM**: Dynamic allocation for BTStack buffers and command processing
- **USB**: CDC device class for serial communication
- **Bluetooth**: HID device class for controller emulation

## Acknowledgments

This firmware builds upon foundational work from the Nintendo Switch controller emulation community:

### [Poohl/joycontrol](https://github.com/Poohl/joycontrol)
The Bluetooth HID implementation and Nintendo Switch Pro Controller protocol handling in this firmware is derived from joycontrol's pioneering research. Their comprehensive reverse engineering of the Switch's Bluetooth communication protocol provided the essential foundation for accurate controller emulation.

**Key contributions used:**
- Nintendo Switch Pro Controller HID report structure
- Bluetooth pairing and authentication sequences  
- Button and analog stick data formatting
- Controller capability advertisements

### [DavidPagels/retro-pico-switch](https://github.com/DavidPagels/retro-pico-switch)
The embedded implementation approach, BTStack integration, and Pico W-specific Bluetooth handling is based on retro-pico-switch's architecture. Their work demonstrated how to successfully implement Switch controller emulation on Raspberry Pi Pico hardware.

**Key contributions used:**
- BTStack configuration for Pico W
- Bluetooth HID device initialization sequences
- CYW43 wireless chip integration  
- Pico SDK build system and CMake structure
- USB and Bluetooth coexistence patterns

### Additional Credits
- **BTStack Team**: For the comprehensive Bluetooth protocol stack
- **Raspberry Pi Foundation**: For the Pico SDK and excellent documentation
- **Nintendo Switch Community**: For reverse engineering and protocol documentation

This project stands on the shoulders of these giants in the Switch homebrew and controller emulation community. Without their groundbreaking work, this implementation would not have been possible.

## License

This firmware is released under the **GNU General Public License v3.0 (GPL-3.0)** due to its use of concepts and implementations derived from GPL-3.0 licensed projects.