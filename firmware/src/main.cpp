#include <stdio.h>
#include <string.h>

#include "SwitchBluetooth.h"
#include "CommandParser.h"
#include "pico/stdlib.h"
#include "btstack.h"

SwitchBluetooth *switchController = nullptr;
CommandParser *commandParser = nullptr;

static btstack_packet_callback_registration_t hci_event_callback_registration;
static btstack_timer_source_t serial_timer;

static void packet_handler_wrapper(uint8_t packet_type, uint16_t channel,
                                   uint8_t *packet, uint16_t packet_size) {
  packet_handler(switchController, packet_type, packet);
}

static void hid_report_data_callback_wrapper(uint16_t cid,
                                             hid_report_type_t report_type,
                                             uint16_t report_id,
                                             int report_size, uint8_t *report) {
  // USB report callback includes 2 bytes excluded here, prepending 2 bytes to
  // keep alignment
  hid_report_data_callback(switchController, report_id, report - 1,
                           report_size + 1);
}

void process_serial_commands() {
    static char line_buffer[256];
    static int buffer_pos = 0;
    
    int c = getchar_timeout_us(0); // Non-blocking read
    if (c == PICO_ERROR_TIMEOUT) {
        return; // No data available
    }
    
    if (c == '\n' || c == '\r') {
        if (buffer_pos > 0) {
            line_buffer[buffer_pos] = '\0';
            
            printf("Executing command: %s\n", line_buffer);
            
            if (!commandParser->parse_and_execute(line_buffer)) {
                printf("Command failed: %s\n", line_buffer);
            } else {
                printf("OK\n");
            }
            
            buffer_pos = 0;
        }
    } else if (buffer_pos < sizeof(line_buffer) - 1) {
        line_buffer[buffer_pos++] = c;
    } else {
        // Buffer overflow - reset
        printf("Command too long, resetting buffer\n");
        buffer_pos = 0;
    }
}

static void serial_timer_handler(btstack_timer_source_t *ts) {
    // Process serial commands
    process_serial_commands();
    
    // Reschedule timer for next check (every 1ms)
    btstack_run_loop_set_timer(ts, 1);
    btstack_run_loop_add_timer(ts);
}

int main() {
  // Initialize stdio USB for serial communication
  stdio_init_all();
  
  // Give USB some time to initialize properly
  sleep_ms(1000);
  
  printf("Autoshine Pico Firmware Starting...\n");
  
  // Give another moment for USB to stabilize
  sleep_ms(500);
  
  // Initialize Switch controller
  switchController = new SwitchBluetooth();
  commandParser = new CommandParser(switchController);
  
  switchController->init();
  
  printf("Bluetooth controller initialized\n");
  
  hci_event_callback_registration.callback = &packet_handler_wrapper;
  hci_add_event_handler(&hci_event_callback_registration);

  hid_device_register_packet_handler(&packet_handler_wrapper);
  hid_device_register_report_data_callback(&hid_report_data_callback_wrapper);

  // Set up periodic timer for serial command processing
  serial_timer.process = &serial_timer_handler;
  btstack_run_loop_set_timer(&serial_timer, 1);  // 1ms interval
  btstack_run_loop_add_timer(&serial_timer);

  // turn on!
  hci_power_control(HCI_POWER_ON);
  
  printf("Bluetooth stack started. Waiting for commands over USB serial...\n");
  printf("Available commands:\n");
  printf("  PRESS <button>      - Press a button (a, b, x, y, l, r, zl, zr, plus, minus, home, capture, l_stick, r_stick, dpad_up, dpad_down, dpad_left, dpad_right)\n");
  printf("  RELEASE <button>    - Release a button\n");
  printf("  STICK <stick> <h> <v> - Set stick position (-1.0 to 1.0)\n");
  printf("  SLEEP <seconds>     - Sleep for specified duration\n");
  printf("  CENTER_STICKS       - Center both analog sticks\n");
  printf("  RELEASE_ALL         - Release all buttons\n");
  printf("  # comment           - Comment line (ignored)\n");
  printf("\nReady for commands...\n");

  // Enter BTStack main event loop (this blocks)
  btstack_run_loop_execute();

  return 0;
}