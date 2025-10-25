/**
 * PKMN Autoshine - Pico Controller Management JavaScript
 * 
 * This module provides the frontend functionality for managing multiple
 * Pico devices and coordinating macro execution across them.
 * 
 * Key Features:
 * - Multiple Pico device discovery and management
 * - Device-specific macro loading and execution
 * - Real-time status monitoring and iteration tracking
 * - WebSocket communication for live updates
 */

// ============================================================================
// Global Variables and State Management
// ============================================================================

let editor;
let ws;
let wsReconnectInterval;
let currentMacroName = '';
let devices = {};
let selectedDevices = [];

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    initializeEditor();
    initializeEventListeners();
    initializeWebSocket();
    loadMacrosList();
    refreshDevices();
});

// ============================================================================
// WebSocket Communication
// ============================================================================

function initializeWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = function() {
        addLogMessage('Connected to server', 'success');
        if (wsReconnectInterval) {
            clearInterval(wsReconnectInterval);
            wsReconnectInterval = null;
        }
    };
    
    ws.onmessage = function(event) {
        try {
            const data = JSON.parse(event.data);
            handleWebSocketMessage(data);
        } catch (e) {
            console.error('Error parsing WebSocket message:', e);
        }
    };
    
    ws.onclose = function() {
        addLogMessage('Disconnected from server', 'error');
        if (!wsReconnectInterval) {
            wsReconnectInterval = setInterval(initializeWebSocket, 3000);
        }
    };
    
    ws.onerror = function(error) {
        console.error('WebSocket error:', error);
    };
}

function handleWebSocketMessage(data) {
    switch (data.type) {
        case 'log':
            addLogMessage(data.message, 'info');
            break;
        case 'device_status':
            updateDevicesDisplay(data.devices);
            break;
        default:
            console.log('Unknown message type:', data.type);
    }
}

// ============================================================================
// Device Management
// ============================================================================

async function refreshDevices() {
    try {
        const response = await fetch('/api/pico/devices');
        const data = await response.json();
        
        devices = {};
        data.devices.forEach(device => {
            devices[device.port] = device;
        });
        
        updateDevicesDisplay();
        updateTargetDevicesSelect();
        updateStatusGrid();
        
    } catch (error) {
        addLogMessage(`Error refreshing devices: ${error.message}`, 'error');
    }
}

function updateDevicesDisplay() {
    const devicesList = document.getElementById('devices_list');
    
    if (Object.keys(devices).length === 0) {
        devicesList.innerHTML = '<p>No Pico devices found. Make sure devices are connected and have the firmware flashed.</p>';
        return;
    }
    
    let html = '';
    for (const [port, device] of Object.entries(devices)) {
        const statusClass = device.running_macro ? 'running' : (device.connected ? 'connected' : '');
        const statusText = device.running_macro ? 
            `Running macro (${device.iteration_count} iterations)` : 
            (device.connected ? 'Connected' : 'Disconnected');
        
        html += `
            <div class="device-item ${statusClass}" data-port="${port}">
                <div class="device-info">
                    <div class="device-port">${port}</div>
                    <div class="device-status">${statusText}</div>
                </div>
                <div class="device-actions">
                    ${!device.connected ? 
                        `<button onclick="connectDevice('${port}')" class="primary">Connect</button>` :
                        `<button onclick="disconnectDevice('${port}')" class="secondary">Disconnect</button>`
                    }
                </div>
            </div>
        `;
    }
    
    devicesList.innerHTML = html;
}

function updateTargetDevicesSelect() {
    const select = document.getElementById('target_devices');
    
    // Clear existing options except "All"
    const allOption = select.querySelector('option[value="all"]');
    select.innerHTML = '';
    select.appendChild(allOption);
    
    // Add connected devices
    for (const [port, device] of Object.entries(devices)) {
        if (device.connected) {
            const option = document.createElement('option');
            option.value = port;
            option.textContent = port;
            select.appendChild(option);
        }
    }
    
    // Select "All" by default if no specific selection
    if (select.selectedOptions.length === 0) {
        allOption.selected = true;
    }
}

function updateStatusGrid() {
    const statusGrid = document.getElementById('status_grid');
    
    const runningDevices = Object.entries(devices).filter(([port, device]) => device.running_macro);
    
    if (runningDevices.length === 0) {
        statusGrid.innerHTML = '<p>No devices running macros</p>';
        return;
    }
    
    let html = '';
    for (const [port, device] of runningDevices) {
        html += `
            <div class="status-card">
                <h4>${port}</h4>
                <div class="iteration-count">${device.iteration_count}</div>
                <div>iterations completed</div>
            </div>
        `;
    }
    
    statusGrid.innerHTML = html;
}

async function connectDevice(port) {
    try {
        const response = await fetch('/api/pico/connect', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({port})
        });
        
        if (response.ok) {
            addLogMessage(`Connecting to ${port}...`, 'info');
            setTimeout(refreshDevices, 1000);
        } else {
            const text = await response.text();
            addLogMessage(`Failed to connect to ${port}: ${text}`, 'error');
        }
    } catch (error) {
        addLogMessage(`Error connecting to ${port}: ${error.message}`, 'error');
    }
}

async function disconnectDevice(port) {
    try {
        const response = await fetch('/api/pico/disconnect', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({port})
        });
        
        if (response.ok) {
            addLogMessage(`Disconnected from ${port}`, 'info');
            setTimeout(refreshDevices, 500);
        }
    } catch (error) {
        addLogMessage(`Error disconnecting from ${port}: ${error.message}`, 'error');
    }
}

async function connectAllDevices() {
    const disconnectedDevices = Object.entries(devices)
        .filter(([port, device]) => !device.connected)
        .map(([port]) => port);
    
    if (disconnectedDevices.length === 0) {
        addLogMessage('All devices are already connected', 'info');
        return;
    }
    
    addLogMessage(`Connecting to ${disconnectedDevices.length} devices...`, 'info');
    
    for (const port of disconnectedDevices) {
        await connectDevice(port);
        await new Promise(resolve => setTimeout(resolve, 500)); // Small delay between connections
    }
}

async function disconnectAllDevices() {
    const connectedDevices = Object.entries(devices)
        .filter(([port, device]) => device.connected)
        .map(([port]) => port);
    
    if (connectedDevices.length === 0) {
        addLogMessage('No devices are connected', 'info');
        return;
    }
    
    for (const port of connectedDevices) {
        await disconnectDevice(port);
    }
}

// ============================================================================
// Macro Management
// ============================================================================

async function loadMacrosList() {
    try {
        const response = await fetch('/api/macros');
        const macros = await response.json();
        
        const select = document.getElementById('macro_select');
        select.innerHTML = '<option value="">Choose a macro...</option>';
        
        macros.forEach(macro => {
            const option = document.createElement('option');
            option.value = macro;
            option.textContent = macro;
            select.appendChild(option);
        });
    } catch (error) {
        addLogMessage(`Error loading macros: ${error.message}`, 'error');
    }
}

function getSelectedDevices() {
    const select = document.getElementById('target_devices');
    const selectedOptions = Array.from(select.selectedOptions);
    
    if (selectedOptions.some(option => option.value === 'all')) {
        return null; // null means all connected devices
    }
    
    return selectedOptions.map(option => option.value);
}

async function loadMacroToPicos() {
    const macroName = document.getElementById('macro_select').value;
    if (!macroName) {
        addLogMessage('Please select a macro first', 'error');
        return;
    }
    
    const devicePorts = getSelectedDevices();
    const targetText = devicePorts ? `${devicePorts.length} selected devices` : 'all connected devices';
    
    try {
        const response = await fetch('/api/pico/load_macro', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                macro_name: macroName,
                device_ports: devicePorts
            })
        });
        
        if (response.ok) {
            const data = await response.json();
            const successCount = Object.values(data.results).filter(success => success).length;
            const totalCount = Object.keys(data.results).length;
            
            addLogMessage(`Loaded macro "${macroName}" to ${successCount}/${totalCount} devices`, 'success');
        } else {
            const text = await response.text();
            addLogMessage(`Failed to load macro: ${text}`, 'error');
        }
    } catch (error) {
        addLogMessage(`Error loading macro: ${error.message}`, 'error');
    }
}

async function startMacroOnPicos() {
    const devicePorts = getSelectedDevices();
    const targetText = devicePorts ? `${devicePorts.length} selected devices` : 'all connected devices';
    
    try {
        const response = await fetch('/api/pico/start_macro', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({device_ports: devicePorts})
        });
        
        if (response.ok) {
            const data = await response.json();
            const successCount = Object.values(data.results).filter(success => success).length;
            const totalCount = Object.keys(data.results).length;
            
            addLogMessage(`Started macro execution on ${successCount}/${totalCount} devices`, 'success');
            setTimeout(refreshDevices, 1000);
        } else {
            const text = await response.text();
            addLogMessage(`Failed to start macro: ${text}`, 'error');
        }
    } catch (error) {
        addLogMessage(`Error starting macro: ${error.message}`, 'error');
    }
}

async function stopMacroOnPicos() {
    const devicePorts = getSelectedDevices();
    
    try {
        const response = await fetch('/api/pico/stop_macro', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({device_ports: devicePorts})
        });
        
        if (response.ok) {
            const data = await response.json();
            const successCount = Object.values(data.results).filter(success => success).length;
            const totalCount = Object.keys(data.results).length;
            
            addLogMessage(`Stopped macro execution on ${successCount}/${totalCount} devices`, 'info');
            setTimeout(refreshDevices, 1000);
        } else {
            const text = await response.text();
            addLogMessage(`Failed to stop macro: ${text}`, 'error');
        }
    } catch (error) {
        addLogMessage(`Error stopping macro: ${error.message}`, 'error');
    }
}

// ============================================================================
// Macro Editor
// ============================================================================

function initializeEditor() {
    if (shouldUseFallback()) {
        // Use simple textarea for mobile/problematic browsers
        document.getElementById('macro_editor').style.display = 'none';
        document.getElementById('mobile-fallback-editor').style.display = 'block';
        editor = {
            getValue: () => document.getElementById('mobile-fallback-editor').value,
            setValue: (val) => { document.getElementById('mobile-fallback-editor').value = val; }
        };
    } else {
        // Use CodeMirror for desktop browsers
        document.getElementById('mobile-fallback-editor').style.display = 'none';
        editor = CodeMirror.fromTextArea(document.getElementById('macro_editor'), {
            mode: 'shell',
            theme: 'dracula',
            lineNumbers: true,
            lineWrapping: true,
            indentUnit: 2,
            tabSize: 2,
            viewportMargin: Infinity
        });
    }
}

function shouldUseFallback() {
    const userAgent = navigator.userAgent.toLowerCase();
    const isProblematicBrowser = userAgent.includes('chrome') && userAgent.includes('mobile');
    const preferFallback = localStorage.getItem('useFallbackEditor') === 'true';
    return preferFallback || isProblematicBrowser;
}

async function editMacro() {
    const selectedMacro = document.getElementById('macro_select').value;
    if (!selectedMacro) {
        addLogMessage('Please select a macro to edit', 'error');
        return;
    }
    
    try {
        const response = await fetch(`/api/macros/${selectedMacro}`);
        if (response.ok) {
            const content = await response.text();
            document.getElementById('macro_name').value = selectedMacro;
            editor.setValue(content);
            currentMacroName = selectedMacro;
            document.getElementById('macro-modal').classList.add('show');
        }
    } catch (error) {
        addLogMessage(`Error loading macro: ${error.message}`, 'error');
    }
}

function newMacro() {
    editor.setValue('# New macro\n# Enter your commands here...\n\n');
    document.getElementById('macro_name').value = '';
    currentMacroName = '';
    document.getElementById('macro-modal').classList.add('show');
}

async function saveMacro() {
    const name = document.getElementById('macro_name').value.trim();
    const content = editor.getValue();
    
    if (!name) {
        addLogMessage('Please enter a filename', 'error');
        return;
    }
    
    try {
        const response = await fetch('/api/macros', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name, content})
        });
        
        if (response.ok) {
            addLogMessage(`Saved macro: ${name}`, 'success');
            document.getElementById('macro-modal').classList.remove('show');
            await loadMacrosList();
            document.getElementById('macro_select').value = name;
            currentMacroName = name;
        } else {
            const text = await response.text();
            addLogMessage(`Failed to save macro: ${text}`, 'error');
        }
    } catch (error) {
        addLogMessage(`Error saving macro: ${error.message}`, 'error');
    }
}

// ============================================================================
// Event Listeners
// ============================================================================

function initializeEventListeners() {
    // Device management
    document.getElementById('refresh-devices').addEventListener('click', refreshDevices);
    document.getElementById('connect_all').addEventListener('click', connectAllDevices);
    document.getElementById('disconnect_all').addEventListener('click', disconnectAllDevices);
    
    // Macro controls
    document.getElementById('load_macro').addEventListener('click', loadMacroToPicos);
    document.getElementById('start_macro').addEventListener('click', startMacroOnPicos);
    document.getElementById('stop_macro').addEventListener('click', stopMacroOnPicos);
    document.getElementById('edit_macro').addEventListener('click', editMacro);
    document.getElementById('new_macro').addEventListener('click', newMacro);
    
    // Modal controls
    document.getElementById('save_macro').addEventListener('click', saveMacro);
    document.getElementById('cancel_edit').addEventListener('click', () => {
        document.getElementById('macro-modal').classList.remove('show');
    });
    document.getElementById('modal-close').addEventListener('click', () => {
        document.getElementById('macro-modal').classList.remove('show');
    });
    
    // Log controls
    document.getElementById('clear-log').addEventListener('click', clearLog);
    
    // Auto-refresh devices periodically
    setInterval(refreshDevices, 5000);
}

// ============================================================================
// Logging
// ============================================================================

function addLogMessage(message, type = 'info') {
    const logContainer = document.getElementById('log');
    const timestamp = new Date().toLocaleTimeString();
    
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${type}`;
    logEntry.innerHTML = `<span class="timestamp">[${timestamp}]</span> ${message}`;
    
    logContainer.appendChild(logEntry);
    logContainer.scrollTop = logContainer.scrollHeight;
    
    // Keep only last 100 messages
    while (logContainer.children.length > 100) {
        logContainer.removeChild(logContainer.firstChild);
    }
}

function clearLog() {
    document.getElementById('log').innerHTML = '';
    addLogMessage('Log cleared', 'info');
}

// ============================================================================
// Utility Functions
// ============================================================================

// Close modals when clicking outside
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('show');
    }
});