cmake_minimum_required(VERSION 3.25.1)

add_executable(${PROJECT_NAME}
    main.cpp
    SwitchBluetooth.cpp
    CommandParser.cpp
)

target_include_directories(autoshine_pico_firmware PRIVATE ${CMAKE_CURRENT_LIST_DIR}/../include)

# Pull in pico libraries that we need
target_link_libraries(autoshine_pico_firmware
    pico_stdlib
    pico_cyw43_arch_lwip_threadsafe_background
    pico_btstack_ble
    pico_btstack_classic
    pico_btstack_cyw43
    pico_rand
    hardware_gpio
    hardware_spi
    hardware_i2c
)

# Enable USB output, disable UART output
pico_enable_stdio_usb(autoshine_pico_firmware 1)
pico_enable_stdio_uart(autoshine_pico_firmware 0)

# Create map/bin/hex/uf2 file in addition to ELF
pico_add_extra_outputs(autoshine_pico_firmware)