# Web App Adapter Factory Integration

This document describes the updates made to the web application to use the adapter factory with prioritized Pico adapter usage.

## Changes Made

### 1. Worker Module (`webapp/worker.py`)
- **Removed**: Direct import and usage of `JoycontrolAdapter`
- **Added**: Import of `adapter.factory.create_adapter`
- **Updated**: `worker_main()` function signature to accept `preferred_adapter` parameter
- **Changed**: Adapter creation to use `await create_adapter(preferred_adapter)` instead of hardcoded adapter

### 2. Server Module (`webapp/server.py`)
- **Added**: Adapter configuration management using `adapter_config` dictionary
- **Updated**: Worker thread creation to pass adapter preference
- **Added**: New API routes for adapter management:
  - `GET /api/adapters` - List available adapters
  - `GET /api/adapters/status` - Get adapter status and connectivity
  - `POST /api/adapters/select` - Set preferred adapter

### 3. Handlers Module (`webapp/handlers.py`)
- **Added**: `api_list_adapters()` - Returns available adapter types
- **Added**: `api_adapter_status()` - Returns current preference and connectivity status
- **Added**: `api_select_adapter()` - Allows setting adapter preference

### 4. Web UI (`webapp/static/index.html`)
- **Added**: Adapter status display section
- **Added**: Adapter selection dropdown and controls
- **Added**: JavaScript functions for adapter management:
  - `updateAdapterStatus()` - Polls adapter status every 5 seconds
  - Event handlers for adapter selection and testing

### 5. Dependencies (`requirements.txt`)
- **Added**: `aiohttp>=3.8.0` for web server functionality

## Features

### Automatic Adapter Detection
The system now uses the adapter factory which:
1. **Prioritizes Pico**: Tries Pico W adapter first (USB serial)
2. **Falls back**: Uses joycontrol (Bluetooth) if Pico unavailable
3. **Reports errors**: Provides clear error messages if no adapters work

### Web UI Controls
- **Adapter Status**: Shows current adapter preference and connectivity
- **Adapter Selection**: Dropdown to choose preferred adapter:
  - "Auto-detect (Pico first)" - Default behavior
  - "Pico W (USB Serial)" - Force Pico adapter
  - "Joycontrol (Bluetooth)" - Force joycontrol adapter
- **Test Connectivity**: Button to test which adapters are available
- **Real-time Updates**: Status updates every 5 seconds

### API Endpoints

#### `GET /api/adapters`
Returns list of available adapter types.

**Response**: `["pico", "joycontrol"]`

#### `GET /api/adapters/status`
Returns current adapter preference and connectivity status.

**Response**:
```json
{
  "preferred": null,
  "connectivity": {
    "pico": false,
    "joycontrol": true
  }
}
```

#### `POST /api/adapters/select`
Sets the preferred adapter type.

**Request**: `{"adapter": "pico"}`  
**Response**: `{"preferred": "pico", "message": "Adapter preference updated..."}`

## Usage

### Starting the Web App
```bash
python web.py [macro_file] [--host HOST] [--port PORT]
```

The system will automatically:
1. Try to connect to Pico W adapter first
2. Fall back to joycontrol if Pico unavailable
3. Display connection status in web logs

### Changing Adapter Preference
1. Open the web interface
2. Use the "Adapter Settings" section
3. Select preferred adapter from dropdown
4. Click "Set Adapter"
5. Restart the system for changes to take effect

### Monitoring Adapter Status
- Check the blue "Adapter Status" section for current preference
- Green checkmarks (✓) indicate available adapters
- Red X marks (✗) indicate unavailable adapters
- Click "Test Connectivity" to refresh status

## Technical Notes

- Adapter changes require system restart to take effect
- The factory handles all connection logic and error handling
- Pico adapter requires USB serial connection and proper firmware
- Joycontrol adapter requires Bluetooth configuration
- The web interface updates adapter status every 5 seconds
- All adapter operations are asynchronous and non-blocking