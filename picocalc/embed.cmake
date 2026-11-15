# cmake -DIN=<rom> -DOUT=<rom.c> -P embed.cmake: the ROM as opticos_rom[16384]
file(READ ${IN} hex HEX)
string(LENGTH "${hex}" n)
if(NOT n EQUAL 32768)
  message(FATAL_ERROR "${IN}: expected a 16K ROM")
endif()
string(REGEX REPLACE "([0-9a-f][0-9a-f])" "0x\\1," arr "${hex}")
file(WRITE ${OUT} "const unsigned char opticos_rom[16384] = {${arr}};\n")
