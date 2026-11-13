#!/usr/bin/env python3
"""Clean-room gate (spec 1.3): fail if opticos.rom shares any run of 12 or
more identical bytes with a reference ROM, anywhere in either image.  The
font area ($3E80-$3FFF) and runs made of a single repeated byte (filler)
are excluded.  Only offsets are printed, never reference bytes.
Usage: similarity_check.py build/opticos.rom path/to/48.rom"""
import sys
N = 12
ours = open(sys.argv[1], 'rb').read()
ref = open(sys.argv[2], 'rb').read()
seen = {}
for i in range(len(ref) - N + 1):
    seen.setdefault(ref[i:i + N], i)
hits = []
for i in range(0, 0x3E80 - N + 1):
    w = ours[i:i + N]
    if len(set(w)) == 1: continue
    if w in seen: hits.append((i, seen[w]))
if hits:
    print('FAIL: %d shared %d-byte windows, first at OpticOS $%04X' % (len(hits), N, hits[0][0]))
    sys.exit(1)
print('similarity: OK (no shared run of %d+ bytes outside the font and filler)' % N)
