"""Pico device communication module."""
from __future__ import annotations

import re
import time
import serial
from typing import Optional


def flatten_press_commands(macro_content: str) -> str:
    """
    Flatten PRESS commands to HOLD + RELEASE.
    
    PRESS <button> becomes:
    - HOLD <button>
    - RELEASE <button>
    """
    lines = []
    
    for line in macro_content.split('\n'):
        stripped = line.strip()
        
        # Check if it's a PRESS command (case-insensitive)
        press_match = re.match(r'PRESS\s+(\w+)', stripped, re.IGNORECASE)
        
        if press_match:
            button = press_match.group(1)
            
            # Expand to HOLD + RELEASE (no SLEEP)
            lines.append(f'HOLD {button}')
            lines.append(f'RELEASE {button}')
        else:
            # Keep line as-is
            lines.append(line)
    
    return '\n'.join(lines)


def convert_sleep_to_frames(macro_content: str) -> str:
    """
    Convert SLEEP commands from seconds to frames.
    
    - If value is a float (e.g., 0.05, 10.0): multiply by 125 to convert seconds to frames (125 Hz)
    - If value is an integer (e.g., 1, 10): keep as-is (already in frames)
    
    SLEEP <value> becomes SLEEP <frames>
    """
    lines = []
    
    for line in macro_content.split('\n'):
        stripped = line.strip()
        
        # Check if it's a SLEEP command (case-insensitive)
        sleep_match = re.match(r'(SLEEP)\s+([\d.]+)', stripped, re.IGNORECASE)
        
        if sleep_match:
            command = sleep_match.group(1)
            value_str = sleep_match.group(2)
            
            # Check if it's a float (contains decimal point)
            if '.' in value_str:
                # Convert seconds to frames (multiply by 125 for 125 Hz)
                seconds = float(value_str)
                frames = int(seconds * 125)
                lines.append(f'{command} {frames}')
            else:
                # Already in frames, keep as-is
                lines.append(line)
        else:
            # Keep line as-is
            lines.append(line)
    
    return '\n'.join(lines)


class PicoDevice:
    """Represents a single Pico device connection."""
    
    def __init__(self, port: str, name: str = None):
        self.port = port
        self.name = name or port.split('/')[-1]  # e.g., "ttyACM0"
        self.serial: Optional[serial.Serial] = None
        self.connected = False
        self.current_macro: Optional[str] = None
        self.is_uploading = False  # Track if macro is being uploaded
        self.iteration_count = 0  # Track macro iteration count
    
    def connect(self) -> bool:
        """Connect to this Pico device."""
        if self.connected:
            return True
        try:
            self.serial = serial.Serial(self.port, 115200, timeout=1.0)
            time.sleep(0.5)  # Give device time to initialize
            
            # Clear any startup messages
            if self.serial.in_waiting:
                self.serial.reset_input_buffer()
            
            self.connected = True
            return True
        except Exception as e:
            print(f"Failed to connect to {self.port}: {e}")
            return False
    
    def disconnect(self) -> None:
        """Disconnect from this Pico device."""
        if self.serial:
            try:
                self.serial.close()
            except:
                pass
            self.connected = False
    
    def send_command(self, cmd: str, allow_during_upload: bool = False) -> bool:
        """Send command to this Pico.
        
        Args:
            cmd: Command to send
            allow_during_upload: If True, allow command even during macro upload
        """
        if not self.connected or not self.serial:
            print(f"Cannot send command to {self.port}: not connected")
            return False
        
        # Block commands during macro upload (unless explicitly allowed)
        if self.is_uploading and not allow_during_upload:
            print(f"[{self.name}] Command blocked: macro upload in progress")
            return False
        
        try:
            command_bytes = (cmd + '\n').encode('utf-8')
            self.serial.write(command_bytes)
            self.serial.flush()
            
            # Read immediate response for debugging
            time.sleep(0.05)
            if self.serial.in_waiting:
                response = self.serial.readline().decode('utf-8', errors='ignore').strip()
                if response:
                    print(f"[{self.name}] Response: {response}")
                    self._process_response(response)
            
            return True
        except Exception as e:
            print(f"Error sending command to {self.port}: {e}")
            self.connected = False
            return False
    
    def send_macro(self, macro_content: str) -> bool:
        """Upload macro to this Pico firmware using proper protocol."""
        if not self.connected:
            print(f"Cannot upload macro to {self.port}: not connected")
            return False
        
        # Set upload flag to block other commands
        self.is_uploading = True
        
        try:
            print(f"\n[{self.name}] Starting macro upload...")
            
            # Process macro content:
            # 1. Flatten PRESS commands to HOLD + RELEASE
            processed_content = flatten_press_commands(macro_content)
            
            # 2. Convert SLEEP from seconds to frames (if float)
            processed_content = convert_sleep_to_frames(processed_content)
            
            # 3. Stop any running macro first (allow during upload)
            self.send_command("STOP_MACRO", allow_during_upload=True)
            time.sleep(0.1)
            
            # 4. Start macro loading sequence (allow during upload)
            self.send_command("LOAD_MACRO_START", allow_during_upload=True)
            time.sleep(0.05)
            
            # 5. Send macro content line by line (allow during upload)
            lines_sent = 0
            for line in processed_content.split('\n'):
                line = line.strip()
                if line:  # Send all non-empty lines (firmware filters comments)
                    self.send_command(line, allow_during_upload=True)
                    lines_sent += 1
            
            print(f"[{self.name}] Sent {lines_sent} lines")
            time.sleep(0.05)
            
            # 6. Complete the macro loading (allow during upload)
            self.send_command("LOAD_MACRO_END", allow_during_upload=True)
            time.sleep(0.2)  # Give firmware time to process
            
            # 7. Read all responses to check for success
            responses = []
            while self.serial.in_waiting:
                line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    print(f"[{self.name}] {line}")
                    responses.append(line)
            
            # Check for success message
            success = any('successfully' in r.lower() or 'loaded' in r.lower() 
                         for r in responses)
            
            if success:
                print(f"[{self.name}] Macro uploaded successfully!")
            else:
                print(f"[{self.name}] Warning: No success confirmation received")
            
            # Clear upload flag
            self.is_uploading = False
            
            return True  # Return True even without confirmation (firmware may not always respond)
            
        except Exception as e:
            print(f"Error sending macro to {self.port}: {e}")
            import traceback
            traceback.print_exc()
            # Clear upload flag on error
            self.is_uploading = False
            return False
    
    def read_response(self, timeout: float = 0.5) -> list:
        """Read all available responses from the device."""
        if not self.connected or not self.serial:
            return []
        
        responses = []
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.serial.in_waiting:
                try:
                    line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                    if line:
                        responses.append(line)
                except:
                    break
            else:
                time.sleep(0.01)
        
        return responses
    
    def poll_serial_buffer(self) -> None:
        """Poll and empty the serial buffer, processing any responses."""
        if not self.connected or not self.serial:
            return
        
        try:
            # Read all available data from the buffer
            while self.serial.in_waiting:
                line = self.serial.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    # Process the line for important information
                    self._process_response(line)
        except Exception as e:
            # Silent fail - don't spam errors during polling
            pass
    
    def _process_response(self, response: str) -> None:
        """Process a response line from the firmware."""
        # Track iteration count from firmware responses
        if 'ITERATION_COMPLETE:' in response:
            try:
                self.iteration_count = int(response.split(':')[1])
                print(f"[{self.name}] Iteration: {self.iteration_count}")
            except:
                pass
        
        # Log other important responses
        if any(keyword in response for keyword in ['successfully', 'failed', 'error', 'loaded']):
            print(f"[{self.name}] {response}")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'port': self.port,
            'name': self.name,
            'connected': self.connected,
            'current_macro': self.current_macro,
            'is_uploading': self.is_uploading,
            'iteration_count': self.iteration_count
        }
