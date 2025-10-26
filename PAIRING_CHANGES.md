# Manual Pairing Mode Implementation

## Overview
Modified the PKMN-Autoshine firmware to require manual pairing instead of automatically pairing with any available Switch console on boot.

## Changes Made

### 1. Firmware Changes (PicoSwitchController)

#### `SwitchBluetooth.h`
- Added `enable_pairing_mode()` method to make device discoverable
- Added `disable_pairing_mode()` method to hide device from Switch
- Added `is_pairing_mode()` getter to check pairing status
- Added `_pairing_mode` boolean state variable

#### `SwitchBluetooth.cpp`
- **Modified `init()`**: Changed `gap_discoverable_control(1)` to `gap_discoverable_control(0)` - device now starts in **non-discoverable mode**
- **Added `enable_pairing_mode()`**: Sets device to discoverable when called
- **Added `disable_pairing_mode()`**: Hides device from Switch scanning

#### `CommandParser.cpp`
- Added `PAIR` command handler - calls `enable_pairing_mode()`
- Added `UNPAIR` command handler - calls `disable_pairing_mode()`

#### `main.cpp`
- Updated help text to include new commands:
  - `PAIR` - Enable pairing mode (make discoverable)
  - `UNPAIR` - Disable pairing mode (hide from Switch)
- Added notice: "Device starts in NON-DISCOVERABLE mode. Use PAIR command to enable pairing."

### 2. Backend Changes (Web Server)

#### `handlers.py`
- Added `enable_pairing()` handler function
  - Accepts POST requests with `port` parameter
  - Sends `PAIR` command to specified Pico device
  - Returns success/error status

#### `server.py`
- Registered new route: `POST /api/pico/pair` → `handlers.enable_pairing`

### 3. Frontend Changes (Web UI)

#### `app.js`
- **Modified `renderDevices()`**: Added "🔗 Pair" button to each device card
  - Button is disabled if device is not connected
  - Shows helpful title tooltip
- **Added `enablePairing(port)` method**:
  - Sends POST request to `/api/pico/pair` with device port
  - Logs success message with pairing instructions
  - Handles errors gracefully

## Usage Instructions

### For Users

1. **Connect Pico Device**: Connect your Pico via USB to the host computer
2. **Open Dashboard**: Navigate to the web interface at `http://localhost:8080`
3. **Enable Pairing**: Click the "🔗 Pair" button next to the device you want to pair
4. **Pair on Switch**: 
   - Go to Switch **System Settings** > **Controllers and Sensors**
   - Select **Change Grip/Order**
   - The device will appear as "Pro Controller"
   - Press L+R on the virtual controller (or wait) to pair

### For Developers

**Serial Commands:**
```bash
# Enable pairing mode
PAIR

# Disable pairing mode  
UNPAIR
```

**Web API:**
```bash
# Enable pairing on specific device
curl -X POST http://localhost:8080/api/pico/pair \
  -H "Content-Type: application/json" \
  -d '{"port": "/dev/ttyACM0"}'
```

## Benefits

1. **Security**: Devices don't automatically pair with any Switch in range
2. **Control**: User explicitly chooses when and which device pairs
3. **Multi-Device**: In multi-Pico setups, pair specific devices to specific Switches
4. **Testing**: Easier to test without accidental connections

## Technical Notes

- Device Bluetooth MAC address is still randomized on boot (format: `7C:BB:8A:XX:XX:XX`)
- Pairing state is not persistent - device returns to non-discoverable mode after reboot
- Once paired, the Switch remembers the device - no need to re-pair unless "Forget Controller" is used
- Pairing mode can be disabled with `UNPAIR` command to hide from Switch scanning

## Compatibility

- Fully backward compatible with existing macros
- No changes required to existing macro files
- Web dashboard automatically shows pairing button for all devices
