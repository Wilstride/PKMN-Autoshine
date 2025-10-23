# Multi-Controller Support Documentation

## Overview

PKMN-Autoshine now supports controlling multiple PicoSwitchController devices simultaneously, allowing you to automate multiple Nintendo Switch consoles at once. This is particularly useful for:

- **Shiny hunting**: Run multiple games to increase your chances
- **Multi-game farming**: Farm resources across multiple save files
- **Coordinated gameplay**: Control multiple characters in multiplayer scenarios
- **Parallel testing**: Test macros on multiple setups simultaneously

## Hardware Requirements

### Basic Setup
- Multiple Raspberry Pi Pico W devices (2 or more recommended)
- Each Pico W flashed with the PicoSwitchController firmware
- Multiple USB cables for serial connections
- Multiple Nintendo Switch consoles (one per Pico W)

### Connection Layout
```
Host Computer
├── /dev/ttyACM0 ← Pico W #1 ← Switch Console #1
├── /dev/ttyACM1 ← Pico W #2 ← Switch Console #2
├── /dev/ttyACM2 ← Pico W #3 ← Switch Console #3
└── ...
```

## Software Configuration

### 1. Adapter Selection

Choose your adapter mode in the web interface:

- **Auto-detect**: Automatically uses multi-controller if multiple devices found
- **Multi-Pico**: Explicitly use multi-controller mode
- **Pico W (Single)**: Use only one controller (legacy mode)
- **Joycontrol**: Bluetooth adapter (single controller)

### 2. Device Detection

The system automatically detects all connected Pico W devices and assigns IDs:
- `pico_0`: First detected device (/dev/ttyACM0)
- `pico_1`: Second detected device (/dev/ttyACM1)
- `pico_2`: Third detected device (/dev/ttyACM2)
- etc.

## Macro Syntax for Multi-Controller

### Device Targeting Syntax

```
device_id:COMMAND arguments
```

### Examples

#### Basic Commands
```bash
# Press A on all controllers
PRESS A

# Press B on controller 0 only
pico_0:PRESS B

# Press X on controller 1 only
pico_1:PRESS X
```

#### Stick Controls
```bash
# Move all controllers' left stick right
STICK L 1.0 0.0

# Move controller 0's left stick up
pico_0:STICK L 0.0 1.0

# Move controller 1's right stick diagonally
pico_1:STICK R 0.7 0.7
```

#### Sleep Commands
```bash
# Global sleep (affects all controllers)
SLEEP 2

# Device-specific sleep (only that controller waits)
pico_0:SLEEP 1
```

#### Broadcasting
```bash
# Explicit broadcast to all devices
all:PRESS HOME
*:PRESS HOME

# Both are equivalent to:
PRESS HOME
```

### Complex Coordination Examples

#### Synchronized Actions
```bash
# All controllers press A simultaneously
*:PRESS A
SLEEP 1

# Sequential button presses
pico_0:PRESS A
SLEEP 0.1
pico_1:PRESS A
SLEEP 0.1
pico_2:PRESS A
```

#### Different Actions per Controller
```bash
# Controller 0: Navigate menus
pico_0:PRESS X
pico_0:SLEEP 1
pico_0:PRESS A

# Controller 1: Battle actions
pico_1:PRESS A
pico_1:SLEEP 2
pico_1:PRESS B

# Controller 2: Movement
pico_2:STICK L 1.0 0.0
pico_2:SLEEP 3
pico_2:STICK L 0.0 0.0
```

## API Usage

### Python Code Examples

#### Creating Multi-Controller Adapter
```python
from adapter.pico import MultiPicoAdapter

# Auto-detect all devices
adapter = MultiPicoAdapter()
await adapter.connect()

# Get connected device IDs
device_ids = adapter.get_device_ids()
print(f"Connected controllers: {device_ids}")
```

#### Targeting Specific Controllers
```python
# Press A on specific controller
await adapter.press(Button.A, device_id="pico_0")

# Press A on all controllers
await adapter.press(Button.A)  # device_id=None (default)
```

#### Using Individual Adapters
```python
# Get adapter for specific device
pico_0_adapter = adapter.get_adapter("pico_0")
await pico_0_adapter.press(Button.B)
```

### Macro Runner Integration
```python
from macros.parser import parse_macro
from macros.runner import run_macro

# Parse macro with device targeting
commands = parse_macro(macro_text)
await run_macro(adapter, commands)
```

## Web Interface

### Controller Management
- View connected controllers in the web interface
- See connection status for each device
- Refresh controller list dynamically
- Monitor individual controller health

### Macro Editor
- Syntax highlighting for device targeting
- Auto-completion for device IDs
- Validation of multi-controller commands
- Preview of command distribution

## Best Practices

### 1. Hardware Setup
- Use quality USB cables to prevent disconnections
- Connect devices to different USB controllers if possible
- Ensure adequate power supply for multiple Pico W devices
- Label your cables and devices for easy identification

### 2. Macro Design
- Start with broadcast commands for basic testing
- Use device-specific commands for specialized tasks
- Add appropriate delays between controller actions
- Test with fewer controllers first, then scale up

### 3. Error Handling
- Always include fallback commands in macros
- Use global sleep commands for synchronization points
- Monitor device connectivity regularly
- Plan for partial device failures

### 4. Performance
- Avoid too many simultaneous rapid commands
- Use reasonable delays between actions
- Monitor system resources with many controllers
- Consider batching operations when possible

## Troubleshooting

### Common Issues

#### Device Detection Problems
```bash
# Check connected devices
ls /dev/ttyACM*

# Check device permissions
sudo chmod 666 /dev/ttyACM*
```

#### Connection Failures
- Verify Pico W firmware is properly flashed
- Check USB cable connections
- Restart devices if necessary
- Verify device IDs in logs

#### Macro Execution Issues
- Validate macro syntax with test script
- Check device targeting syntax
- Verify all referenced devices are connected
- Monitor logs for error messages

### Testing Multi-Controller Setup
```bash
# Run the test suite
python test_multi_controller.py

# Test specific functionality
python -c "
import asyncio
from adapter.pico import MultiPicoAdapter
async def test():
    adapter = MultiPicoAdapter()
    await adapter.connect()
    print(f'Connected: {adapter.get_device_ids()}')
    adapter.close()
asyncio.run(test())
"
```

## Advanced Features

### Custom Device Naming
The system uses auto-generated IDs (`pico_0`, `pico_1`, etc.) but you can:
- Map device IDs to meaningful names in your macros
- Use comments to document which device controls which console
- Create device-specific macro files

### Integration with Existing Macros
Existing single-controller macros work unchanged:
- Commands without device prefixes broadcast to all controllers
- Gradual migration from single to multi-controller setups
- Backward compatibility maintained

### Future Enhancements
- Device-specific configuration profiles
- Load balancing across controllers
- Health monitoring and automatic failover
- Advanced coordination patterns

## Example Use Cases

### Shiny Hunting Setup
```bash
# Start all games
*:PRESS A
SLEEP 3

# Each controller hunts in different areas
pico_0:PRESS X  # Route hunting
pico_1:PRESS Y  # Wild area
pico_2:PRESS PLUS  # Static encounters

# Coordinated encounter checking
SLEEP 5
*:PRESS A  # Check for shiny
SLEEP 2
*:PRESS B  # Run if not shiny
```

### Multi-Game Resource Farming
```bash
# Access storage on all games
*:PRESS X
SLEEP 2
*:PRESS A

# Each game farms different resources
pico_0:PRESS A  # Farm berries
pico_1:PRESS B  # Farm ore  
pico_2:PRESS X  # Farm pokemon

# Collect and repeat
SLEEP 30
*:PRESS HOME
```

## Support and Community

For additional help:
- Check the GitHub repository for updates
- Join the community discussions
- Report issues with hardware compatibility
- Share your multi-controller macro creations

---

*Last updated: October 2024*
*PKMN-Autoshine Multi-Controller Documentation v1.0*