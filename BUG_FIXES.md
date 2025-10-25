# PKMN-Autoshine: Bug Fixes Summary

## Issues Fixed

### 1. ✅ **PRESS Command Reliability**

**Problem**: The PRESS command was using blocking `sleep_ms(50)` which interfered with the main event loop, causing unreliable button presses for a/b/x/y buttons.

**Solution**: Implemented non-blocking PRESS command execution:
- Added press button state tracking (`_press_button_active`, `_press_release_time`)
- PRESS command now holds the button and schedules release after 50ms
- Main loop continues processing while waiting for button release
- Added debug output for troubleshooting

**Files Modified**:
- `PicoSwitchController/include/CommandParser.h` - Added press state variables
- `PicoSwitchController/src/CommandParser.cpp` - Implemented non-blocking PRESS logic

### 2. ✅ **Web Interface Modal Fix**

**Problem**: The new Pico web interface was missing CSS styles for modal dialogs, preventing the macro editor from opening.

**Solution**: Added comprehensive modal styling to the Pico interface:
- Modal overlay with proper z-index and backdrop
- Responsive modal content with animations
- Form styling for macro editor
- CodeMirror and fallback editor support

**Files Modified**:
- `src/webapp/static/pico-index.html` - Added modal CSS styles

### 3. ✅ **Enhanced Debugging and Monitoring**

**Improvements**:
- Added debug output to PRESS command execution
- Enhanced firmware startup message with version info
- Added button name validation and error reporting
- Improved command execution logging

## Usage Instructions

### Building Updated Firmware

```bash
cd PicoSwitchController/build
cmake ..
make -j4
```

Flash the generated `autoshine_pico_firmware.uf2` to your Pico devices.

### Using the Web Interface

1. **Start the server**:
   ```bash
   python3 web.py --port 8081
   ```

2. **Open the web interface**:
   Navigate to `http://localhost:8081`

3. **Device Management**:
   - Click "Refresh Devices" to scan for Pico controllers
   - Use "Connect All" to connect to all detected devices
   - Individual devices can be connected/disconnected as needed

4. **Running Macros**:
   - Select a macro from the dropdown
   - Choose target devices (default: all connected)
   - Click "Load to Picos" to upload the macro
   - Click "Start Execution" to begin running
   - Monitor progress in the "Execution Status" section

5. **Editing Macros**:
   - Click "Edit" to open the macro editor modal
   - The modal now works properly with syntax highlighting
   - Save changes and reload to devices

### Supported Button Names

The following button names are supported in macros:
- **Face buttons**: `a`, `b`, `x`, `y`
- **Shoulder buttons**: `l`, `r`, `zl`, `zr`
- **System buttons**: `plus`, `minus`, `home`, `capture`
- **D-pad**: `dpad_up`, `dpad_down`, `dpad_left`, `dpad_right`
- **Stick buttons**: `l_stick`, `r_stick`

### Example Test Macro

Create a test macro to verify button functionality:

```
# Test all buttons
PRESS a
SLEEP 1.0
PRESS b
SLEEP 1.0
PRESS x
SLEEP 1.0
PRESS y
SLEEP 1.0
PRESS zl
SLEEP 1.0
PRESS zr
SLEEP 1.0
```

## Troubleshooting

### PRESS Commands Not Working
1. **Check firmware version**: Ensure you're running the updated firmware with "v2.0" in the startup message
2. **Verify button names**: Use the exact button names listed above (lowercase)
3. **Check serial output**: Look for debug messages like "PRESS command: pressing button 'a'"
4. **Test with working buttons**: If ZL works but A doesn't, there may be a connection issue

### Web Interface Issues
1. **Modal not opening**: Hard refresh the browser (Ctrl+F5) to reload CSS
2. **Device not detected**: Check USB connections and firmware flash
3. **Connection failed**: Try reconnecting individual devices

### Serial Communication
Monitor the Pico's serial output for debugging:
```bash
# Linux
sudo minicom -D /dev/ttyACM0 -b 115200

# Or use screen
screen /dev/ttyACM0 115200
```

Look for:
- Startup message: "=== PKMN-Autoshine Pico Firmware v2.0 ==="
- Command execution: "Executing: PRESS a"
- Button press debug: "PRESS command: pressing button 'a'"
- Button release: "Releasing button 'a' after 50ms"

## Performance Improvements

The non-blocking PRESS implementation provides:
- **Better reliability**: No blocking operations in main loop
- **Accurate timing**: Hardware-level 50ms press duration
- **Responsive execution**: Commands process immediately
- **Debug visibility**: Clear logging of button operations

## Next Steps

With these fixes, the system should now provide:
1. **Reliable button presses** for all supported buttons
2. **Working web interface** with modal editor functionality  
3. **Better debugging** through enhanced logging
4. **Improved user experience** with responsive UI and accurate macro execution

Test the system with the new `button_test.txt` macro to verify all buttons work correctly!