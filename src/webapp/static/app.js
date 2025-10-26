/**
 * PKMN Autoshine - Clean Web UI Application
 * 
 * Simplified macro management interface without bloat.
 * Features: WebSocket communication, macro CRUD, execution controls, live logging
 */

class AutoshineApp {
    constructor() {
        // State
        this.macros = [];
        this.selectedMacro = null;
        this.devices = [];
        this.selectedDevice = null;  // null = no device selected
        this.ws = null;
        this.isEditing = false;
        this.editingMacro = null;
        
        // DOM elements
        this.elements = {
            macroList: document.getElementById('macroList'),
            currentMacro: document.getElementById('currentMacro'),
            picoCount: document.getElementById('picoCount'),
            picoDevices: document.getElementById('picoDevices'),
            logsContainer: document.getElementById('logsContainer'),
            editorModal: document.getElementById('editorModal'),
            editorTitle: document.getElementById('editorTitle'),
            macroName: document.getElementById('macroName'),
            macroEditor: document.getElementById('macroEditor'),
            uploadBtn: document.getElementById('uploadBtn'),
            runBtn: document.getElementById('runBtn'),
            stopBtn: document.getElementById('stopBtn'),
            editBtn: document.getElementById('editBtn'),
            deleteBtn: document.getElementById('deleteBtn')
        };
        
        // Initialize
        this.init();
    }
    
    async init() {
        this.log('Initializing application...', 'info');
        await this.loadMacros();
        await this.loadDevices();
        this.connectWebSocket();
        this.setupKeyboardShortcuts();
        this.setupVisibilityHandler();
        this.startDeviceStatusPolling();
    }
    
    setupVisibilityHandler() {
        // Handle mobile hibernation/wake - reconnect WebSocket and refresh when page becomes visible
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                // Page became visible again
                this.log('Page resumed, refreshing connection...', 'info');
                
                // Reconnect WebSocket if disconnected
                if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
                    this.connectWebSocket();
                }
                
                // Refresh devices and macros
                this.loadDevices(true);
                this.loadMacros();
            }
        });
    }
    
    startDeviceStatusPolling() {
        // Poll device status every 2 seconds to update iteration counts
        setInterval(async () => {
            if (this.devices.length > 0) {
                await this.loadDevices(true);  // silent mode
            }
        }, 2000);
    }
    
    // ===== WebSocket Management =====
    
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;
        
        this.log(`Connecting to ${wsUrl}...`, 'info');
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            this.log('✓ Connected to server', 'success');
        };
        
        this.ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'log') {
                    this.log(data.message, data.level || 'info');
                } else if (data.type === 'status') {
                    this.log(data.message || 'Status update');
                }
            } catch (e) {
                this.log(event.data);
            }
        };
        
        this.ws.onerror = (error) => {
            this.log('WebSocket error', 'error');
        };
        
        this.ws.onclose = () => {
            this.log('⚠ Disconnected from server. Reconnecting in 3s...', 'warning');
            setTimeout(() => this.connectWebSocket(), 3000);
        };
    }
    
    async checkPicoStatus() {
        try {
            const response = await fetch('/api/pico/devices');
            if (!response.ok) throw new Error('Failed to get devices');
            
            this.devices = await response.json();
            this.renderDevices();
            this.updateDeviceSelect();
        } catch (error) {
            this.log(`Error loading devices: ${error.message}`, 'error');
        }
    }
    
    async loadDevices(silent = false) {
        try {
            await this.checkPicoStatus();
            if (!silent) {
                // Only log on explicit user action, not during polling
            }
        } catch (error) {
            if (!silent) {
                this.log(`Error loading devices: ${error.message}`, 'error');
            }
        }
    }
    
    async refreshDevices() {
        try {
            const response = await fetch('/api/pico/refresh', { method: 'POST' });
            if (!response.ok) throw new Error('Failed to refresh devices');
            
            const data = await response.json();
            this.devices = data.devices;
            this.renderDevices();
            
            if (data.new_connections > 0) {
                this.log(`✓ Found ${data.new_connections} new device(s)`, 'success');
            } else {
                this.log('No new devices found', 'info');
            }
        } catch (error) {
            this.log(`Error refreshing devices: ${error.message}`, 'error');
        }
    }
    
    renderDevices() {
        this.elements.picoCount.textContent = this.devices.length;
        
        if (this.devices.length === 0) {
            this.elements.picoDevices.innerHTML = `
                <div style="color: var(--text-secondary); text-align: center; padding: 0.5rem;">
                    No devices connected. Click refresh to scan.
                </div>
            `;
            this.selectedDevice = null;
            this.updateButtonStates();
            return;
        }
        
        this.elements.picoDevices.innerHTML = this.devices.map(device => {
            // Determine Bluetooth status color and label
            let btColor, btLabel;
            switch(device.bt_status) {
                case 'connected':
                    btColor = '#4ade80';  // Green
                    btLabel = 'BT Connected';
                    break;
                case 'pairing':
                    btColor = '#60a5fa';  // Blue
                    btLabel = 'BT Pairing';
                    break;
                case 'disconnected':
                default:
                    btColor = '#ef4444';  // Red
                    btLabel = 'BT Disconnected';
                    break;
            }
            
            const isSelected = this.selectedDevice === device.port;
            
            return `
                <div style="background: var(--bg-tertiary); padding: 0.5rem; border-radius: 4px; border: 1px solid ${isSelected ? 'var(--accent-primary)' : 'var(--border-color)'}; display: flex; justify-content: space-between; align-items: center; font-size: 0.85rem;">
                    <div style="display: flex; align-items: center; gap: 0.75rem; flex: 1; min-width: 0;">
                        <input 
                            type="radio" 
                            name="targetDevice" 
                            value="${this.escapeHtml(device.port)}"
                            ${isSelected ? 'checked' : ''}
                            onchange="app.selectDevice('${this.escapeHtml(device.port)}')"
                            style="cursor: pointer; width: 16px; height: 16px; margin: 0;"
                            title="Select as target device">
                        <span 
                            id="name-${this.escapeHtml(device.port)}" 
                            style="font-weight: 500; color: var(--accent-primary); white-space: nowrap; cursor: pointer;" 
                            onclick="app.editDeviceName('${this.escapeHtml(device.port)}')"
                            title="Click to edit nickname">
                            ${this.escapeHtml(device.name)}
                        </span>
                        <span style="color: ${btColor}; font-size: 1rem;" title="${btLabel}">●</span>
                        ${device.is_uploading ? 
                            '<span style="color: var(--warning);">⏳ Uploading</span>' :
                            device.current_macro ? 
                                `<span style="color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${this.escapeHtml(device.current_macro)}</span>` : 
                                '<span style="color: var(--text-secondary);">Idle</span>'}
                    </div>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        ${device.iteration_count > 0 ? 
                            `<div style="color: var(--accent-primary); font-weight: 500; white-space: nowrap;">#${device.iteration_count}</div>` : 
                            ''}
                        <button 
                            onclick="app.enablePairing('${this.escapeHtml(device.port)}')" 
                            class="small secondary" 
                            style="padding: 0.25rem 0.5rem; font-size: 0.75rem;"
                            ${!device.connected ? 'disabled' : ''}
                            title="Enable pairing mode on this device">
                            🔗 Pair
                        </button>
                    </div>
                </div>
            `;
        }).join('');
        
        // Validate that selectedDevice still exists
        if (this.selectedDevice && !this.devices.some(d => d.port === this.selectedDevice)) {
            this.selectedDevice = null;
        }
        
        this.updateButtonStates();
    }
    
    selectDevice(port) {
        this.selectedDevice = port;
        const device = this.devices.find(d => d.port === port);
        const deviceName = device ? device.name : port;
        this.log(`Target: ${deviceName}`, 'info');
        this.renderDevices();
        this.updateButtonStates();
    }
    
    handleWebSocketMessage(data) {
        // Simplified - just handle logs
        if (data.type === 'log') {
            this.log(data.message, data.level || 'info');
        }
    }
    
    // ===== Macro Management =====
    
    async loadMacros() {
        try {
            const response = await fetch('/api/macros');
            if (!response.ok) throw new Error('Failed to load macros');
            
            // API returns array of {name, size, modified} objects
            const macroObjects = await response.json();
            this.macros = macroObjects.map(m => m.name).sort((a, b) => a.localeCompare(b));
            
            this.renderMacroList();
            this.log(`Loaded ${this.macros.length} macro(s)`, 'info');
        } catch (error) {
            this.log(`Error loading macros: ${error.message}`, 'error');
            this.macros = [];
            this.renderMacroList();
        }
    }
    
    renderMacroList() {
        if (this.macros.length === 0) {
            this.elements.macroList.innerHTML = `
                <div class="macro-item" style="color: var(--text-secondary); text-align: center; padding: 2rem;">
                    No macros found. Click "New" to create one.
                </div>
            `;
            return;
        }
        
        this.elements.macroList.innerHTML = this.macros.map(name => `
            <div class="macro-item ${this.selectedMacro === name ? 'selected' : ''}" 
                 onclick="app.selectMacro('${name.replace(/'/g, "\\'")}')">
                ${this.escapeHtml(name)}
            </div>
        `).join('');
    }
    
    selectMacro(name) {
        this.selectedMacro = name;
        this.renderMacroList();
        this.updateButtonStates();
        this.elements.currentMacro.textContent = name;
        this.log(`Selected macro: ${name}`, 'info');
    }
    
    async newMacro() {
        this.isEditing = true;
        this.editingMacro = null;
        this.elements.editorTitle.textContent = 'New Macro';
        this.elements.macroName.value = '';
        this.elements.macroEditor.value = '';
        this.elements.editorModal.classList.add('active');
        this.elements.macroName.focus();
    }
    
    async editMacro() {
        if (!this.selectedMacro) {
            this.log('No macro selected', 'warning');
            return;
        }
        
        try {
            const response = await fetch(`/api/macros/${encodeURIComponent(this.selectedMacro)}`);
            if (!response.ok) throw new Error('Failed to load macro content');
            
            const content = await response.text();
            
            this.isEditing = true;
            this.editingMacro = this.selectedMacro;
            this.elements.editorTitle.textContent = 'Edit Macro';
            this.elements.macroName.value = this.selectedMacro;
            this.elements.macroEditor.value = content;
            this.elements.editorModal.classList.add('active');
            this.elements.macroEditor.focus();
        } catch (error) {
            this.log(`Error loading macro: ${error.message}`, 'error');
        }
    }
    
    async saveMacro() {
        const name = this.elements.macroName.value.trim();
        const content = this.elements.macroEditor.value;
        
        if (!name) {
            this.log('Filename cannot be empty', 'warning');
            this.elements.macroName.focus();
            return;
        }
        
        try {
            let response;
            
            if (this.editingMacro) {
                // Update existing macro
                response = await fetch(`/api/macros/${encodeURIComponent(this.editingMacro)}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content })
                });
            } else {
                // Create new macro
                response = await fetch('/api/macros', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name, content })
                });
            }
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(errorText || 'Failed to save macro');
            }
            
            this.log(`✓ Saved macro: ${name}`, 'success');
            this.closeEditor();
            await this.loadMacros();
            this.selectMacro(name);
        } catch (error) {
            this.log(`Error saving macro: ${error.message}`, 'error');
        }
    }
    
    async deleteMacro() {
        if (!this.selectedMacro) {
            this.log('No macro selected', 'warning');
            return;
        }
        
        if (!confirm(`Delete macro "${this.selectedMacro}"?`)) {
            return;
        }
        
        try {
            const response = await fetch(`/api/macros/${encodeURIComponent(this.selectedMacro)}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                throw new Error('Failed to delete macro');
            }
            
            this.log(`✓ Deleted macro: ${this.selectedMacro}`, 'success');
            this.selectedMacro = null;
            await this.loadMacros();
            this.updateButtonStates();
        } catch (error) {
            this.log(`Error deleting macro: ${error.message}`, 'error');
        }
    }
    
    closeEditor() {
        this.elements.editorModal.classList.remove('active');
        this.isEditing = false;
        this.editingMacro = null;
    }
    
    // ===== Macro Execution Controls =====
    
    async uploadMacro() {
        if (!this.selectedMacro) {
            this.log('No macro selected', 'warning');
            return;
        }
        
        if (!this.selectedDevice) {
            this.log('No device selected', 'warning');
            return;
        }
        
        try {
            const body = {
                name: this.selectedMacro,
                port: this.selectedDevice
            };
            
            const response = await fetch('/api/upload', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            });
            
            if (!response.ok) {
                const error = await response.text();
                throw new Error(error);
            }
            
            const device = this.devices.find(d => d.port === this.selectedDevice);
            const deviceName = device ? device.name : this.selectedDevice;
            
            this.log(`📤 Uploaded '${this.selectedMacro}' to ${deviceName}`, 'success');
            
            // Refresh device status to show current macro
            setTimeout(() => this.loadDevices(), 500);
            
            this.updateButtonStates();
        } catch (error) {
            this.log(`Error uploading macro: ${error.message}`, 'error');
        }
    }
    
    async runMacro() {
        if (!this.selectedDevice) {
            this.log('No device selected', 'warning');
            return;
        }
        
        try {
            // Send START_MACRO command to run continuously
            const body = {
                command: 'START_MACRO',
                port: this.selectedDevice
            };
            
            // Send via WebSocket for real-time execution
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify(body));
            }
            
            const device = this.devices.find(d => d.port === this.selectedDevice);
            const deviceName = device ? device.name : this.selectedDevice;
            
            this.log(`▶️ Running macro on ${deviceName} (continuous)`, 'success');
            
            this.updateButtonStates();
        } catch (error) {
            this.log(`Error running macro: ${error.message}`, 'error');
        }
    }
    
    async stopMacro() {
        if (!this.selectedDevice) {
            this.log('No device selected', 'warning');
            return;
        }
        
        try {
            const body = {
                command: 'STOP_MACRO',
                port: this.selectedDevice
            };
            
            // Send via WebSocket
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify(body));
            }
            
            const device = this.devices.find(d => d.port === this.selectedDevice);
            const deviceName = device ? device.name : this.selectedDevice;
            
            this.log(`⏹️ Stopped macro on ${deviceName}`, 'info');
            
            this.updateButtonStates();
        } catch (error) {
            this.log(`Error stopping macro: ${error.message}`, 'error');
        }
    }
    
    // ===== Pairing Control =====
    
    async enablePairing(port) {
        try {
            const device = this.devices.find(d => d.port === port);
            const deviceName = device ? device.name : port;
            
            const response = await fetch('/api/pico/pair', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ port })
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(errorText || 'Failed to enable pairing mode');
            }
            
            this.log(`🔗 Pairing mode enabled on ${deviceName}. Go to Switch Settings > Controllers > Change Grip/Order to pair.`, 'success');
        } catch (error) {
            this.log(`Error enabling pairing: ${error.message}`, 'error');
        }
    }
    
    async editDeviceName(port) {
        const device = this.devices.find(d => d.port === port);
        if (!device) return;
        
        const currentName = device.name;
        const newName = prompt(`Enter nickname for device (leave empty to reset):`, currentName);
        
        // User cancelled
        if (newName === null) return;
        
        try {
            const response = await fetch('/api/pico/nickname', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    port: port,
                    nickname: newName 
                })
            });
            
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(errorText || 'Failed to set nickname');
            }
            
            const data = await response.json();
            
            // Update local device list
            device.name = data.name;
            this.renderDevices();
            
            if (newName) {
                this.log(`✓ Set nickname to "${data.name}"`, 'success');
            } else {
                this.log(`✓ Reset nickname to default`, 'success');
            }
        } catch (error) {
            this.log(`Error setting nickname: ${error.message}`, 'error');
        }
    }
    
    // ===== Logging =====
    
    log(message, level = 'default') {
        const timestamp = new Date().toLocaleTimeString();
        const entry = document.createElement('div');
        entry.className = `log-entry ${level}`;
        entry.textContent = `[${timestamp}] ${message}`;
        
        this.elements.logsContainer.appendChild(entry);
        
        // Auto-scroll to bottom
        this.elements.logsContainer.scrollTop = this.elements.logsContainer.scrollHeight;
        
        // Limit log entries to prevent memory issues
        const maxLogs = 500;
        while (this.elements.logsContainer.children.length > maxLogs) {
            this.elements.logsContainer.removeChild(this.elements.logsContainer.firstChild);
        }
    }
    
    clearLogs() {
        this.elements.logsContainer.innerHTML = '';
        this.log('Logs cleared', 'info');
    }
    
    // ===== Utilities =====
    
    updateButtonStates() {
        const hasSelection = this.selectedMacro !== null;
        const hasDevices = this.devices.length > 0;
        const hasDeviceSelected = this.selectedDevice !== null;
        
        // Edit and Delete require a macro selection
        this.elements.editBtn.disabled = !hasSelection;
        this.elements.deleteBtn.disabled = !hasSelection;
        
        // Upload requires both a macro AND a device to be selected
        this.elements.uploadBtn.disabled = !hasSelection || !hasDeviceSelected;
        
        // Run requires a device to be selected (macro is optional since device might have one already)
        this.elements.runBtn.disabled = !hasDeviceSelected;
        
        // Stop only requires a device to be selected
        this.elements.stopBtn.disabled = !hasDeviceSelected;
    }
    
    formatTime(seconds) {
        if (seconds < 0) return '0:00';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        } else {
            return `${minutes}:${secs.toString().padStart(2, '0')}`;
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl+S or Cmd+S to save in editor
            if ((e.ctrlKey || e.metaKey) && e.key === 's' && this.isEditing) {
                e.preventDefault();
                this.saveMacro();
            }
            
            // Escape to close editor
            if (e.key === 'Escape' && this.isEditing) {
                this.closeEditor();
            }
        });
    }
}

// Initialize app when DOM is ready
let app;
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        app = new AutoshineApp();
    });
} else {
    app = new AutoshineApp();
}
