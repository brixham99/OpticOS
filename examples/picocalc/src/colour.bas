' Colours at 40 columns (PicoCalc)
BORDER 0: PAPER 0: INK 7: CLS
PRINT "The eight colours, as PAPER and INK:"
FOR c% = 0 TO 7
  PRINT AT 2 + c%, 0; PAPER c%; "      "; PAPER 0; INK c%; " INK "; c%; INK 7; BRIGHT 1; "  bright";
  PRINT AT 2 + c%, 24; INK c%; BRIGHT 1; "INK "; c%
NEXT
PRINT AT 11, 0; "Each character has its own colour"
PRINT AT 12, 0; "cell, so colours never clash:"
PRINT AT 13, 0; "Any column: ";
PRINT AT 13, 13; INK 2; "red"; INK 7; " - clean"
PRINT AT 15, 0; FLASH 1; INK 6; " FLASH "; FLASH 0; "  "; INVERSE 1; " INVERSE "; INVERSE 0
FOR x = 0 TO 319 STEP 40
  INK x / 40: PLOT x, 40: DRAW 39, 0: DRAW 0, -24: DRAW -39, 0: DRAW 0, 24
NEXT
INK 7
