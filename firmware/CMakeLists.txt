cmake_minimum_required(VERSION 3.25.1)

# Set board before importing SDK
set(PICO_BOARD pico_w)

include($ENV{PICO_SDK_PATH}/external/pico_sdk_import.cmake)
include($ENV{PICO_SDK_PATH}/tools/CMakeLists.txt)
set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(PICO_CXX_ENABLE_EXCEPTIONS 1)

project(autoshine_pico_firmware C CXX ASM)

pico_sdk_init()
add_subdirectory(src)