' The Union Flag in each screen mode of OpticOS 128 (needs the screen-mode
' extension ROM in ROM slot 1): SCREEN 0 draws it by colour cells and lines
' as flag.bas does; SCREEN 1 (64x48) and SCREEN 2 (32x24, one colour per
' cell) draw the same flag pixel by pixel, from its geometry.
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
DEF PROC flagpix(w, h, top)
  ' the flag in w x h pixels from row top down, in 60 x 30 flag units;
  ' it looks the same turned half a turn, so each pixel is plotted twice
  FOR j = 0 TO h / 2 - 1
    v = (j + 0.5) * 30 / h
    FOR i = 0 TO w - 1
      u = (i + 0.5) * 60 / w
      c = 1
      d1 = 2 * v - u
      d2 = 2 * v + u - 60
      IF ABS d1 < 6.7 OR ABS d2 < 6.7 THEN c = 7
      IF u < 30 AND d1 > 0 AND d1 < 4.5 THEN c = 2
      IF u >= 30 AND d2 < 0 AND d2 > -4.5 THEN c = 2
      IF ABS (u - 30) < 5 OR ABS (v - 15) < 5 THEN c = 7
      IF ABS (u - 30) < 3 OR ABS (v - 15) < 3 THEN c = 2
      PLOT i, top - j, c
      PLOT w - 1 - i, top - h + 1 + j, c
    NEXT i
  NEXT j
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
flagpix 64, 32, 47
s1 = INT((FRAMES - t) / 5) / 10
WAIT 250
t = FRAMES
SCREEN 2: CLS
flagpix 32, 16, 23
s2 = INT((FRAMES - t) / 5) / 10
WAIT 250
SCREEN 0
PRINT "SCREEN 1 in "; s1; " s, SCREEN 2 in "; s2; " s"
