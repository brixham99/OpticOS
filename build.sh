#!/bin/sh
# Assemble OpticOS without make: ./build.sh  ->  build/opticos.rom
set -e
cd "$(dirname "$0")"
mkdir -p build
(cd src && ${PASMO:-pasmo} --bin opticos.asm ../build/opticos.rom ../build/opticos.sym)
python3 tools/check_layout.py build/opticos.sym build/opticos.rom --md build/bytes.md
