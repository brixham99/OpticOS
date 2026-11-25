' Concentric-circle / target demo for SCREEN 0-3.
' Rings are four pixels (or four chunky pixels / cells) thick, to cut clash.
SCREEN 0: BORDER 0: PAPER 0: INK 7: CLS
t = FRAMES
PAPER 1: INK 7: CLS
target 128, 96, 88
s0 = INT((FRAMES - t) / 5) / 10
WAIT 250
t = FRAMES
SCREEN 1: PAPER 1: INK 7: CLS
target 128, 96, 88
s1 = INT((FRAMES - t) / 5) / 10
WAIT 250
t = FRAMES
SCREEN 2: PAPER 1: INK 7: CLS
target 32, 24, 22
s2 = INT((FRAMES - t) / 5) / 10
WAIT 250
t = FRAMES
SCREEN 3: PAPER 1: INK 7: CLS
target 16, 12, 11
s3 = INT((FRAMES - t) / 5) / 10
WAIT 250
SCREEN 0
PRINT "SCREEN 0 in "; s0; " s"
PRINT "SCREEN 1 in "; s1; " s"
PRINT "SCREEN 2 in "; s2; " s"
PRINT "SCREEN 3 in "; s3; " s"

DEF PROC target(cx, cy, rmax)
  ' Concentric rings, alternating red and white, on the blue field.
  r = rmax
  c = 2
  WHILE r >= 0
    CIRCLE cx, cy, r, c
    IF c = 2 THEN c = 7 ELSE c = 2
    r = r - 4
  WEND
ENDPROC
