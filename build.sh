#!/bin/sh
# Assemble OpticOS without make: ./build.sh  ->  build/opticos.rom (Spectrum)
# and build/opticos_pc.rom (PicoCalc)
set -e
cd "$(dirname "$0")"
mkdir -p build
(cd src && ${PASMO:-pasmo} --equ PICOCALC=0 --bin opticos.asm ../build/opticos.rom ../build/opticos.sym)
python3 tools/check_layout.py build/opticos.sym build/opticos.rom --md build/bytes.md
(cd src && ${PASMO:-pasmo} --equ PICOCALC=1 --bin opticos.asm ../build/opticos_pc.rom ../build/opticos_pc.sym)
python3 tools/check_layout.py build/opticos_pc.sym build/opticos_pc.rom --md build/bytes_pc.md
