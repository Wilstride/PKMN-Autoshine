#include "CommandParser.h"
#include <cstring>
#include <cstdlib>
#include <cctype>
#include <cstdio>
#include "pico/stdlib.h"

CommandParser::CommandParser(SwitchBluetooth* switch_controller) : _switch(switch_controller) {}

bool CommandParser::parse_and_execute(const char* command_line) {
    // Skip leading whitespace
    const char* ptr = command_line;
    skip_whitespace(ptr);
    
    if (*ptr == '\0' || *ptr == '#') {
        return true; // Empty line or comment
    }
    
    // Extract command
    char command[32];
    int i = 0;
    while (*ptr && !isspace(*ptr) && i < sizeof(command) - 1) {
        command[i++] = toupper(*ptr++);
    }
    command[i] = '\0';
    
    // Skip whitespace between command and args
    skip_whitespace(ptr);
    
    // Execute command
    if (strcmp(command, "PRESS") == 0) {
        return parse_press_command(ptr);
    } else if (strcmp(command, "RELEASE") == 0) {
        return parse_release_command(ptr);
    } else if (strcmp(command, "STICK") == 0) {
        return parse_stick_command(ptr);
    } else if (strcmp(command, "SLEEP") == 0) {
        return parse_sleep_command(ptr);
    } else if (strcmp(command, "CENTER_STICKS") == 0) {
        _switch->center_sticks();
        return true;
    } else if (strcmp(command, "RELEASE_ALL") == 0) {
        _switch->release_all_buttons();
        return true;
    } else {
        printf("Unknown command: %s\n", command);
        return false;
    }
}

bool CommandParser::parse_press_command(const char* args) {
    char button_name[32];
    if (!parse_button_name(args, button_name, sizeof(button_name))) {
        printf("Invalid button name for PRESS command\n");
        return false;
    }
    
    _switch->press_button(button_name);
    return true;
}

bool CommandParser::parse_release_command(const char* args) {
    char button_name[32];
    if (!parse_button_name(args, button_name, sizeof(button_name))) {
        printf("Invalid button name for RELEASE command\n");
        return false;
    }
    
    _switch->release_button(button_name);
    return true;
}

bool CommandParser::parse_stick_command(const char* args) {
    const char* ptr = args;
    skip_whitespace(ptr);
    
    // Parse stick name
    char stick_name[32];
    if (!parse_button_name(ptr, stick_name, sizeof(stick_name))) {
        printf("Invalid stick name for STICK command\n");
        return false;
    }
    
    // Parse horizontal value
    float h, v;
    if (!parse_float(ptr, h)) {
        printf("Invalid horizontal value for STICK command\n");
        return false;
    }
    
    // Parse vertical value
    if (!parse_float(ptr, v)) {
        printf("Invalid vertical value for STICK command\n");
        return false;
    }
    
    _switch->set_stick(stick_name, h, v);
    return true;
}

bool CommandParser::parse_sleep_command(const char* args) {
    const char* ptr = args;
    skip_whitespace(ptr);
    
    float duration;
    if (!parse_float(ptr, duration)) {
        printf("Invalid duration for SLEEP command\n");
        return false;
    }
    
    // Convert to milliseconds and sleep
    uint32_t sleep_duration_ms = (uint32_t)(duration * 1000);
    sleep_ms(sleep_duration_ms);
    return true;
}

void CommandParser::skip_whitespace(const char*& ptr) {
    while (*ptr && isspace(*ptr)) {
        ptr++;
    }
}

bool CommandParser::parse_float(const char*& ptr, float& value) {
    skip_whitespace(ptr);
    
    char* end_ptr;
    value = strtof(ptr, &end_ptr);
    
    if (ptr == end_ptr) {
        return false; // No digits found
    }
    
    ptr = end_ptr;
    return true;
}

bool CommandParser::parse_button_name(const char*& ptr, char* button_name, size_t max_len) {
    skip_whitespace(ptr);
    
    size_t i = 0;
    while (*ptr && !isspace(*ptr) && i < max_len - 1) {
        button_name[i++] = tolower(*ptr++);
    }
    button_name[i] = '\0';
    
    return i > 0;
}