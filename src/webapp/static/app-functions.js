/**
 * PKMN Autoshine - Application Functions (Part 2)
 * 
 * This file contains the remaining application functions including macro management,
 * control functions, alert system, and initialization logic.
 */

// ============================================================================
// Macro Management Functions
// ============================================================================

/**
 * Load the list of available macros from the server.
 */
async function listMacros() {
  try {
    const res = await fetch('/api/macros');
    if (!res.ok) return;
    
    const names = await res.json();
    
    // Populate macro dropdown
    const select = document.getElementById('macro_select');
    if (select) {
      select.innerHTML = '<option value="">Choose a macro...</option>';
      
      names.forEach(name => {
        const option = document.createElement('option');
        option.value = name;
        option.textContent = name;
        select.appendChild(option);
      });
    }
  } catch (error) {
    console.error('Failed to list macros:', error);
    addLogMessage('Failed to load macro list', 'error');
  }
}

/**
 * Load a specific macro file into the editor.
 * @param {string} name - The macro filename to load
 */
async function loadMacro(name) {
  if (!name) return;
  
  try {
    const res = await fetch(`/api/macros/${encodeURIComponent(name)}`);
    if (!res.ok) throw new Error(`Failed to load macro: ${res.status}`);
    
    const content = await res.text();
    if (editor) {
      editor.setValue(content);
    }
    
    const macroNameElement = document.getElementById('macro_name');
    if (macroNameElement) macroNameElement.value = name;
    
    currentMacroName = name;
    addLogMessage(`Loaded macro: ${name}`, 'success');
  } catch (error) {
    console.error('Failed to load macro:', error);
    addLogMessage(`Failed to load macro: ${name}`, 'error');
  }
}

/**
 * Save the current macro content to a file.
 */
async function saveMacro() {
  const macroNameElement = document.getElementById('macro_name');
  const name = macroNameElement ? macroNameElement.value.trim() : '';
  const content = editor ? editor.getValue() : '';
  
  if (!name) {
    addLogMessage('Please enter a filename', 'error');
    return;
  }
  
  if (!name.endsWith('.txt')) {
    if (macroNameElement) macroNameElement.value = name + '.txt';
  }
  
  try {
    const res = await fetch('/api/macros', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ name: name.endsWith('.txt') ? name : name + '.txt', content })
    });
    
    if (!res.ok) throw new Error(`Save failed: ${res.status}`);
    
    await listMacros();
    currentMacroName = name;
    addLogMessage(`Saved macro: ${name}`, 'success');
    
    // Update select dropdown
    const macroSelect = document.getElementById('macro_select');
    if (macroSelect) macroSelect.value = name;
    
    // Close modal
    hideModal();
  } catch (error) {
    console.error('Failed to save macro:', error);
    addLogMessage(`Failed to save macro: ${error.message}`, 'error');
  }
}

/**
 * Create a new macro file.
 */
function newMacro() {
  if (editor) {
    editor.setValue('# New macro\n# Enter your commands here...\n\n');
  }
  
  const macroNameElement = document.getElementById('macro_name');
  if (macroNameElement) macroNameElement.value = '';
  
  currentMacroName = '';
  
  const modalTitle = document.getElementById('modal-title');
  if (modalTitle) modalTitle.innerHTML = '<i class="fas fa-plus"></i> Create New Macro';
  
  showModal();
  addLogMessage('Creating new macro', 'info');
}

/**
 * Start running the selected macro.
 */
async function runMacro() {
  const macroSelect = document.getElementById('macro_select');
  const selectedMacro = macroSelect ? macroSelect.value : '';
  
  if (!selectedMacro) {
    addLogMessage('Please select a macro to run', 'error');
    return;
  }
  
  try {
    const res = await fetch('/api/select', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ name: selectedMacro })
    });
    
    if (!res.ok) throw new Error(`Failed to run macro: ${res.status}`);
    
    addLogMessage(`Started macro: ${selectedMacro}`, 'success');
  } catch (error) {
    console.error('Failed to run macro:', error);
    addLogMessage(`Failed to run macro: ${error.message}`, 'error');
  }
}

/**
 * Run the selected macro exactly once.
 */
async function runOnce() {
  const macroSelect = document.getElementById('macro_select');
  const selectedMacro = macroSelect ? macroSelect.value : '';
  
  if (!selectedMacro) {
    addLogMessage('Please select a macro to run once', 'error');
    return;
  }
  
  try {
    const res = await fetch('/api/run-once', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ name: selectedMacro })
    });
    
    if (!res.ok) throw new Error(`Failed to run macro once: ${res.status}`);
    
    addLogMessage(`Running macro once: ${selectedMacro}`, 'success');
  } catch (error) {
    console.error('Failed to run macro once:', error);
    addLogMessage(`Failed to run macro once: ${selectedMacro}`, 'error');
  }
}

/**
 * Edit the currently selected macro.
 */
async function editMacro() {
  const macroSelect = document.getElementById('macro_select');
  const selectedMacro = macroSelect ? macroSelect.value : '';
  
  if (!selectedMacro) {
    addLogMessage('Please select a macro to edit', 'warning');
    return;
  }
  
  try {
    const res = await fetch(`/api/macros/${encodeURIComponent(selectedMacro)}`);
    if (res.ok) {
      const content = await res.text();
      if (editor) {
        editor.setValue(content);
      }
      
      const macroNameElement = document.getElementById('macro_name');
      if (macroNameElement) macroNameElement.value = selectedMacro;
      
      const modalTitle = document.getElementById('modal-title');
      if (modalTitle) modalTitle.innerHTML = '<i class="fas fa-edit"></i> Edit Macro: ' + selectedMacro;
      
      showModal();
    } else {
      addLogMessage('Failed to load macro', 'error');
    }
  } catch (error) {
    addLogMessage('Error loading macro: ' + error.message, 'error');
  }
}

// ============================================================================
// Modal Management
// ============================================================================

/**
 * Show the macro editor modal.
 */
function showModal() {
  const modal = document.getElementById('macro-modal');
  if (modal) {
    modal.style.display = 'flex';
    setTimeout(() => {
      if (editor && editor.refresh) {
        editor.refresh();
        editor.focus();
      }
    }, 100);
  }
}

/**
 * Hide the macro editor modal.
 */
function hideModal() {
  const modal = document.getElementById('macro-modal');
  if (modal) modal.style.display = 'none';
}

/**
 * Show the settings modal.
 */
function showSettings() {
  // Reset the alert interval modification flag when opening settings
  alertIntervalUserModified = false;
  const modal = document.getElementById('settings-modal');
  if (modal) modal.style.display = 'flex';
}

/**
 * Hide the settings modal.
 */
function hideSettings() {
  const modal = document.getElementById('settings-modal');
  if (modal) modal.style.display = 'none';
}

// ============================================================================
// Control Functions
// ============================================================================

/**
 * Send a command to the server via WebSocket.
 * @param {string} cmd - The command to send
 */
function sendCommand(cmd) {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ cmd }));
    addLogMessage(`Sent command: ${cmd}`, 'info');
  } else {
    addLogMessage('Not connected to server', 'error');
  }
}

/**
 * Reset macro execution metrics.
 */
async function resetMetrics() {
  try {
    const res = await fetch('/api/reset-metrics', {
      method: 'POST',
      headers: { 'content-type': 'application/json' }
    });
    
    if (!res.ok) throw new Error(`Failed to reset metrics: ${res.status}`);
    
    // Immediately update the UI
    const elements = {
      'iteration_count': '0',
      'runtime_display': '0:00',
      'time_per_iteration': '--'
    };
    
    Object.entries(elements).forEach(([id, value]) => {
      const element = document.getElementById(id);
      if (element) element.textContent = value;
    });
    
    addLogMessage('Metrics reset successfully', 'success');
  } catch (error) {
    console.error('Failed to reset metrics:', error);
    addLogMessage(`Failed to reset metrics: ${error.message}`, 'error');
  }
}

// ============================================================================
// Alert System
// ============================================================================

/**
 * Set the alert interval for iteration notifications.
 */
async function setAlerts() {
  const alertInput = document.getElementById('alert_interval');
  const interval = alertInput ? parseInt(alertInput.value) || 0 : 0;
  
  try {
    const res = await fetch('/api/alerts/set', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ alert_interval: interval })
    });
    
    if (!res.ok) throw new Error(`Failed to set alerts: ${res.status}`);
    
    // Reset the user modified flag since the setting was successfully applied
    alertIntervalUserModified = false;
    addLogMessage(`Alert interval set to ${interval} iterations${interval === 0 ? ' (disabled)' : ''}`, 'success');
  } catch (error) {
    console.error('Failed to set alerts:', error);
    addLogMessage(`Failed to set alerts: ${error.message}`, 'error');
  }
}

/**
 * Request browser notification permission.
 */
function requestNotificationPermission() {
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission().then(permission => {
      if (permission === 'granted') {
        addLogMessage('Browser notifications enabled', 'success');
      } else {
        addLogMessage('Browser notifications denied', 'warning');
        const notificationCheckbox = document.getElementById('enable_notifications');
        if (notificationCheckbox) notificationCheckbox.checked = false;
      }
    });
  }
}

/**
 * Show alert notification when iteration threshold is reached.
 * @param {number} iterations - The number of iterations completed
 */
function showAlert(iterations) {
  const enableNotifications = document.getElementById('enable_notifications')?.checked ?? true;
  const enableSound = document.getElementById('enable_sound')?.checked ?? true;
  const pauseOnAlert = document.getElementById('pause_on_alert')?.checked ?? false;
  
  const message = `Macro completed ${iterations} iterations`;
  
  // Show browser notification
  if (enableNotifications && 'Notification' in window && Notification.permission === 'granted') {
    new Notification('PKMN-Autoshine Alert', {
      body: message,
      icon: 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="gold"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>',
      tag: 'iteration-alert',
      requireInteraction: true
    });
  }
  
  // Play sound
  if (enableSound) {
    playAlertSound();
  }
  
  // Pause macro if enabled
  if (pauseOnAlert && ws) {
    ws.send(JSON.stringify({action: 'pause'}));
    addLogMessage(`⏸️ Macro paused automatically due to alert at ${iterations} iterations`, 'warning');
  }
  
  // Also show in log
  addLogMessage(`🔔 ${message}`, 'warning');
}

/**
 * Play alert sound using Web Audio API.
 */
function playAlertSound() {
  try {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
    oscillator.type = 'sine';
    
    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
    
    oscillator.start();
    oscillator.stop(audioContext.currentTime + 0.5);
  } catch (error) {
    console.warn('Could not play alert sound:', error);
  }
}

// ============================================================================
// Adapter Management
// ============================================================================

/**
 * Set the preferred adapter type.
 */
async function setAdapter() {
  const adapterSelect = document.getElementById('adapter_select');
  const adapter = adapterSelect ? adapterSelect.value || null : null;
  
  try {
    const res = await fetch('/api/adapters/select', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ adapter })
    });
    
    if (!res.ok) throw new Error(`Failed to set adapter: ${res.status}`);
    
    const result = await res.json();
    addLogMessage(result.message, 'success');
    await updateAdapterStatus();
  } catch (error) {
    console.error('Failed to set adapter:', error);
    addLogMessage(`Failed to set adapter: ${error.message}`, 'error');
  }
}

/**
 * Test adapter connectivity.
 */
async function testAdapters() {
  const button = document.getElementById('test_adapters');
  if (!button) return;
  
  const originalText = button.innerHTML;
  
  button.classList.add('loading');
  button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Testing...';
  
  try {
    addLogMessage('Testing adapter connectivity...', 'info');
    await updateAdapterStatus();
    addLogMessage('Adapter test completed', 'success');
  } catch (error) {
    console.error('Failed to test adapters:', error);
    addLogMessage('Adapter test failed', 'error');
  } finally {
    button.classList.remove('loading');
    button.innerHTML = originalText;
  }
}

// ============================================================================
// Event Listeners Setup
// ============================================================================

/**
 * Set up all event listeners for the application.
 */
function setupEventListeners() {
  // Control buttons
  const pauseBtn = document.getElementById('pause');
  if (pauseBtn) {
    pauseBtn.onclick = () => {
      sendCommand('pause');
    };
  }
  
  const forceStopBtn = document.getElementById('force_stop');
  if (forceStopBtn) {
    forceStopBtn.onclick = () => {
      sendCommand('force_stop');
    };
  }

  // Macro controls
  const runMacroBtn = document.getElementById('run_macro');
  if (runMacroBtn) runMacroBtn.onclick = runMacro;
  
  const runOnceBtn = document.getElementById('run_once');
  if (runOnceBtn) runOnceBtn.onclick = runOnce;
  
  const macroSelect = document.getElementById('macro_select');
  if (macroSelect) macroSelect.onchange = (e) => loadMacro(e.target.value);
  
  const editMacroBtn = document.getElementById('edit_macro');
  if (editMacroBtn) editMacroBtn.onclick = editMacro;
  
  const newMacroBtn = document.getElementById('new_macro');
  if (newMacroBtn) newMacroBtn.onclick = newMacro;
  
  const saveMacroBtn = document.getElementById('save_macro');
  if (saveMacroBtn) saveMacroBtn.onclick = saveMacro;
  
  // Modal controls
  const modalClose = document.getElementById('modal-close');
  if (modalClose) modalClose.onclick = hideModal;
  
  const cancelEdit = document.getElementById('cancel_edit');
  if (cancelEdit) cancelEdit.onclick = hideModal;
  
  // Settings modal controls
  const settingsToggle = document.getElementById('settings-toggle');
  if (settingsToggle) settingsToggle.onclick = showSettings;
  
  const settingsClose = document.getElementById('settings-close');
  if (settingsClose) settingsClose.onclick = hideSettings;
  
  const settingsSave = document.getElementById('settings_save');
  if (settingsSave) settingsSave.onclick = hideSettings;
  
  const settingsModal = document.getElementById('settings-modal');
  if (settingsModal) {
    settingsModal.onclick = (e) => {
      if (e.target.id === 'settings-modal') hideSettings();
    };
  }

  // Adapter controls
  const setAdapterBtn = document.getElementById('set_adapter');
  if (setAdapterBtn) setAdapterBtn.onclick = setAdapter;
  
  const testAdaptersBtn = document.getElementById('test_adapters');
  if (testAdaptersBtn) testAdaptersBtn.onclick = testAdapters;

  // Metrics controls
  const resetMetricsBtn = document.getElementById('reset_metrics');
  if (resetMetricsBtn) resetMetricsBtn.onclick = resetMetrics;

  // Alert controls
  const setAlertsBtn = document.getElementById('set_alerts');
  if (setAlertsBtn) setAlertsBtn.onclick = setAlerts;
  
  const enableNotifications = document.getElementById('enable_notifications');
  if (enableNotifications) {
    enableNotifications.onchange = function() {
      if (this.checked) {
        requestNotificationPermission();
      }
    };
  }
  
  // Alert interval input listeners to prevent automatic updates while user is editing
  const alertIntervalInput = document.getElementById('alert_interval');
  if (alertIntervalInput) {
    alertIntervalInput.oninput = function() {
      alertIntervalUserModified = true;
    };
    alertIntervalInput.onfocus = function() {
      alertIntervalUserModified = true;
    };
  }

  // Log controls
  const clearLogBtn = document.getElementById('clear-log');
  if (clearLogBtn) clearLogBtn.onclick = clearLog;

  // Keyboard shortcuts
  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
      e.preventDefault();
      saveMacro();
    }
    if (e.key === 'Escape') {
      hideModal();
    }
  });
}

// ============================================================================
// Application Initialization
// ============================================================================

/**
 * Initialize the entire application.
 */
async function initialize() {
  addLogMessage('Initializing PKMN Autoshine...', 'info');
  
  initializeEditor();
  setupEventListeners();
  connectWebSocket();
  
  // Load initial data
  await Promise.all([
    listMacros(),
    updateAdapterStatus()
  ]);
  
  // Set up periodic updates
  setInterval(updateMacroDetails, 1000);
  setInterval(updateAdapterStatus, 30000);
  
  addLogMessage('Application initialized successfully!', 'success');
}

// Start the application when page loads
document.addEventListener('DOMContentLoaded', initialize);