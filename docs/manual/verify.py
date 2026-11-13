#!/usr/bin/env python3
"""Run each example in docs/manual/examples in the rig and print the screen text."""
import os, sys, glob
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools', 'rig'))
from p3lib import Basic
b = Basic()
for f in sorted(glob.glob(os.path.join(HERE, 'examples', '*.bas'))):
    prog = [l.strip() for l in open(f) if l.strip()]
    print('=====', os.path.basename(f))
    for r in b.run(prog, limit=3_000_000_000): print('|' + r)
    b.line('LIST'); print('--- LIST'); [print('|' + r) for r in b.screen() if r]
