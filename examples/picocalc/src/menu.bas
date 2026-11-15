' OpticOS examples for the PicoCalc: the menu
DEF PROC menu
  BORDER 0: PAPER 0: INK 7: CLS
  INK 6: PRINT "OpticOS examples for the PicoCalc": INK 7
  PRINT
  RESTORE menu
  REPEAT
    READ n$, d$
    IF n$ <> "" THEN PRINT TAB(1); "LOAD """; n$; """": PRINT TAB(3); INK 5; d$
  UNTIL n$ = ""
  PRINT
  PRINT "Type a LOAD line, then RUN."
  PRINT "LIST shows the program."
  DATA "times", "a times table with TAB and INK"
  DATA "guess", "the computer halves to a number"
  DATA "fact", "recursive functions"
  DATA "sort", "DATA, RESTORE name, SWAP, arrays"
  DATA "errors", "TRY, CATCH and ERROR n, msg$"
  DATA "ball", "a bouncing ball; SPACE stops it"
  DATA "tree", "a recursive tree drawn with DRAW TO"
  DATA "colour", "the colours, a cell per character"
  DATA "hilo", "guess my number (INPUT, TRY, CASE)"
  DATA "flag", "the Union Flag in cells and DRAW"
  DATA "happybatpc", "Happy Bat, a game: runs by itself"
  DATA "", ""
ENDPROC
