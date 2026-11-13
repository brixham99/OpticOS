# OpticOS build.  `make` assembles build/opticos.rom (16,384 bytes) and
# checks the layout.  `make check` runs the headless rig tests; pass
# REF=/path/to/48.rom for the black-box reference comparisons and the
# clean-room similarity gate (the reference ROM is never committed).
PASMO ?= pasmo
SRC := $(wildcard src/*.asm src/*.inc) font/font4x8.bin

build/opticos.rom: $(SRC)
	@mkdir -p build
	cd src && $(PASMO) --bin opticos.asm ../build/opticos.rom ../build/opticos.sym
	python3 tools/check_layout.py build/opticos.sym build/opticos.rom --md build/bytes.md

rig:
	gcc -O2 -shared -fPIC -o tools/rig/libz80.so tools/rig/z80.c

zex: rig
	python3 tools/rig/zex.py zexdoc
	python3 tools/rig/zex.py zexall

check: build/opticos.rom rig
ifdef REF
	python3 tools/similarity_check.py build/opticos.rom $(REF)
	python3 tools/rig/test_phase1.py --ref $(REF)
else
	python3 tools/rig/test_phase1.py
endif

fuse: build/opticos.rom
	python3 tools/fuse_phase1.py build/opticos.rom build/fuse /workspace/spectrum-ball/bounceball.tap

clean:
	rm -rf build tools/rig/libz80.so

.PHONY: rig zex check fuse clean
