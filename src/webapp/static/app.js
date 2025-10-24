/**
 * PKMN Autoshine - Main Application JavaScript
 * 
 * This module provides the complete frontend functionality for the macro automation
 * control interface. It handles WebSocket communication, macro management, editor
 * initialization, and user interface interactions.
 * 
 * Key Features:
 * - Real-time WebSocket communication with backend
 * - Advanced code editor with syntax highlighting (CodeMirror)
 * - Mobile-responsive design with fallback editor
 * - Macro file management (create, edit, save, run)
 * - Live status monitoring and metrics tracking
 * - Adapter management and connectivity testing
 * - Alert system with notifications and sound
 * - Comprehensive logging with spam filtering
 */

// ============================================================================
// Global Variables and State Management
// ============================================================================

let editor;
let ws;
let wsReconnectInterval;
let currentMacroName = '';
let alertIntervalUserModified = false;

// Log management with spam filtering
let logEntries = [];
let lastLogMessage = '';
let logRepeatCount = 0;
const MAX_LOG_ENTRIES = 20;
const SPAM_MESSAGES = [
  'Could not find Pico W device',
  'No module named \'joycontrol\'',
  'Could not connect to any adapter',
  'Attempting to reconnect',
  'WebSocket disconnected'
];

// ============================================================================
// Device Detection and Editor Utilities
// ============================================================================

/**
 * Detect if the current device is a mobile device.
 * @returns {boolean} True if mobile device detected
 */
function isMobileDevice() {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
         ('ontouchstart' in window) ||
         (navigator.maxTouchPoints && navigator.maxTouchPoints > 0);
}

/**
 * Check if the fallback editor should be used instead of CodeMirror.
 * @returns {boolean} True if fallback editor should be used
 */
function shouldUseFallback() {
  // Check for problematic mobile browsers or user preference
  const userAgent = navigator.userAgent.toLowerCase();
  const isProblematicBrowser = userAgent.includes('chrome') && userAgent.includes('mobile');
  
  // Check localStorage for user preference
  const preferFallback = localStorage.getItem('useFallbackEditor') === 'true';
  
  return preferFallback || isProblematicBrowser;
}

// ============================================================================
// Editor Initialization and Mobile Support
// ============================================================================

/**
 * Initialize fallback editor for mobile devices with limited CodeMirror support.
 */
function initializeFallbackEditor() {
  const wrapper = document.getElementById('editor-wrapper');
  const fallbackEditor = document.getElementById('mobile-fallback-editor');
  
  wrapper.classList.add('use-fallback');
  
  // Add helpful placeholder for mobile users
  fallbackEditor.placeholder = `Enter your macro commands here...

Available commands:
PRESS <button>     - Press a button (a, b, x, y, l, r, zl, zr, plus, minus, home, capture)
STICK <stick> <x> <y> - Move analog stick (l or r, coordinates -1.0 to 1.0)
SLEEP <seconds>    - Wait for specified time

Example:
PRESS a
SLEEP 0.5
STICK l 0.0 1.0
SLEEP 0.1`;

  // Set up fallback editor as the main editor interface
  editor = {
    getValue: function() {
      return fallbackEditor.value;
    },
    setValue: function(value) {
      fallbackEditor.value = value;
    },
    getWrapperElement: function() {
      return fallbackEditor;
    },
    refresh: function() {
      // No-op for regular textarea
    },
    focus: function() {
      fallbackEditor.focus();
    }
  };

  // Add a button to switch back to CodeMirror if desired
  const switchButton = document.createElement('button');
  switchButton.textContent = '🔄 Try Advanced Editor';
  switchButton.style.cssText = `
    position: absolute;
    top: 5px;
    right: 5px;
    background: var(--accent-primary);
    color: white;
    border: none;
    padding: 5px 10px;
    border-radius: 4px;
    font-size: 12px;
    cursor: pointer;
    z-index: 1000;
  `;
  
  wrapper.style.position = 'relative';
  wrapper.appendChild(switchButton);
  
  switchButton.onclick = function() {
    localStorage.setItem('useFallbackEditor', 'false');
    location.reload();
  };

  addLogMessage('📱 Using mobile-optimized editor', 'info');
}

/**
 * Initialize CodeMirror editor with custom syntax highlighting and mobile support.
 */
function initializeEditor() {
  // Check if we should use the mobile fallback
  if (isMobileDevice() && shouldUseFallback()) {
    initializeFallbackEditor();
    return;
  }

  // Define custom mode for macro syntax
  CodeMirror.defineMode("macro", function() {
    return {
      token: function(stream, state) {
        // Comments
        if (stream.match(/^#.*/)) {
          return "comment";
        }
        
        // Commands
        if (stream.match(/^(PRESS|STICK|SLEEP)\b/)) {
          return "keyword";
        }
        
        // Button names
        if (stream.match(/\\b(a|b|x|y|l|r|zl|zr|plus|minus|home|capture|ls|rs)\\b/)) {
          return "atom";
        }
        
        // Numbers (coordinates, time values)
        if (stream.match(/[-+]?\\d*\\.?\\d+/)) {
          return "number";
        }
        
        // Strings
        if (stream.match(/^"([^"\\\\]|\\\\.)*"/)) {
          return "string";
        }
        
        stream.next();
        return null;
      }
    };
  });

  // Use different input methods for mobile vs desktop
  const isMobile = isMobileDevice();
  const editorConfig = {
    mode: 'macro',
    theme: 'dracula',
    lineNumbers: true,
    indentUnit: 2,
    lineWrapping: true,
    autoCloseBrackets: true,
    matchBrackets: true,
    showCursorWhenSelecting: true,
    tabSize: 2,
    extraKeys: {
      "Ctrl-S": function() { saveMacro(); },
      "Cmd-S": function() { saveMacro(); }
    }
  };

  // Add mobile-specific configuration
  if (isMobile) {
    editorConfig.inputStyle = "textarea";  // Use textarea input for better mobile support
    editorConfig.spellcheck = false;
    editorConfig.autocorrect = false;
    editorConfig.autocapitalize = false;
    editorConfig.lineWiseCopyCut = false;
    editorConfig.undoDepth = 200;
  } else {
    editorConfig.inputStyle = "contenteditable";
    // Add desktop backspace handler
    editorConfig.extraKeys["Backspace"] = function(cm) {
      const cursor = cm.getCursor();
      if (cursor.ch === 0 && cursor.line > 0) {
        const prevLine = cm.getLine(cursor.line - 1);
        const prevLineEnd = prevLine.length;
        cm.replaceRange("", 
          {line: cursor.line - 1, ch: prevLineEnd}, 
          {line: cursor.line, ch: 0}
        );
      } else {
        return CodeMirror.Pass;
      }
    };
  }

  editor = CodeMirror.fromTextArea(document.getElementById('macro_editor'), editorConfig);

  // Setup mobile support function
  function setupMobileSupport(cm) {
    let lastContent = cm.getValue();
    let isHandlingInput = false;

    // Handle virtual keyboard changes on mobile
    cm.on('focus', function() {
      setTimeout(() => {
        if (window.visualViewport) {
          const handleViewportChange = () => {
            const editorElement = cm.getWrapperElement();
            const rect = editorElement.getBoundingClientRect();
            if (rect.bottom > window.visualViewport.height) {
              editorElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
          };
          window.visualViewport.addEventListener('resize', handleViewportChange);
        }
      }, 100);
    });

    // Monitor content changes for backspace detection
    cm.on('beforeChange', function(cm, changeObj) {
      if (isHandlingInput) return;
      
      const cursor = cm.getCursor();
      const currentContent = cm.getValue();
      
      // Check if this is a backspace operation at line beginning
      if (changeObj.origin === '+delete' && 
          changeObj.from.line > 0 && 
          changeObj.from.ch === 0 && 
          changeObj.to.ch === 0) {
        
        isHandlingInput = true;
        changeObj.cancel();
        
        // Manually handle line merging
        setTimeout(() => {
          const prevLine = cm.getLine(changeObj.from.line - 1);
          const currentLine = cm.getLine(changeObj.from.line);
          const prevLineEnd = prevLine.length;
          
          // Replace the newline with nothing, merging the lines
          cm.replaceRange(currentLine, 
            {line: changeObj.from.line - 1, ch: prevLineEnd}, 
            {line: changeObj.from.line + 1, ch: 0}
          );
          
          // Set cursor position at the merge point
          cm.setCursor({line: changeObj.from.line - 1, ch: prevLineEnd});
          
          isHandlingInput = false;
        }, 0);
      }
    });

    // Direct input monitoring as fallback
    const textarea = cm.getInputField();
    if (textarea) {
      textarea.addEventListener('input', function(e) {
        if (isHandlingInput) return;
        
        setTimeout(() => {
          const newContent = cm.getValue();
          const cursor = cm.getCursor();
          
          // Detect if lines were merged (content got shorter and we're at start of line)
          if (newContent.length < lastContent.length && cursor.ch === 0 && cursor.line > 0) {
            const lines = newContent.split('\\n');
            const lastLines = lastContent.split('\\n');
            
            // If we lost a line, it might be a backspace at line start
            if (lines.length < lastLines.length) {
              cm.refresh();
            }
          }
          
          lastContent = newContent;
        }, 0);
      });

      // Handle keydown events directly on the textarea
      textarea.addEventListener('keydown', function(e) {
        if (e.key === 'Backspace' || e.keyCode === 8) {
          const cursor = cm.getCursor();
          
          // If at the beginning of a line
          if (cursor.ch === 0 && cursor.line > 0) {
            e.preventDefault();
            isHandlingInput = true;
            
            const prevLine = cm.getLine(cursor.line - 1);
            const currentLine = cm.getLine(cursor.line);
            const prevLineEnd = prevLine.length;
            
            // Merge lines
            cm.replaceRange(prevLine + currentLine, 
              {line: cursor.line - 1, ch: 0}, 
              {line: cursor.line + 1, ch: 0}
            );
            
            // Position cursor at merge point
            cm.setCursor({line: cursor.line - 1, ch: prevLineEnd});
            
            setTimeout(() => {
              isHandlingInput = false;
              cm.refresh();
            }, 10);
          }
        }
      });
    }

    // Handle orientation changes
    window.addEventListener('orientationchange', () => {
      setTimeout(() => {
        cm.refresh();
      }, 200);
    });

    // Force periodic refresh on mobile
    setInterval(() => {
      if (document.activeElement === textarea) {
        cm.refresh();
      }
    }, 1000);
  }

  // Add custom CSS for macro syntax highlighting
  const style = document.createElement('style');
  style.textContent = `
    .cm-s-dracula .cm-keyword { color: #ff79c6; font-weight: bold; }
    .cm-s-dracula .cm-atom { color: #8be9fd; }
    .cm-s-dracula .cm-number { color: #bd93f9; }
    .cm-s-dracula .cm-comment { color: #6272a4; font-style: italic; }
  `;
  document.head.appendChild(style);

  // Add mobile-specific event handling
  if (isMobileDevice()) {
    setupMobileSupport(editor);
    
    // Additional fallback: mutation observer for content changes
    const wrapper = editor.getWrapperElement();
    const observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(mutation) {
        if (mutation.type === 'childList' || mutation.type === 'characterData') {
          // Force a refresh after DOM changes
          setTimeout(() => editor.refresh(), 10);
        }
      });
    });
    
    observer.observe(wrapper, {
      childList: true,
      subtree: true,
      characterData: true
    });

    // Detect persistent backspace issues and offer fallback
    let backspaceProblemCount = 0;
    const textarea = editor.getInputField();
    
    if (textarea) {
      textarea.addEventListener('keydown', function(e) {
        if (e.key === 'Backspace' && editor.getCursor().ch === 0 && editor.getCursor().line > 0) {
          backspaceProblemCount++;
          
          if (backspaceProblemCount >= 3) {
            setTimeout(() => {
              if (confirm('Having trouble with backspace? Switch to mobile-optimized editor?')) {
                localStorage.setItem('useFallbackEditor', 'true');
                location.reload();
              }
            }, 500);
          }
        }
      });
    }
  }
}

// ============================================================================
// WebSocket Communication
// ============================================================================

/**
 * Initialize WebSocket connection with automatic reconnection.
 */
function connectWebSocket() {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${wsProtocol}//${location.host}/ws`);
  
  const wsIndicator = document.getElementById('ws-indicator');
  const wsStatus = document.getElementById('ws-status');
  
  ws.onopen = () => {
    console.log('WebSocket connected');
    if (wsIndicator) wsIndicator.classList.add('connected');
    if (wsStatus) wsStatus.textContent = 'Connected';
    clearInterval(wsReconnectInterval);
    addLogMessage('🟢 Connected to server', 'success');
  };

  ws.onclose = () => {
    console.log('WebSocket disconnected');
    if (wsIndicator) wsIndicator.classList.remove('connected');
    if (wsStatus) wsStatus.textContent = 'Disconnected';
    addLogMessage('🔴 Disconnected from server', 'error');
    
    // Auto-reconnect
    wsReconnectInterval = setInterval(() => {
      addLogMessage('🔄 Attempting to reconnect...', 'info');
      connectWebSocket();
    }, 5000);
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    addLogMessage('❌ Connection error', 'error');
  };

  ws.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data);
      handleWebSocketMessage(msg);
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  };
}

/**
 * Handle incoming WebSocket messages.
 * @param {Object} msg - The parsed WebSocket message
 */
function handleWebSocketMessage(msg) {
  if (msg.type === 'log') {
    addLogMessage(msg.message || msg.msg, msg.level || 'info');
  } else if (msg.type === 'status') {
    updateStatus(msg);
  } else if (msg.type === 'alert') {
    showAlert(msg.iterations);
  }
}

// ============================================================================
// Status Management and Real-time Updates
// ============================================================================

/**
 * Update macro execution status from server.
 */
async function updateMacroDetails() {
  try {
    const res = await fetch('/api/status');
    if (!res.ok) return;
    
    const status = await res.json();
    
    // Update individual status fields
    const iterationElement = document.getElementById('iteration_count');
    const runtimeElement = document.getElementById('runtime_display');
    const timePerIterElement = document.getElementById('time_per_iteration');
    
    if (iterationElement) iterationElement.textContent = status.iterations || 0;
    if (runtimeElement) runtimeElement.textContent = status.runtime || '0:00';
    if (timePerIterElement) timePerIterElement.textContent = status.sec_per_iter ? status.sec_per_iter + 's' : '--';
    
    // Check for pending alert
    if (status.pending_alert && status.iterations > 0) {
      showAlert(status.iterations);
    }
    
    // Update alert interval UI if it changed (but don't overwrite if user has modified it)
    if (status.alert_interval !== undefined && !alertIntervalUserModified) {
      const alertInput = document.getElementById('alert_interval');
      // Only update if the input is not currently focused
      if (alertInput && document.activeElement !== alertInput) {
        alertInput.value = status.alert_interval;
      }
    }
  } catch (error) {
    console.error('Failed to update macro details:', error);
  }
}

/**
 * Update adapter connectivity status.
 */
async function updateAdapterStatus() {
  try {
    const res = await fetch('/api/adapters/status');
    if (!res.ok) return;
    
    const status = await res.json();
    const preferred = status.preferred || 'auto-detect';
    const connectivity = status.connectivity || {};
    
    const statusLines = [
      `🔌 Adapter: ${preferred}`,
      `${connectivity.pico ? '✅' : '❌'} Pico W: ${connectivity.pico ? 'Available' : 'Unavailable'}`,
      `${connectivity.joycontrol ? '✅' : '❌'} Joycontrol: ${connectivity.joycontrol ? 'Available' : 'Unavailable'}`
    ];
    
    const adapterStatusElement = document.getElementById('adapter_status');
    const adapterSelectElement = document.getElementById('adapter_select');
    
    if (adapterStatusElement) adapterStatusElement.textContent = statusLines.join('\\n');
    if (adapterSelectElement) adapterSelectElement.value = status.preferred || '';
    
    // Update status card styling
    const adapterCard = adapterStatusElement?.closest('.status-card');
    if (adapterCard) {
      if (connectivity.pico || connectivity.joycontrol) {
        adapterCard.classList.remove('error');
        adapterCard.classList.add('success');
      } else {
        adapterCard.classList.remove('success');
        adapterCard.classList.add('error');
      }
    }
  } catch (error) {
    console.error('Failed to update adapter status:', error);
  }
}

/**
 * Update status display from WebSocket or API data.
 * @param {Object|string} data - Status data or string message
 */
function updateStatus(data) {
  // Handle both old string format and new structured data
  if (typeof data === 'string') {
    const macroStatusElement = document.getElementById('macro_status');
    if (macroStatusElement) macroStatusElement.textContent = data;
    return;
  }
  
  // Update iteration counter, runtime and time per iteration in main display
  if (data.iterations !== undefined) {
    const element = document.getElementById('iteration_count');
    if (element) element.textContent = data.iterations;
  }
  if (data.runtime) {
    const element = document.getElementById('runtime_display');
    if (element) element.textContent = data.runtime;
  }
  if (data.sec_per_iter !== undefined) {
    const element = document.getElementById('time_per_iteration');
    if (element) element.textContent = data.sec_per_iter ? data.sec_per_iter + 's' : '--';
  }
  
  // Update console status with MAC address if available (in settings)
  const consoleStatusElement = document.getElementById('console_status');
  if (consoleStatusElement) {
    if (data.console_mac) {
      consoleStatusElement.textContent = `${data.console_type || 'Switch'} (${data.console_mac})`;
    } else if (data.adapter_name) {
      consoleStatusElement.textContent = data.adapter_name + ' - No console connected';
    } else {
      consoleStatusElement.textContent = 'No adapter connected';
    }
  }
  
  // Update macro status (in settings)
  if (data.status) {
    const macroStatusElement = document.getElementById('macro_status');
    if (macroStatusElement) macroStatusElement.textContent = data.status;
  }
  
  // Update adapter status in settings
  if (data.adapter_name) {
    const adapterStatusElement = document.getElementById('adapter_status');
    if (adapterStatusElement) adapterStatusElement.textContent = data.adapter_name;
  }
}

// ============================================================================
// Logging System with Spam Filtering
// ============================================================================

/**
 * Check if a log message should be filtered as spam.
 * @param {string} message - The log message to check
 * @returns {boolean} True if message is spam
 */
function isSpamMessage(message) {
  return SPAM_MESSAGES.some(spam => message.includes(spam));
}

/**
 * Add a log message to the display with spam filtering.
 * @param {string} message - The log message
 * @param {string} type - Message type ('info', 'success', 'warning', 'error')
 */
function addLogMessage(message, type = 'info') {
  // Filter out spam messages after first occurrence
  if (isSpamMessage(message)) {
    if (message === lastLogMessage) {
      logRepeatCount++;
      // Only show repeated spam messages every 10th occurrence
      if (logRepeatCount % 10 !== 0) {
        return;
      }
      message = `${message} (repeated ${logRepeatCount} times)`;
    } else {
      logRepeatCount = 1;
    }
  } else {
    logRepeatCount = 0;
  }
  
  lastLogMessage = message;
  
  const timestamp = new Date().toLocaleTimeString();
  const prefix = type === 'error' ? '❌' : type === 'success' ? '✅' : type === 'info' ? 'ℹ️' : type === 'warning' ? '⚠️' : '📝';
  const logEntry = `[${timestamp}] ${prefix} ${message}`;
  
  logEntries.push(logEntry);
  
  // Keep only the latest entries
  if (logEntries.length > MAX_LOG_ENTRIES) {
    logEntries = logEntries.slice(-MAX_LOG_ENTRIES);
  }
  
  // Update display
  const logContent = document.getElementById('log');
  if (logContent) {
    logContent.textContent = logEntries.join('\\n');
    logContent.scrollTop = logContent.scrollHeight;
  }
}

/**
 * Clear all log entries.
 */
function clearLog() {
  logEntries = [];
  const logContent = document.getElementById('log');
  if (logContent) logContent.textContent = '';
  addLogMessage('Log cleared');
}

// Continue in next part due to length...