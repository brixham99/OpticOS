' The Union Flag, drawn by colour cells and lines (PicoCalc version)
' The flag fills the top 20 character rows (y 160-319), 320 x 160 pixels;
' the rows below stay black. Colours are laid out by 8x8 colour cell: blue
' PAPER for the field, white INK lines for the diagonals, red PAPER showing
' through cleared pixels for the thin red diagonals, and whole cells of
' PAPER for the central cross.
DEF PROC span(x1, x2, y)
  ' one horizontal run of pixels, clipped to the flag's width
  IF x1 < 0 THEN x1 = 0
  IF x2 > 319 THEN x2 = 319
  IF x1 <= x2 THEN PLOT x1, y: DRAW x2 - x1, 0
ENDPROC
DEF PROC field
  ' the blue field: 20 rows of blue paper
  PAPER 1: INK 7: BRIGHT 0
  FOR r = 0 TO 19
    PRINT AT r, 0; STRING$(40, " ");
  NEXT r
ENDPROC
DEF PROC diagonals
  ' the white saltire: two bands, 81 pixels across, corner to corner
  INK 7: PAPER 1: INVERSE 0
  FOR r = 0 TO 159
    a = 0
    IF r < 80 THEN a = 1
    span 2 * r - 40, 2 * r + 40 + a, 319 - r
    span 279 + a - 2 * r, 359 - 2 * r, 319 - r
  NEXT r
ENDPROC
DEF PROC edges(top, bottom)
  ' white pixel rows of the cross's border that share cells with the diagonals
  INK 7: PAPER 1: INVERSE 0
  FOR r = top TO bottom
    span 0, 319, 319 - r
  NEXT r
ENDPROC
DEF PROC red_diagonals
  ' the thin red diagonals, offset from the centre of each white band;
  ' clearing pixels lets the red paper show while the white ink stays
  INK 7: PAPER 2: INVERSE 1
  FOR r = 0 TO 51
    span 2 * r - 19, 2 * r + 3, 319 - r
    span 299 - 2 * r, 318 - 2 * r, 319 - r
  NEXT r
  FOR r = 108 TO 159
    span 320 - 2 * r, 339 - 2 * r, 319 - r
    span 2 * r - 1, 2 * r + 19, 319 - r
  NEXT r
  INVERSE 0
ENDPROC
DEF PROC cross
  ' the central cross in whole cells: white border, red centre
  PRINT AT 7, 0; PAPER 7; STRING$(40, " ");
  PRINT AT 12, 0; PAPER 7; STRING$(40, " ");
  FOR r = 8 TO 11
    PRINT AT r, 0; PAPER 2; STRING$(40, " ");
  NEXT r
  FOR r = 0 TO 19
    IF r < 7 OR r > 12 THEN PRINT AT r, 17; PAPER 7; " "; PAPER 2; "    "; PAPER 7; " ";
    IF r >= 7 AND r <= 12 THEN PRINT AT r, 18; PAPER 2; "    ";
  NEXT r
ENDPROC
' main program
t = FRAMES
BORDER 0: PAPER 0: INK 7: CLS
field
diagonals
edges 52, 55
edges 104, 107
red_diagonals
cross
PAPER 0: INK 7
PRINT AT 22, 0; "Drawn in "; INT((FRAMES - t) / 5) / 10; " seconds";
