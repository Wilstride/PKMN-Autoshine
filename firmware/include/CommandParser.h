#ifndef CommandParser_h
#define CommandParser_h

#include "SwitchBluetooth.h"

class CommandParser {
public:
    CommandParser(SwitchBluetooth* switch_controller);
    
    // Parse and execute a command line
    bool parse_and_execute(const char* command_line);
    
private:
    SwitchBluetooth* _switch;
    
    // Command parsing helpers
    bool parse_press_command(const char* args);
    bool parse_stick_command(const char* args);
    bool parse_sleep_command(const char* args);
    bool parse_release_command(const char* args);
    
    // Utility functions
    void skip_whitespace(const char*& ptr);
    bool parse_float(const char*& ptr, float& value);
    bool parse_button_name(const char*& ptr, char* button_name, size_t max_len);
};

#endif