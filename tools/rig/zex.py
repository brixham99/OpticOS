#!/usr/bin/env python3
"""Run zexdoc/zexall (Frank Cringle's Z80 exercisers, GPL) on the rig core.
The .com files are fetched into tests/cache/ (gitignored), not committed."""
import ctypes, os, sys, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))
URL = 'https://raw.githubusercontent.com/anotherlin/z80emu/master/testfiles/%s.com'
name = sys.argv[1] if len(sys.argv) > 1 else 'zexdoc'
path = os.path.join(HERE, 'tests/cache/%s.com' % name)
if not os.path.exists(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    urllib.request.urlretrieve(URL % name, path)
lib = ctypes.CDLL(os.path.join(HERE, 'libz80.so'))
lib.z_mem.restype = ctypes.POINTER(ctypes.c_uint8)
lib.z_init()
m = lib.z_mem(); d = open(path, 'rb').read()
ctypes.memmove(ctypes.addressof(m.contents) + 0x100, d, len(d))
lib.z_cpm_run(ctypes.c_longlong(20_000_000_000))
