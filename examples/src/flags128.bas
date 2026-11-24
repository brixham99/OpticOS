' The Union Flag in each screen mode of OpticOS 128 (needs the merged
' SAY+SCREEN extension ROM in slot 1).  SCREEN 0 uses the original flag
' listing (colour cells and DRAW).  SCREEN 1 (64x48) and SCREEN 2 (32x24)
' draw the same flag with BOX and DRAW, which write the framebuffer in
' machine code.
' The Union Flag, drawn by colour cells and lines
' The flag fills the top 16 character rows (y 64-191); the rows below stay black.
' Colours are laid out by 8x8 colour cell: blue PAPER for the field, white INK
' lines for the diagonals, red PAPER showing through cleared pixels for the
' thin red diagonals, and whole cells of PAPER for the central cross.
DEF PROC span(x1, x2, y)
  ' one horizontal run of pixels, clipped to the flag's width
  IF x1 < 0 THEN x1 = 0
  IF x2 > 255 THEN x2 = 255
  IF x1 <= x2 THEN PLOT x1, y: DRAW x2 - x1, 0
ENDPROC
DEF PROC field
  ' the blue field: 16 rows of blue paper
  PAPER 1: INK 7: BRIGHT 0
  FOR r = 0 TO 15
    PRINT AT r, 0; STRING$(64, " ");
  NEXT r
ENDPROC
DEF PROC diagonals
  ' the white saltire: two bands, 65 pixels across, corner to corner
  INK 7: PAPER 1: INVERSE 0
  FOR r = 0 TO 127
    a = 0
    IF r < 64 THEN a = 1
    span 2 * r - 32, 2 * r + 32 + a, 191 - r
    span 223 + a - 2 * r, 287 - 2 * r, 191 - r
  NEXT r
ENDPROC
DEF PROC edges(top, bottom)
  ' white pixel rows of the cross's border that share cells with the diagonals
  INK 7: PAPER 1: INVERSE 0
  FOR r = top TO bottom
    span 0, 255, 191 - r
  NEXT r
ENDPROC
DEF PROC red_diagonals
  ' the thin red diagonals, offset from the centre of each white band;
  ' clearing pixels lets the red paper show while the white ink stays
  INK 7: PAPER 2: INVERSE 1
  FOR r = 0 TO 35
    span 2 * r - 15, 2 * r + 2, 191 - r
    span 239 - 2 * r, 254 - 2 * r, 191 - r
  NEXT r
  FOR r = 92 TO 127
    span 256 - 2 * r, 271 - 2 * r, 191 - r
    span 2 * r - 1, 2 * r + 15, 191 - r
  NEXT r
  INVERSE 0
ENDPROC
DEF PROC cross
  ' the central cross in whole cells: white border, red centre
  PRINT AT 5, 0; PAPER 7; STRING$(64, " ");
  PRINT AT 10, 0; PAPER 7; STRING$(64, " ");
  FOR r = 6 TO 9
    PRINT AT r, 0; PAPER 2; STRING$(64, " ");
  NEXT r
  FOR r = 0 TO 15
    IF r < 5 OR r > 10 THEN PRINT AT r, 26; PAPER 7; "  "; PAPER 2; "        "; PAPER 7; "  ";
    IF r >= 5 AND r <= 10 THEN PRINT AT r, 28; PAPER 2; "        ";
  NEXT r
ENDPROC

DEF PROC dband(w, h, top, i0, i1, d0, d1, c)
  ' both saltire arms: a horizontal run [xa+d0, xa+d1] in colour c
  ' on every row i from the top (i0..i1).  xa is 2*i (\) or w-1-2*i (/).
  ' If xa is odd the run is shifted left one pixel so mode 1 edges sit
  ' on the 2x2 attribute grid (no three colours in one cell).
  FOR i = i0 TO i1
    y = top - i
    xa = 2 * i
    a = xa + d0
    b = xa + d1
    IF xa <> 2 * (xa DIV 2) THEN a = a - 1: b = b - 1
    IF a < 0 THEN a = 0
    IF b > w - 1 THEN b = w - 1
    IF a <= b THEN PLOT a, y, c: DRAW TO b, y, c
    xa = w - 1 - 2 * i
    a = xa + d0
    b = xa + d1
    IF xa <> 2 * (xa DIV 2) THEN a = a - 1: b = b - 1
    IF a < 0 THEN a = 0
    IF b > w - 1 THEN b = w - 1
    IF a <= b THEN PLOT a, y, c: DRAW TO b, y, c
  NEXT i
ENDPROC
DEF PROC flag(w, h, top)
  ' Union Flag, w by h, top row at y = top (origin bottom left).
  ' White-band thickness matches the earlier centred listing
  ' (mode 1 ~6 chunky px vertical, mode 2 ~3-4 cells). The red saltire
  ' is offset as in SCREEN 0: to the left in the top half, to the right
  ' in the bottom half, with white remaining on both sides of the red.
  bot = top - h + 1
  BOX 0, bot, w, h, 1
  m = h DIV 2
  IF h < 24 THEN wd0 = -3 ELSE wd0 = -6
  IF h < 24 THEN wd1 = 4 ELSE wd1 = 7
  IF h < 24 THEN rt0 = -1 ELSE rt0 = -4
  rt1 = 0
  rb0 = 1
  IF h < 24 THEN rb1 = 2 ELSE rb1 = 5
  dband w, h, top, 0, h - 1, wd0, wd1, 7
  dband w, h, top, 0, m - 1, rt0, rt1, 2
  dband w, h, top, m, h - 1, rb0, rb1, 2
  cw = (h + 2) DIV 6
  IF cw < 1 THEN cw = 1
  BOX w DIV 2 - cw, bot, 2 * cw, h, 7
  BOX 0, bot + h DIV 2 - cw, w, 2 * cw, 7
  cr = (h + 4) DIV 10
  IF cr < 1 THEN cr = 1
  BOX w DIV 2 - cr, bot, 2 * cr, h, 2
  BOX 0, bot + h DIV 2 - cr, w, 2 * cr, 2
ENDPROC
' main program
t = FRAMES
SCREEN 0: BORDER 0: PAPER 0: INK 7: CLS
field
diagonals
edges 36, 39
edges 88, 91
red_diagonals
cross
PAPER 0: INK 7
PRINT AT 22, 0; "SCREEN 0 in "; INT((FRAMES - t) / 5) / 10; " seconds";
WAIT 250
t = FRAMES
SCREEN 1: CLS
flag 64, 32, 47
s1 = INT((FRAMES - t) / 5) / 10
WAIT 250
t = FRAMES
SCREEN 2: CLS
flag 32, 16, 23
s2 = INT((FRAMES - t) / 5) / 10
WAIT 250
SCREEN 0
PRINT "SCREEN 1 in "; s1; " s, SCREEN 2 in "; s2; " s"
