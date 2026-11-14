"""Fuse 1.6.0's phantom typist (phantom_typist.c, 48K "Keyword" mode, JPP:
J, SS+P, SS+P, ENTER) re-created frame by frame in the OpticOS test rig.
Fuse rules copied from the source:
 * after reset the typist WAITS until, in one frame, every keyboard half-row
   ($FE,$FD,...,$7F) has been read; then the next state is LOAD;
 * at each frame end: state = next; delay = the state's delay_before_state;
   then delay is decremented once if > 0;
 * while delay > 0 reads see no keys; otherwise a read sees the state's keys
   and sets next = the following state (so each key is down for one frame,
   for every read in that frame).
States: LOAD (J, delay 8) -> QUOTE1 (SS+P, 0) -> QUOTE2 (SS+P, 5) -> ENTER (0).
In OpticOS the only keyboard reads at boot and at the prompt are the ISR's
kscan of all 8 rows, so 'some reads this frame' == 'the ISR ran' (FRAMES moved)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
STATES = {'LOAD': (['j'], 'QUOTE1', 8), 'QUOTE1': (['sym', 'p'], 'QUOTE2', 0),
          'QUOTE2': (['sym', 'p'], 'ENTER', 5), 'ENTER': (['enter'], 'INACTIVE', 0)}
KEYMAP = {'j': 'j', 'p': 'p', 'sym': '#', 'enter': '\n'}
class Typist:
    def __init__(self, s, frames_addr=23672):
        self.s = s; self.state = 'WAITING'; self.next = 'WAITING'; self.delay = 0
        self.fa = frames_addr; self.log = []; self.n = 0
    def keys(self):
        if self.state in STATES and self.delay == 0: return STATES[self.state][0]
        return []
    def frame(self, setkey):
        ks = self.keys()
        for k in ks: setkey(k, True)
        f0 = self.s.peek(self.fa)
        self.s.frame(1)
        read = self.s.peek(self.fa) != f0
        for k in ks: setkey(k, False)
        if read:
            if self.state == 'WAITING': self.next = 'LOAD'
            elif self.state in STATES and self.delay == 0:
                self.next = STATES[self.state][1]; self.log.append((self.n, self.state, '+'.join(ks)))
        if self.next != self.state:
            self.state = self.next; self.delay = STATES.get(self.state, ([], '', 0))[2]
        if self.delay > 0: self.delay -= 1
        self.n += 1
