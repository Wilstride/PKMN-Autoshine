# PKMN-Autoshine: Bluetooth Frame-Based Timing Implementation

## ✅ **Changes Implemented**

### **1. Firmware Changes (PicoSwitchController)**

#### **Frame-Based Timing**
- **SLEEP command** now accepts bluetooth frames instead of milliseconds
- **125Hz bluetooth frame rate** = 8ms per frame
- **Formula**: `sleep_duration_ms = frames * 8.0`

#### **PRESS Command Removed**
- Removed `parse_press_command()` method from firmware
- Removed press button state variables (`_press_button_active`, etc.)
- PRESS commands are now handled entirely by the server preprocessing

#### **Updated Help Text**
```
=== PKMN-Autoshine Pico Firmware v2.1 ===
Bluetooth frame rate: 125Hz (8ms per frame)
Available commands:
  HOLD <button>       - Hold a button down (without releasing)
  RELEASE <button>    - Release a button
  SLEEP <frames>      - Sleep for specified bluetooth frames
Note: PRESS commands are preprocessed by server into HOLD+SLEEP+RELEASE
```

### **2. Server-Side Preprocessing (PicoAdapter)**

#### **Automatic PRESS Flattening**
```python
# PRESS button → 
HOLD button
SLEEP 1        # 1 bluetooth frame
RELEASE button
```

#### **Seconds to Frames Conversion**
```python  
# SLEEP seconds → SLEEP frames
frames = seconds * 125.0  # 125Hz frame rate
```

#### **Example Preprocessing**
**Input**:
```
PRESS a
SLEEP 0.5
PRESS b  
SLEEP 1.0
```

**Output**:
```
HOLD a
SLEEP 1      # 1 frame hold
RELEASE a
SLEEP 62.5   # 0.5s × 125Hz = 62.5 frames
HOLD b
SLEEP 1      # 1 frame hold  
RELEASE b
SLEEP 125.0  # 1.0s × 125Hz = 125 frames
```

## 🎯 **Key Benefits**

### **Accurate Nintendo Switch Timing**
- **125Hz bluetooth frame rate** matches real Pro Controller
- **1 frame button press** (8ms) is realistic button timing
- **Frame-based sleep** provides precise timing control

### **Server-Side Intelligence**
- **PRESS flattening** removes complexity from firmware
- **Automatic conversion** of user-friendly seconds to precise frames
- **Backward compatibility** with existing macro files using PRESS and seconds

### **Simplified Firmware**
- **Removed PRESS complexity** from firmware code
- **Frame-based timing** is simpler and more accurate
- **Cleaner command set** focused on basic operations

## 📊 **Timing Examples**

| User Input | Frames | Milliseconds | Description |
|------------|--------|--------------|-------------|
| `PRESS a` | 1 frame hold | 8ms | Single button press |
| `SLEEP 0.1` | 12.5 frames | 100ms | Short delay |  
| `SLEEP 0.5` | 62.5 frames | 500ms | Half second |
| `SLEEP 1.0` | 125 frames | 1000ms | One second |
| `SLEEP 2.0` | 250 frames | 2000ms | Two seconds |

## 🛠 **Usage**

### **Macro Files (User Perspective)**
Users can continue writing macros with familiar syntax:
```
# User writes this:
PRESS a
SLEEP 0.5
PRESS b
SLEEP 1.0
```

### **Firmware Execution (Behind the Scenes)**  
Server automatically converts to precise frame timing:
```
# Firmware receives this:
HOLD a
SLEEP 1
RELEASE a  
SLEEP 62.5
HOLD b
SLEEP 1
RELEASE b
SLEEP 125.0
```

## 🚀 **Testing**

### **Build Firmware**
```bash
cd PicoSwitchController/build
make -j4
# Flash autoshine_pico_firmware.uf2 to Pico
```

### **Test Preprocessing**
```bash
# Start web server
python3 web.py --port 8082

# Use frame_timing_test.txt macro to verify:
# - PRESS commands flatten correctly
# - Timing converts from seconds to frames
# - All buttons work reliably
```

### **Expected Behavior**
- **All buttons** (a, b, x, y, zl, zr, etc.) should work reliably
- **Timing accuracy** improved with frame-based precision
- **No more timing issues** from blocking operations
- **Consistent behavior** across all button types

This implementation now matches the Nintendo Switch Pro Controller's actual 125Hz bluetooth timing and provides the precise 1-frame button press duration you requested!