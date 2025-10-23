# PKMN-Autoshine Adapter Integration Guide

## Overview
The PKMN-Autoshine system now supports automatic adapter detection and selection, with Pico W firmware as the primary adapter and joycontrol as a fallback option.

## Supported Adapters

### 1. Pico W (Primary - Recommended)
- **Hardware**: Raspberry Pi Pico W with retro-pico-switch firmware
- **Detection**: Automatic USB VID/PID detection (Raspberry Pi Foundation devices)
- **Connection**: USB serial communication
- **Benefits**: Better reliability, lower latency, dedicated hardware

### 2. Joycontrol (Fallback)
- **Hardware**: Linux system with Bluetooth capability
- **Detection**: Checks for hciconfig and sudo access
- **Connection**: Bluetooth HID emulation
- **Benefits**: Software-only solution, works on most Linux systems

## Automatic Adapter Selection

The system uses the following priority order:
1. **Pico W**: If a compatible device is detected and responsive
2. **Joycontrol**: If Bluetooth and sudo access are available
3. **Error**: If no adapters are available

## Usage

### Command Line Interface (CLI)

```bash
# Use automatic adapter selection (recommended)
python cli.py macro_file.txt

# Force specific adapter
python cli.py --adapter pico macro_file.txt
python cli.py --adapter joycontrol macro_file.txt

# Check adapter status
python check_status.py
```

### Web Interface

```bash
# Start web server with automatic adapter selection
python web.py

# Start with specific adapter preference
python web.py --adapter pico
python web.py --adapter joycontrol

# Access web interface at http://localhost:8080
```

The web interface now displays:
- Current active adapter
- Pico W availability status
- Joycontrol availability status
- Recommended adapter based on connectivity

## Status Checking

Use the diagnostic tool to check your system:

```bash
python check_status.py
```

This will show:
- Available adapters
- Hardware detection results
- Bluetooth capability
- Connectivity test results
- Recommendations for setup

## Troubleshooting

### Pico W Issues
- Ensure Pico W is flashed with retro-pico-switch firmware
- Check USB connection and permissions
- Verify device appears in system USB devices
- Try different USB ports/cables

### Joycontrol Issues
- Install BlueZ: `sudo apt install bluez`
- Check Bluetooth adapter: `hciconfig`
- Ensure sudo access for the user
- Pair and trust the Switch before use

### General Issues
- Run `python check_status.py` for detailed diagnostics
- Check Python dependencies: `pip install aiohttp pyserial`
- Verify all adapter modules are importable

## Architecture

### Key Components
- `adapter/factory.py`: Central adapter selection and creation
- `adapter/pico.py`: Pico W adapter implementation  
- `adapter/joycontrol.py`: Joycontrol adapter wrapper
- `check_status.py`: System diagnostics tool
- `cli/main.py`: Updated CLI with adapter selection
- `webapp/`: Web interface with adapter status display

### Flow
1. System detects available adapters
2. Tests connectivity for each adapter
3. Selects best available adapter automatically
4. Falls back gracefully if primary adapter fails
5. Provides user feedback and status information

## Configuration

### Web Server Settings
- Default host: `0.0.0.0` (all interfaces)
- Default port: `8080`
- Adapter preference: `auto` (can be `pico`, `joycontrol`, or `auto`)

### CLI Settings
- Adapter preference: `auto` (can be overridden with --adapter)
- Macro file: Required argument
- Verbose output available with status checking

## API Endpoints

The web interface exposes these endpoints:
- `GET /api/adapter/status`: Current adapter availability and connectivity
- `GET /api/adapter/current`: Currently active adapter information
- WebSocket `/ws`: Real-time communication and logging

## Best Practices

1. **Hardware Setup**: Use Pico W for best performance and reliability
2. **Fallback**: Keep joycontrol available as backup option
3. **Monitoring**: Use web interface to monitor adapter status
4. **Diagnostics**: Run status checker when experiencing issues
5. **Updates**: Keep firmware and dependencies updated

## Migration from Previous Versions

If you were using the old hardcoded joycontrol system:
1. Your existing setup will continue to work as fallback
2. Add Pico W hardware for improved performance
3. Use `python check_status.py` to verify new functionality
4. Update any custom scripts to use the new CLI interface

The system is fully backward compatible while providing enhanced functionality.