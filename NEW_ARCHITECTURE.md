# PKMN-Autoshine: New Pico-Based Architecture

This document describes the major architectural changes implemented to restructure PKMN-Autoshine for direct macro execution on PicoSwitchController devices.

## 🎯 Overview

The system has been redesigned with a new architecture where:
- **PicoSwitchController firmware** directly executes macro files with accurate timing
- **Web service** focuses on configuration, monitoring, and device management
- **Multiple Pico devices** can be managed simultaneously
- **Progress tracking** provides real-time iteration counts from each device

## 🔄 Architecture Changes

### Before (Legacy)
```
Web Service → Adapter → Commands → PicoSwitchController
     ↑
   Macro Execution
   Progress Tracking
```

### After (New)
```
Web Service → Configuration/Monitoring
     ↓
Multiple Pico Devices → Direct Macro Execution
     ↑
   Progress Reports
```

## 🚀 Getting Started

### 1. Build and Flash Updated Firmware

The PicoSwitchController firmware has been enhanced with new capabilities:

```bash
cd PicoSwitchController
mkdir -p build && cd build
cmake ..
make -j4
```

Flash the `autoshine_pico_firmware.uf2` file to your Pico devices.

### 2. Start the New Web Service

```bash
# Start the new Pico management server (default)
python web.py

# Or start on custom host/port
python web.py --host 192.168.1.100 --port 8080

# Use legacy mode if needed
python web.py --legacy macro_file.txt --adapter-port /dev/ttyACM0
```

### 3. Access the Web Interface

Open `http://localhost:8080` in your browser. You'll see the new interface with:
- **Pico Devices**: Discovery, connection management, and status
- **Macro Controls**: File selection and device targeting
- **Execution Status**: Real-time iteration tracking per device
- **Live Logs**: Device responses and system messages

## 📋 New Features

### Enhanced PicoSwitchController Firmware

#### New Commands
- `PRESS <button>` - Press and release a button (50ms hold)
- `LOAD_MACRO_START` - Begin receiving macro content
- `LOAD_MACRO_END` - Complete macro loading  
- `START_MACRO` - Start executing loaded macro
- `STOP_MACRO` - Stop macro execution

#### Macro Execution
- Direct macro file loading and parsing
- Accurate timing with non-blocking sleep
- Automatic iteration loops
- Progress reporting: `ITERATION_COMPLETE:N`

#### Example Serial Communication
```
LOAD_MACRO_START
PRESS a
SLEEP 0.5
PRESS b
LOAD_MACRO_END
START_MACRO
```

### Web Service Enhancements

#### Multi-Device Management
- Automatic Pico device discovery
- Individual device connection/disconnection
- Bulk operations (connect all, disconnect all)
- Real-time device status monitoring

#### Macro Management
- Device-specific macro loading
- Target device selection (individual or all)
- Centralized macro file management
- Real-time execution monitoring

#### Progress Monitoring
- Per-device iteration counts
- Live status updates via WebSocket
- Execution state tracking
- Device response logging

## 🎮 Using the New System

### 1. Connect Devices
1. Connect your Pico devices via USB
2. Click "Refresh Devices" or wait for auto-discovery
3. Click "Connect All" or connect individual devices

### 2. Load and Run Macros
1. Select a macro file from the dropdown
2. Choose target devices (default: all connected)
3. Click "Load to Picos" to upload the macro
4. Click "Start Execution" to begin
5. Monitor progress in the "Execution Status" section

### 3. Monitor Progress
- Real-time iteration counts for each device
- Live logs showing device responses
- WebSocket updates for immediate status changes

## 📁 File Structure Changes

### New Files
```
src/webapp/
├── pico_manager.py      # Multi-device management
├── pico_server.py       # New web server implementation
└── static/
    ├── pico-index.html  # New web interface
    └── pico-app.js      # Frontend JavaScript

PicoSwitchController/
├── include/CommandParser.h  # Enhanced with macro support
└── src/
    ├── CommandParser.cpp    # Macro parsing and execution
    └── main.cpp            # Updated command processing
```

### Updated Files
- `web.py` - Launch script with legacy mode support
- `src/adapter/pico.py` - Enhanced with macro loading methods

## 🔧 API Endpoints

### New Pico Management API
- `GET /api/pico/devices` - List available Pico devices
- `POST /api/pico/connect` - Connect to specific device
- `POST /api/pico/disconnect` - Disconnect from device
- `POST /api/pico/load_macro` - Load macro to devices
- `POST /api/pico/start_macro` - Start macro execution
- `POST /api/pico/stop_macro` - Stop macro execution
- `GET /api/pico/status` - Get device status

### Existing Macro API (unchanged)
- `GET /api/macros` - List macro files
- `GET /api/macros/{name}` - Get macro content
- `POST /api/macros` - Save macro file

## 🚀 Benefits of New Architecture

### Performance
- ⚡ **Faster execution**: Direct firmware control eliminates communication overhead
- 🎯 **Better accuracy**: Hardware-level timing for precise macro execution
- 📈 **Scalability**: Multiple devices can run independently

### Reliability  
- 🔒 **Independent operation**: Each Pico runs autonomously
- 🛡️ **Fault isolation**: One device failure doesn't affect others
- 🔄 **Automatic recovery**: Devices continue running after host disconnection

### Management
- 👁️ **Real-time monitoring**: Live progress tracking and status updates
- 🎛️ **Device selection**: Target specific devices or all simultaneously
- 📊 **Better logging**: Per-device logging and centralized monitoring

## 🔄 Migration Guide

### From Legacy System
1. **Update firmware**: Flash new firmware to Pico devices
2. **Update macros**: Ensure compatibility (PRESS command now supported)
3. **Use new web interface**: Default mode uses new architecture
4. **Legacy fallback**: Use `--legacy` flag for old behavior

### Macro Compatibility
The new system supports all existing macro commands plus:
- `PRESS` command (replaces HOLD+SLEEP+RELEASE patterns)
- Better SLEEP accuracy with non-blocking implementation
- Automatic iteration looping (no need for external loop control)

## 🐛 Troubleshooting

### Device Not Found
1. Ensure Pico is connected via USB
2. Check that new firmware is flashed
3. Verify USB drivers are installed
4. Try reconnecting the USB cable

### Macro Not Loading
1. Check macro file syntax
2. Verify device is connected
3. Check web service logs for errors
4. Try loading to individual devices first

### Execution Issues
1. Monitor device logs for errors
2. Check macro commands for typos
3. Verify button names are correct
4. Ensure adequate sleep delays

## 📚 Technical Details

### Firmware Changes
- Added macro command buffer (1000 commands max)
- Implemented non-blocking sleep state machine
- Added iteration completion reporting
- Enhanced command parser with PRESS support

### Communication Protocol
```
Host → Pico: LOAD_MACRO_START
Host → Pico: <macro lines>
Host → Pico: LOAD_MACRO_END
Host → Pico: START_MACRO
Pico → Host: ITERATION_COMPLETE:1
Pico → Host: ITERATION_COMPLETE:2
...
```

### WebSocket Messages
```json
{
  "type": "device_status",
  "devices": {
    "/dev/ttyACM0": {
      "connected": true,
      "running_macro": true,
      "iteration_count": 42
    }
  }
}
```

This new architecture provides a more robust, scalable, and accurate macro execution system while maintaining the flexibility to manage multiple devices simultaneously.