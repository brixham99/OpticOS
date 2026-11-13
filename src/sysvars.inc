; sysvars.inc - OpticOS system variables.
; Addresses and meanings at the Sinclair-compatible slots are a published
; interface (spec section 9). Slots marked "reused" hold OpticOS internals.

KS_LAST  equ $5C00      ; reused (KSTATE): index of the key last seen, $FF none
KS_CNT   equ $5C01      ; reused: auto-repeat countdown
KS_MODE  equ $5C02      ; reused: bit 0 caps lock, bit 1 E mode pending
CUR_VIS  equ $5C03      ; reused: console cursor currently drawn (0/1)
LAST_K   equ $5C08
REPDEL   equ $5C09
REPPER   equ $5C0A
PR_CTRL  equ $5C0E      ; reused (TVDATA): pending control code, 0 none
PR_P1    equ $5C0F      ; reused: first AT/TAB parameter, $FF none yet
STRMS    equ $5C10      ; stream table, streams -3..15
CHARS    equ $5C36
ERR_NR   equ $5C3A
FLAGS    equ $5C3B
ERR_SP   equ $5C3D
BORDCR   equ $5C48
VARS     equ $5C4B
CHANS    equ $5C4F
CURCHL   equ $5C51
PROG     equ $5C53
NXTLIN   equ $5C55      ; legacy shim: address of next BASIC line
E_LINE   equ $5C59
CH_ADD   equ $5C5D      ; legacy shim: text pointer
DF_SZ    equ $5C6B
SEED     equ $5C76
FRAMES   equ $5C78      ; 3 bytes
UDG      equ $5C7B
COORDS   equ $5C7D
S_POSN   equ $5C88      ; column (0-63), +1 row (0-23)
ATTR_P   equ $5C8D
MASK_P   equ $5C8E
ATTR_T   equ $5C8F
MASK_T   equ $5C90
P_FLAG   equ $5C91      ; bit 0 OVER, bit 2 INVERSE
; MEMBOT ($5C92-$5CAF) is reused for OpticOS internals
OMODE    equ $5C92      ; text mode: 64
GLYPHBUF equ $5C98      ; 8 bytes, must not cross a page
NMIADD   equ $5CB0
RAMTOP   equ $5CB2
P_RAMT   equ $5CB4
CHANTAB  equ $5CB6      ; channel table K S R P, $80 (21 bytes)
LEGPROG  equ $5CCB      ; legacy BASIC programs load here
LINEBUF  equ $5B00      ; console edit line (64 bytes)
LG_WANT  equ $5B40      ; legacy LOAD: wanted type
LG_NAME  equ $5B41      ; legacy LOAD: wanted name (10), $FF = any
LG_DEST  equ $5B4C      ; legacy LOAD: explicit destination (2), 0 = header
HDRBUF   equ $5B50      ; 17-byte tape header buffer

FONT     equ $3E80
