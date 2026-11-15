# OpticOS firmware for the ClockworkPi PicoCalc with a Raspberry Pi Pico 2.
# Build: make picocalc (in the Docker image, tools/docker), which runs
#   cmake -S picocalc -B build/fw -DOPTICOS_ROM=build/opticos_pc.rom
# and gives build/fw/opticos.uf2.
cmake_minimum_required(VERSION 3.13)
set(PICO_BOARD pico2 CACHE STRING "")
include($ENV{PICO_SDK_PATH}/external/pico_sdk_import.cmake)
project(opticos C CXX ASM)
set(CMAKE_C_STANDARD 11)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()
pico_sdk_init()

if(NOT OPTICOS_ROM)
  set(OPTICOS_ROM ${CMAKE_CURRENT_SOURCE_DIR}/../build/opticos_pc.rom)
endif()
get_filename_component(OPTICOS_ROM ${OPTICOS_ROM} ABSOLUTE)

# the ROM image as a C array
add_custom_command(
  OUTPUT ${CMAKE_CURRENT_BINARY_DIR}/rom.c
  COMMAND ${CMAKE_COMMAND} -DIN=${OPTICOS_ROM} -DOUT=${CMAKE_CURRENT_BINARY_DIR}/rom.c
          -P ${CMAKE_CURRENT_SOURCE_DIR}/embed.cmake
  DEPENDS ${OPTICOS_ROM} ${CMAKE_CURRENT_SOURCE_DIR}/embed.cmake)

# SD card and FatFs: carlk3's no-OS-FatFS-SD-SDIO-SPI-RPi-Pico v3.6.2 (in the
# Docker image at $FATFS_SD_PATH)
if(NOT FATFS_SD_PATH)
  set(FATFS_SD_PATH $ENV{FATFS_SD_PATH})
endif()
add_subdirectory(${FATFS_SD_PATH}/src fatfs)

add_executable(opticos main.c lcd.c kbd.c storage_sd.c hw_config.c ../emu/picocalc.c ${CMAKE_CURRENT_BINARY_DIR}/rom.c)
target_include_directories(opticos PRIVATE ${CMAKE_CURRENT_SOURCE_DIR} ../emu)
target_compile_options(opticos PRIVATE -O2 -Wall -Wno-unused-function)
target_link_libraries(opticos pico_stdlib pico_multicore hardware_spi hardware_i2c no-OS-FatFS-SD-SDIO-SPI-RPi-Pico)
# run from RAM: the Z80 core's big dispatch loop is too slow from XIP flash
pico_set_binary_type(opticos copy_to_ram)
# serial output: in the PicoCalc only the USB-C port (wired to UART0, GP0/GP1,
# 115200) carries a serial console; the Pico's own USB does not show up
pico_enable_stdio_usb(opticos 0)
pico_enable_stdio_uart(opticos 1)
pico_add_extra_outputs(opticos)

# lcdtest.uf2: LCD and keyboard-controller bring-up only (no emulator, one
# core): the screen cycles red, green, blue, white once a second and
# the keyboard backlight toggles with it
add_executable(lcdtest lcdtest.c lcd.c)
target_compile_options(lcdtest PRIVATE -O2 -Wall)
target_link_libraries(lcdtest pico_stdlib hardware_spi hardware_i2c)
pico_enable_stdio_usb(lcdtest 0)
pico_enable_stdio_uart(lcdtest 1)
pico_add_extra_outputs(lcdtest)

