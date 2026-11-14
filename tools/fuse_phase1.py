#!/usr/bin/env python3
"""Run OpticOS in real Fuse (SDL) on a private Xvfb with tape traps OFF and
real-signal loading, type LOAD "" and capture screenshots.
Usage: fuse_phase1.py build/opticos.rom out_dir [tape ...]"""
import os, subprocess, sys, time
DISP = ':57'
ENV = dict(os.environ, DISPLAY=DISP, SDL_AUDIODRIVER='dummy')
PREFIX = '/workspace/tools-prefix'
if os.path.isdir(PREFIX):
    ENV['PATH'] = PREFIX + '/usr/bin:' + ENV['PATH']
    ENV['LD_LIBRARY_PATH'] = PREFIX + '/usr/lib/x86_64-linux-gnu'
DATA = PREFIX + '/usr/share/fuse' if os.path.isdir(PREFIX + '/usr/share/fuse') else '.'
def x(*a): return subprocess.run(list(a), env=ENV, capture_output=True, text=True).stdout
def ensure_x():
    if subprocess.run(['xdotool', 'getmouselocation'], env=ENV, capture_output=True).returncode:
        subprocess.Popen(['Xvfb', DISP, '-screen', '0', '800x600x24'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)
class Fuse:
    def __init__(self, rom, tape=None, traps=False):
        # traps=False: real tape signal only.  traps=True: Fuse's defaults
        # (tape traps, loader detection and loader acceleration all on).
        ensure_x()
        mode = ['--traps', '--detect-loader', '--accelerate-loader'] if traps else \
               ['--no-traps', '--no-detect-loader', '--no-accelerate-loader']
        args = ['fuse-sdl', '--machine', '48', '--rom-48', rom, '--no-auto-load'] + mode + ['--fastload', '--no-sound',
                '--no-confirm-actions', '--no-statusbar', '--graphics-filter', 'normal']
        if tape: args += ['--tape', tape]
        self.p = subprocess.Popen(args, env=ENV, cwd=DATA, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        for _ in range(50):
            time.sleep(0.2)
            w = x('xdotool', 'search', '--pid', str(self.p.pid)).split()
            if w: self.win = w[-1]; break
        else: raise RuntimeError('no Fuse window: ' + self.p.stderr.read().decode()[:500])
        time.sleep(1)
        g = dict(l.split('=') for l in x('xdotool', 'getwindowgeometry', '--shell', self.win).split())
        self.geo = int(g['X']), int(g['Y']), int(g['WIDTH']), int(g['HEIGHT'])
        x('xdotool', 'windowfocus', '--sync', self.win)
        x('xdotool', 'mousemove', '0', '0')
    def key(self, k, hold=0.12, mods=()):
        for m in mods: x('xdotool', 'keydown', m)
        x('xdotool', 'keydown', k); time.sleep(hold); x('xdotool', 'keyup', k)
        for m in mods: x('xdotool', 'keyup', m)
        time.sleep(0.08)
    def shot(self, out):
        X, Y, W, H = self.geo
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-f', 'x11grab', '-video_size', '%dx%d' % (W, H),
                        '-i', '%s+%d,%d' % (DISP, X, Y), '-frames:v', '1', '-vf', 'scale=iw*2:ih*2:flags=neighbor', out], env=ENV)
    def close(self): self.p.terminate(); self.p.wait()

if __name__ == '__main__':
    # --traps: Fuse's defaults (tape traps, loader detection and acceleration);
    # the tape is then started by Fuse itself, so F8 is not pressed.
    TRAPS = '--traps' in sys.argv
    sys.argv = [a for a in sys.argv if a != '--traps']
    rom, out = os.path.abspath(sys.argv[1]), sys.argv[2]
    os.makedirs(out, exist_ok=True)
    subprocess.run(['pkill', '-f', 'fuse-sdl.*opticos'])
    f = Fuse(rom, traps=TRAPS); time.sleep(4.5)   # boot, chime and the 0.8 s key swallow
    f.shot(os.path.join(out, 'fuse_boot.png'))
    for k in 'hello':
        f.key(k)
    f.key('Return'); time.sleep(0.5)
    f.shot(os.path.join(out, 'fuse_console.png')); f.close()
    for tape in sys.argv[3:]:
        name = os.path.splitext(os.path.basename(tape))[0]
        f = Fuse(rom, os.path.abspath(tape), traps=TRAPS); time.sleep(4.5)   # boot, chime and the 0.8 s key swallow
        for k in 'load': f.key(k)
        f.key('space'); f.key('p', mods=('Control_L',)); f.key('p', mods=('Control_L',))
        f.key('Return'); time.sleep(0.3)
        if not TRAPS: f.key('F8')        # play the tape
        t0 = time.time(); last = None; still = 0
        # wait for loading to finish: the screen stops changing, or the
        # tape's real-time length has passed (animated title screens)
        limit = {'bounceball': 75, 'miremare': 225}.get(name, 300)
        while time.time() - t0 < limit:
            time.sleep(5)
            f.shot('/tmp/_fuse_poll.png')
            d = open('/tmp/_fuse_poll.png', 'rb').read()
            still = still + 1 if d == last else 0
            last = d
            if still >= 3 and time.time() - t0 > 20: break
        f.shot(os.path.join(out, 'fuse_%s.png' % name))
        print(name, 'settled after %.0f s' % (time.time() - t0))
        if name == 'bounceball':
            f.key('space', hold=0.3); time.sleep(2)
            f.shot(os.path.join(out, 'fuse_%s_play.png' % name))
        f.close()
