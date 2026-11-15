#!/usr/bin/env python3
"""Spectrum software on the PicoCalc: the Spectrum screen mode (display
register DV_MODE) and the Kempston joystick.  A Sinclair game tape (BASIC
loader: BORDER, LOAD "" CODE, RANDOMIZE USR; machine code that draws on the
Spectrum screen at $4000) loads from the card through the legacy loader,
which shows the Spectrum screen; OpticOS's prompt shows its own display
again.  Runs on the PicoCalc ROM whatever OPTICOS_MACHINE says."""
import os, sys, shutil, tempfile
os.environ['OPTICOS_MACHINE'] = 'picocalc'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p3lib import Basic, SYM, shot
from rig import PAL, BPAL

fails = 0
def check(name, got, want):
    global fails
    ok = got == want
    print('%-56s %s %s' % (name, 'PASS' if ok else 'FAIL', '' if ok else '%r, wanted %r' % (got, want)))
    fails += not ok

def num(n):                     # a Sinclair BASIC number: its digits, then $0E and the 5-byte small integer
    return str(n).encode() + bytes([0x0E, 0, 0, n & 255, n >> 8, 0])
def block(flag, data):
    p = flag
    for x in data: p ^= x
    blk = bytes([flag]) + bytes(data) + bytes([p])
    return bytes([len(blk) & 255, len(blk) >> 8]) + blk
def header(kind, name, length, p1, p2):
    return block(0, bytes([kind]) + name.ljust(10).encode() + bytes([length & 255, length >> 8, p1 & 255, p1 >> 8, p2 & 255, p2 >> 8]))
def game_tape(name, ret):
    """10 BORDER 1: LOAD "" CODE : RANDOMIZE USR 32768, then code that fills the screen
    ($AA pixels, yellow on blue), makes the border green, and loops (or returns)"""
    body = b'\xE7' + num(1) + b':\xEF""\xAF:\xF9\xC0' + num(32768) + b'\x0D'
    prog = bytes([0, 10, len(body) & 255, len(body) >> 8]) + body
    code = bytes([0x21, 0x00, 0x40, 0x11, 0x01, 0x40, 0x01, 0xFF, 0x17, 0x36, 0xAA, 0xED, 0xB0,   # pixels
                  0x21, 0x00, 0x58, 0x11, 0x01, 0x58, 0x01, 0xFF, 0x02, 0x36, 0x0E, 0xED, 0xB0,   # attributes
                  0x3E, 0x04, 0xD3, 0xFE, 0xFB])                                                 # border green, EI
    code += bytes([0xC9]) if ret else bytes([0x76, 0x18, 0xFD])                                   # RET, or HALT: JR
    return (header(0, name, len(prog), 10, len(prog)) + block(0xFF, prog) +
            header(3, name + 'c', len(code), 32768, 32768) + block(0xFF, code))

card = tempfile.mkdtemp(prefix='pcspec_card_')
open(os.path.join(card, 'game.tap'), 'wb').write(game_tape('game', False))
open(os.path.join(card, 'gamer.tap'), 'wb').write(game_tape('gamer', True))
b = Basic(); s = b.s; s.sd(card)
def typed(text):
    s.run_until(SYM['cg_lp'], 20_000_000)
    s.load(SYM['EBUF'], text.encode()); s.poke(SYM['CON_LEN'], len(text))
    s.setregs(PC=SYM['con_enter'], SP=s.regs()['SP'] + 2)

check('at the prompt: OpticOS\'s display', s.mode(), 0)
typed('LOAD "game"'); s.frame(150)
check('a Sinclair game: the Spectrum screen is shown', s.mode(), 1)
check('...with its border colour (OUT 254)', s.border(), 4)
im = s.image(scale=1)
check('its pixels at (32, 64) on the panel, in its colours',
      (im.getpixel((32, 64)), im.getpixel((33, 64)), im.getpixel((32 + 255, 64 + 191))), (PAL[6], PAL[1], PAL[1]))
check('...inside the border', (im.getpixel((0, 0)), im.getpixel((319, 319)), im.getpixel((16, 100))), (PAL[4],) * 3)
shot(s, 'pc_spectrum_game.png')

b = Basic(); s = b.s; s.sd(card)
b.line('LOAD "gamer"')
check('a game that returns: back at the prompt, OpticOS\'s display', (s.mode(), b.screen()[-1] == ']' or ']' in b.screen()), (0, True))
check('...its Spectrum screen was drawn ($AA at $4000)', s.peek(0x4000), 0xAA)

b.enter(['OUT 27*256+209, 1', 'POKE 16384, 255', 'WAIT 20']); typed('RUN'); s.frame(8)
check('OUT 27*256+209, 1 in a program shows the Spectrum screen', s.mode(), 1)
s.run_until(SYM['cg_lp'], 200_000_000)
check('...and the prompt shows OpticOS\'s display again', s.mode(), 0)
b.line('OUT 27*256+209, 1'); check('typed at the prompt it lasts only to the next prompt', s.mode(), 0)

s.kempston(0x10); r = b.run(['PRINT IN 31'])
check('Kempston: IN 31 reads the joystick (fire)', r[-1], '16')
s.kempston(0x05); r = b.run(['PRINT IN 31'])
check('Kempston: right and down', r[-1], '5')
s.kempston(0)
shutil.rmtree(card)
print('%d failure(s)' % fails); sys.exit(1 if fails else 0)
