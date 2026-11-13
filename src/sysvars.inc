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

; ---- maths workspace (phase 2), $5B61-$5BFF (see docs/maths.md)
RNDS     equ $5C93      ; reused MEMBOT: 32-bit RND state (4 bytes)
FSG      equ $5B61      ; maths scratch byte
NBUF     equ $5B62      ; number-to-string output (16)
NDIG     equ $5B72      ; decimal digits (9)
NDE      equ $5B7B      ; decimal exponent of the first digit
NCNT     equ $5B7C      ; digit count
VDX      equ $5B7D      ; string-to-number decimal exponent
NBP      equ $5B7E      ; output pointer into NBUF (2)
FA       equ $5B80      ; unpacked accumulator: g m1 m2 m3 m4 exp sign (8)
FB       equ $5B88      ; unpacked operand
FT       equ $5B90      ; byte-code temporaries T0-T6, 8 bytes each
T6       equ $5BC0      ; T6: polynomial argument / scratch
FRP      equ $5BFC      ; saved right-operand pointer (2)
VSP      equ $5BFE      ; value stack pointer (2)

; ---- phase 3 interpreter workspace ($5BC8-$5BFB; the value stack itself
; now lives below RAMTOP, see ws_init)
CSB      equ $5BC8      ; control stack base (grows down from here)
CSLIM    equ $5BCA      ; control stack limit
VSB      equ $5BCC      ; value stack base (5-byte entries, grows up)
VSLIM    equ $5BCE      ; value stack limit
TKB      equ $5BD0      ; tokenised direct-mode line (256 bytes)
HTOP     equ $5BD2      ; string heap top (exclusive)
HP       equ $5BD4      ; string heap bottom (lowest block)
VARSB    equ $5BD6      ; variables start (after the PROC/FN table)
VEND     equ $5BD8      ; variables end
PEND     equ $5BDA      ; program end (the $00 sentinel)
CSP      equ $5BDC      ; control stack pointer
CURLN    equ $5BDE      ; line being executed
VID      equ $5BE0      ; identifier token being looked up
VHD      equ $5BE2      ; its hash-chain head
VTY      equ $5BE4      ; its type
ERRV     equ $5BE5      ; ERR: number of the last error
PPF      equ $5BE6      ; 1 = program changed, prepass needed
LSTLV    equ $5BE7      ; LIST indent level
LSTCH    equ $5BE8      ; LIST: last character printed
BCN      equ $5BE9      ; bind: arguments left
BAP      equ $5BEA      ; bind: next argument (2)
BAF      equ $5BEC      ; bind: first argument (2)
GS       equ $5BEE      ; GC: block start (2)
GB       equ $5BF0      ; GC: back-pointer (2)
GN       equ $5BF2      ; GC: new start (2)
GD       equ $5BF4      ; GC: destination top (2)
GL       equ $5BF6      ; GC: length
GF       equ $5BF7      ; GC: scan mode
WLEN     equ $5BF8      ; tokeniser: word length
TMP      equ $5BFA      ; scratch (2)
DIMB     equ $5B40      ; DIM sizes / tokeniser number (legacy area, 8 bytes)
HEADS    equ $5CCB      ; 32 variable hash-chain heads
STATIC   equ $5D0B      ; A%-Z%, 2 bytes each
CURL     equ $5D40      ; current line (marker), 0 = above the first line
ESTART   equ $5D42      ; input line: linear screen position of its text
EIDX     equ $5D44      ; input line: cursor index
EMODE    equ $5D45      ; bit 0 insert mode (AUTO), bit 1 EDIT replace pending
CON_LEN  equ $5D46      ; input line: length
EBUF     equ $5D50      ; input line buffer (128 bytes, 126 characters)
EMAX     equ 126
OPROG    equ $5DD0      ; OpticBASIC program start
