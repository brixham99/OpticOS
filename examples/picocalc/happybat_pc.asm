; =============================================================================
; happybat_pc.asm - the machine-code half of Happy Bat for the PicoCalc
; (OpticOS's PicoCalc build).  Assemble with pasmo:
;     pasmo --bin happybat_pc.asm hbcodepc.bin
;
; A port of examples/src/happybat.asm (the ZX Spectrum version, unchanged).
; The game is the same; the screen is the PicoCalc's 320 x 320 pixels, which
; machine code reaches through the display device on port $D1 (register in B,
; emu/picocalc.c) rather than through screen memory:
;   byte access  - a byte is 8 pixels of a line, bit 7 leftmost; column
;                  0-39, line 0-319 from the top.  PUT / XOR (with a hit
;                  latch for collisions) step along the line; NEXT goes
;                  down one; RLD scrolls a line 4 pixels left; a row pattern
;                  of up to 8 bytes can be FILLed down many lines at once.
;   cells        - one attribute per 8 x 8 cell (40 x 40), set by COL, ROW
;                  and CELL; CLS clears every pixel and sets every cell.
; Written from scratch (clean room), like the Spectrum version.  It uses no
; IX, IY or alternate registers, and waits for frames with HALT.
;
; OpticBASIC's CALL and USR take no register arguments, so BASIC POKEs (and
; DPOKEs) the parameter block below; USR 60003 hands back a step's result.
;
; Screen layout (pixel lines from the top):
;   lines   0- 15  rows 0-1: the score line, printed by BASIC
;   lines  16-303  the playfield, 288 lines: sky, pipes and the bat
;   lines 304-311  row 38: the ground, which scrolls
;   lines 312-319  row 39: help text, printed by BASIC
; Horizontal positions are in nibbles (4 pixels): the screen is 80 nibbles
; wide and everything moves one nibble left per step.
; =============================================================================

DEV      equ $D1            ; the display device
DV_COL   equ 0              ; registers (src/sysvars.inc, emu/picocalc.c)
DV_ROW   equ 1
DV_CELL  equ 6
DV_CLS   equ 8
DV_BCOL  equ 17
DV_BLL   equ 18             ; (DV_BLH = 19)
DV_BPUT  equ 20
DV_BXOR  equ 21
DV_HIT   equ 22
DV_NEXT  equ 23
DV_RLD   equ 24
DV_PAT   equ 25
DV_FILL  equ 26

PF_TOP   equ 16             ; first screen line of the playfield
PF_H     equ 288            ; playfield height in lines
GR_TOP   equ 304            ; first line of the ground
GR_ROW   equ 38             ; its character row
BASE_ROW equ 39             ; the help text's row
YMAX     equ 280            ; lowest top line for the 8-line bat
BAT_COL  equ 10             ; the bat's byte column: x = 80-95
BAT_NIB  equ 20             ; ... = nibble 20
NIBS     equ 80             ; the screen is 80 nibbles wide
NPIPE    equ 5              ; pipe slots (pipes 24 nibbles apart: at most 4)
PSZ      equ 6              ; bytes a slot: x, gap top (2), gap bottom (2), spare
FREE     equ $80            ; x value marking a free slot
A_SKY    equ $4C            ; bright, blue paper, green ink (pipes)
A_BAT    equ $4E            ; bright, blue paper, yellow ink (the bat)
A_DEAD   equ $4A            ; bright, blue paper, red ink (a dead bat)
A_GROUND equ $66            ; bright, green paper, yellow ink
A_BASE   equ $60            ; bright, green paper, black ink (row 39)
FRAMES   equ 23672          ; OpticOS frame counter (low byte)

        org 60000

; ---- entry points: the addresses BASIC calls ---------------------------------
        jp init             ; 60000  CALL 60000: new playfield
        jp step             ; 60003  USR 60003: one step -> BC = 0, 1 or 2
        jp dead             ; 60006  CALL 60006: colour the bat red

; ---- parameters, POKEd / DPOKEd (and PEEKed) by BASIC ----------------------
baty:   defw 136            ; 60009  bat's top line in the playfield (0-280);
                            ;        BASIC sets it on the title screen and
                            ;        before CALL 60000; in play the code moves it
gaptop: defw 80             ; 60011  first line of the next pipe's gap
gapbot: defw 160            ; 60013  first line below that gap
newpipe: defb 0             ; 60015  POKE 1: start that pipe at the right edge
mode:   defb 1              ; 60016  1 = play; 0 = title (no gravity, no
                            ;        pipes: only the ground scrolls)
sig:    defm "HP"           ; 60017  signature: BASIC checks it to see
                            ;        whether the code is already loaded
grav:   defb 2              ; 60019  gravity, quarter pixels per step per step
flapv:  defb 18             ; 60020  a flap's upward speed, quarter px / step
vmax:   defb 20             ; 60021  fastest fall, quarter pixels per step
pacev:  defb 2              ; 60022  frames per step at least (1 or more)

; ---- internal state -------------------------------------------------------
y16:    defw 544            ; bat height in quarter pixels (0 - 4*YMAX)
v16:    defw 0              ; its speed, quarter pixels per step (+ = down)
pkey:   defb 0              ; 1 if SPACE was down at the last step
oldy:   defw 0              ; where the bat was drawn last
oldspr: defw spr_up         ; and with which wing frame
drawn:  defb 0              ; 1 while the bat is on the screen
tick:   defb 0              ; step counter, for the wing beat
phase:  defb 0              ; ground pattern phase, 0-3
lastf:  defb 0              ; FRAMES at the last step, for pacing
crash:  defb 0              ; set during a step: hit the top or the ground
scored: defb 0              ; set during a step: a pipe got past the bat
ptab:   defs NPIPE*PSZ,FREE ; the pipes
pg1:    defw 0              ; the pipe being drawn: its gap top
pg2:    defw 0              ;   and gap bottom
scol:   defb 0              ;   first byte column written on each line
slen:   defb 0              ;   bytes written on each line (1-5)
sbody:  defw 0              ;   where in its body pattern to start
scap:   defw 0              ;   and in its cap pattern
sptr:   defw 0              ; pattern for the lines seg is drawing

; -----------------------------------------------------------------------------
; init: clear the screen to the sky colour, colour the ground and help rows,
; draw the ground, and reset everything: no pipes, no bat on the screen, play
; mode, the bat at height baty and not moving.  BASIC prints the score line
; and any text afterwards.
; -----------------------------------------------------------------------------
init:   ld c,DEV
        ld a,A_SKY
        ld b,DV_CLS
        out (c),a           ; every pixel clear, every cell sky
        ld e,GR_ROW
        ld d,A_GROUND
        call row_attr
        ld e,BASE_ROW
        ld d,A_BASE
        call row_attr
        xor a               ; the ground: two bytes, 20 times a line
        ld b,DV_BCOL
        out (c),a
        ld hl,GR_TOP
        call bline
        ld de,ginit
        ld h,8              ; H = lines
in_gl:  ld l,20             ; L = pairs
        ld b,DV_BPUT
in_gp:  ld a,(de)
        out (c),a
        inc de
        ld a,(de)
        out (c),a
        dec de
        dec l
        jr nz,in_gp
        inc de              ; next ground line's pair
        inc de
        ld b,DV_NEXT
        out (c),a
        dec h
        jr nz,in_gl
        ld hl,ptab          ; every pipe slot free
        ld b,NPIPE*PSZ
in_pt:  ld (hl),FREE
        inc hl
        djnz in_pt
        xor a
        ld (drawn),a        ; no bat on the screen
        ld (tick),a
        ld (phase),a        ; 80 nibbles drawn: the next one is phase 0
        ld (newpipe),a
        ld h,a
        ld l,a
        ld (v16),hl         ; not moving
        inc a
        ld (mode),a         ; play mode
        ld (pkey),a         ; a SPACE still held from before is not a flap
        ld hl,(baty)        ; height in quarter pixels = baty * 4
        add hl,hl
        add hl,hl
        ld (y16),hl
        ld a,(FRAMES)
        ld (lastf),a
        ret

; row_attr: every cell of row E gets attribute D.  C = DEV.  A, B, L changed.
row_attr:
        ld b,DV_ROW
        out (c),e
        ld l,0
ra_lp:  ld b,DV_COL
        out (c),l
        ld b,DV_CELL
        out (c),d
        inc l
        ld a,l
        cp 40
        jr nz,ra_lp
        ret

; bline: HL = screen line -> the device's byte-access line.  C = DEV; B changed.
bline:  ld b,DV_BLL
        out (c),l
        inc b
        out (c),h
        ret

; -----------------------------------------------------------------------------
; step: one step of the game, called with r% = USR 60003.
;  1. wait until pacev frames have passed since the last step, so the game
;     runs at the same speed however much is on the screen;
;  2. take the bat off the screen;
;  3. in play: read SPACE and move the bat (phys), then start, move and draw
;     the pipes (pipes);
;  4. scroll the ground; put the bat back, testing its pixels as it goes.
; Returns BC = 1 if the bat crashed (pipe, ground or top), else 2 if a pipe
; has just got past the bat (a point), else 0.
; -----------------------------------------------------------------------------
step:   call pace
        call bat_off
        xor a
        ld (crash),a
        ld (scored),a
        ld a,(mode)
        or a
        jr z,st_t           ; title: no gravity, no pipes
        call phys
        call pipes
st_t:   call ground
        ld hl,tick
        inc (hl)
        call bat_on         ; C <> 0: the bat touched a pipe
        ld a,c
        or a
        jr z,st_1
        ld (crash),a
st_1:   ld bc,1
        ld a,(crash)
        or a
        ret nz              ; 1: crashed
        inc c
        ld a,(scored)
        or a
        ret nz              ; 2: scored
        ld c,0
        ret                 ; 0: flying on

; -----------------------------------------------------------------------------
; pace: HALT until at least pacev frames have passed since the last call.
; -----------------------------------------------------------------------------
pace:   ld hl,lastf
pa_lp:  ld a,(FRAMES)
        sub (hl)            ; frames since the last step
        ld b,a
        ld a,(pacev)
        dec a
        cp b                ; carry if B >= pacev
        jr c,pa_ok
        halt                ; wait for the next frame
        jr pa_lp
pa_ok:  ld a,(FRAMES)
        ld (hl),a
        ret

; -----------------------------------------------------------------------------
; phys: the bat's flight.  A new press of SPACE (it was up at the last step)
; sets the speed to -flapv and chirps; then gravity adds grav to the speed, up
; to vmax downwards, and the speed is added to the height.  Going above the
; top or below YMAX stops the bat there and sets crash.  baty = height / 4.
; -----------------------------------------------------------------------------
phys:   ld a,$7F            ; keyboard half-row SPACE, SYMBOL, M, N, B
        in a,($FE)
        cpl
        and 1               ; A = 1 while SPACE is held
        ld hl,pkey
        ld b,(hl)
        ld (hl),a
        jr z,ph_g           ; not held
        dec b
        jr z,ph_g           ; held, but it was held last step too
        ld a,(flapv)        ; a flap: speed = -flapv
        neg
        ld l,a
        ld h,$FF
        ld (v16),hl
        call chirp
ph_g:   ld hl,(v16)         ; gravity
        ld a,(grav)
        ld e,a
        ld d,0
        add hl,de
        bit 7,h
        jr nz,ph_v          ; still going up: no limit
        ld a,(vmax)
        ld e,a
        ld a,h
        or a
        jr nz,ph_cl
        ld a,l
        cp e
        jr c,ph_v
ph_cl:  ex de,hl            ; falling too fast: speed = vmax
ph_v:   ld (v16),hl
        ld de,(y16)
        add hl,de           ; new height
        bit 7,h
        jr z,ph_lo
        ld hl,0             ; above the top of the playfield
        jr ph_cr
ph_lo:  push hl
        ld de,YMAX*4+1
        or a
        sbc hl,de
        pop hl
        jr c,ph_ok
        ld hl,YMAX*4        ; on the ground
ph_cr:  ld a,1
        ld (crash),a
ph_ok:  ld (y16),hl
        srl h               ; baty = height / 4
        rr l
        srl h
        rr l
        ld (baty),hl
        ret

; -----------------------------------------------------------------------------
; chirp: a short rising click on the speaker for a flap (about 1 ms).
; Bit 4 of port 254 drives the speaker; bits 0-2 keep the border black.
; -----------------------------------------------------------------------------
chirp:  ld b,24
ch_lp:  ld a,b
        and 1
        rlca
        rlca
        rlca
        rlca
        out ($FE),a
        ld a,b
        add a,8
ch_d:   dec a
        jr nz,ch_d
        djnz ch_lp
        ret

; -----------------------------------------------------------------------------
; pipes: if BASIC asked for one (newpipe), put a new pipe in a free slot at
; x = 80, just off the right edge, with the gap from gaptop/gapbot.  Then
; move and redraw every pipe in use (pipe1).
; -----------------------------------------------------------------------------
pipes:  ld a,(newpipe)
        or a
        jr z,pp_mv
        xor a
        ld (newpipe),a
        ld hl,ptab
        ld de,PSZ
        ld b,NPIPE
pp_f:   ld a,(hl)
        cp FREE
        jr z,pp_new
        add hl,de
        djnz pp_f
        jr pp_mv            ; no free slot (cannot happen 24 steps apart)
pp_new: ld (hl),NIBS
        inc hl
        ex de,hl
        ld hl,gaptop        ; gap top and bottom, 2 bytes each
        ld bc,4
        ldir
pp_mv:  ld hl,ptab
        ld b,NPIPE
pp_lp:  push bc
        push hl
        call pipe1
        pop hl
        ld de,PSZ
        add hl,de
        pop bc
        djnz pp_lp
        ret

; -----------------------------------------------------------------------------
; pipe1: move the pipe in slot HL one nibble left and draw it.  A pipe is 8
; nibbles wide: x .. x+7.  Its right edge passing the bat (x = 12, so x+7 = 19
; is just left of nibble 20) sets scored.  A pipe gone off the left (x < -8)
; frees its slot.  Each line gets 5 bytes from a pattern (body or cap, for
; even or odd x), cut at the left edge (the device drops bytes past the
; right edge); the 5th byte rubs out the pixels the pipe has just left on
; its right.  The gap's lines are not touched.
; -----------------------------------------------------------------------------
pipe1:  ld a,(hl)
        cp FREE
        ret z
        dec a               ; one nibble left
        ld (hl),a
        cp BAT_NIB-8
        jr nz,p1_a
        ld a,1
        ld (scored),a       ; its right edge is past the bat
        ld a,(hl)
p1_a:   add a,8             ; x from -8 to 80 is on (or next to) the screen
        cp NIBS+9
        jr c,p1_on
        ld (hl),FREE        ; gone: free the slot
        ret
p1_on:  push hl
        inc hl
        ld de,pg1           ; gap top and bottom
        ld bc,4
        ldir
        pop hl
        ld a,(hl)           ; A = x
        ld de,body_e        ; patterns for even x
        ld bc,cap_e
        bit 0,a
        jr z,p1_ev
        ld de,body_o        ; or odd x
        ld bc,cap_o
p1_ev:  ld (sbody),de
        ld (scap),bc
        sra a               ; A = first byte column = x / 2, rounded down
        ld c,5              ; C = bytes a line
        bit 7,a
        jr z,p1_r
        neg                 ; partly off the left: A = bytes cut off
        ld b,a
        ld a,c
        sub b
        ld c,a
        ld e,b              ; start that far into the patterns
        ld d,0
        ld hl,(sbody)
        add hl,de
        ld (sbody),hl
        ld hl,(scap)
        add hl,de
        ld (scap),hl
        xor a               ; and at column 0
p1_r:   ld (scol),a
        ld a,c
        ld (slen),a
        ld hl,(sbody)       ; body from the top down to the top cap
        ld (sptr),hl
        ld de,(pg1)
        dec de
        dec de
        dec de
        dec de
        ld hl,0
        call seg
        ld hl,(scap)        ; the cap above the gap
        ld (sptr),hl
        ld hl,(pg1)
        ld de,-4
        add hl,de
        ld de,4
        call seg
        ld hl,(pg2)         ; the cap below it
        ld de,4
        call seg
        ld hl,(sbody)       ; body from below that cap to the ground
        ld (sptr),hl
        ld hl,(pg2)
        ld de,4
        add hl,de
        ex de,hl            ; DE = first line
        ld hl,PF_H
        or a
        sbc hl,de           ; HL = lines
        ex de,hl
        ; fall into seg

; -----------------------------------------------------------------------------
; seg: draw DE lines (1-288) of a pipe from playfield line HL: the slen-byte
; row at sptr, at byte column scol, filled down by the device.
; -----------------------------------------------------------------------------
seg:    push de
        ld de,PF_TOP
        add hl,de
        ld c,DEV
        call bline
        ld a,(scol)
        ld b,DV_BCOL        ; (empties the row pattern)
        out (c),a
        ld hl,(sptr)
        ld a,(slen)
        ld e,a
        ld b,DV_PAT
sg_p:   ld a,(hl)
        out (c),a
        inc hl
        dec e
        jr nz,sg_p
        pop de
        ld b,DV_FILL
        ld a,d
        or a
        jr z,sg_f
        xor a               ; 256 lines first (A = 0)
        out (c),a
sg_f:   ld a,e              ; the rest
        or a
        ret z
        out (c),a
        ret

; -----------------------------------------------------------------------------
; ground: scroll the 8 ground lines 4 pixels left, feeding in each line's
; next pattern nibble at the right, then advance the pattern phase.
; -----------------------------------------------------------------------------
ground: ld c,DEV
        ld hl,GR_TOP
        call bline
        ld a,(phase)
        ld e,a
        ld d,0
        ld hl,gpat
        add hl,de           ; HL -> this phase's nibble for ground line 0
        ld e,8
        ld b,DV_RLD
gd_lp:  ld a,(hl)
        out (c),a           ; (then the next line)
        inc hl              ; same phase, next line: 4 bytes on
        inc hl
        inc hl
        inc hl
        dec e
        jr nz,gd_lp
        ld a,(phase)
        inc a
        and 3
        ld (phase),a
        ret

; -----------------------------------------------------------------------------
; bat_on: draw the bat at baty with this step's wing frame (the wings beat
; every two steps) and colour its cells yellow.  Returns C <> 0 if any of its
; pixels landed on something already on the screen (a pipe).
; -----------------------------------------------------------------------------
bat_on: ld a,(tick)
        and 2
        ld hl,spr_up
        jr z,bo_1
        ld hl,spr_dn
bo_1:   ld (oldspr),hl
        ex de,hl            ; DE = sprite
        ld hl,(baty)
        ld (oldy),hl
        call bat_xor        ; C = sprite AND screen, before drawing
        push bc
        ld hl,(oldy)
        ld e,A_BAT
        call bat_attr
        ld a,1
        ld (drawn),a
        pop bc
        ret

; -----------------------------------------------------------------------------
; bat_off: if the bat is on the screen, XOR it away (which restores exactly
; what was under it) and give its cells back the sky colour.
; -----------------------------------------------------------------------------
bat_off: ld a,(drawn)
        or a
        ret z
        xor a
        ld (drawn),a
        ld de,(oldspr)
        ld hl,(oldy)
        call bat_xor
        ld hl,(oldy)
        ld e,A_SKY
        jp bat_attr

; -----------------------------------------------------------------------------
; dead: colour the bat red where it was last drawn (game over).
; -----------------------------------------------------------------------------
dead:   ld hl,(oldy)
        ld e,A_DEAD
        jp bat_attr

; -----------------------------------------------------------------------------
; bat_xor: XOR the 16 x 8 sprite at DE onto the screen at byte column BAT_COL,
; playfield line HL.  Returns C = the device's hit latch: non-zero means the
; bat overlapped something (sprite AND screen, before each byte changed).
; -----------------------------------------------------------------------------
bat_xor: ld c,DEV
        ld b,DV_HIT         ; clear the hit latch
        out (c),a
        push de
        ld de,PF_TOP
        add hl,de
        call bline
        pop de
        ld a,BAT_COL
        ld b,DV_BCOL
        out (c),a
        ld l,8
bx_lp:  ld b,DV_BXOR
        ld a,(de)           ; left byte
        out (c),a
        inc de
        ld a,(de)           ; right byte
        out (c),a
        inc de
        ld b,DV_NEXT
        out (c),a
        dec l
        jr nz,bx_lp
        ld b,DV_HIT
        in a,(c)
        ld c,a
        ret

; -----------------------------------------------------------------------------
; bat_attr: set the attribute E in the cells the bat covers when its top is at
; playfield line HL: two columns, in the character row of its top line and of
; its bottom line (the same row when it is aligned).
; -----------------------------------------------------------------------------
bat_attr:
        push hl
        ld bc,PF_TOP
        add hl,bc
        call ba_row         ; row of the top line
        pop hl
        ld bc,PF_TOP+7
        add hl,bc           ; row of the bottom line
ba_row: srl h               ; HL = screen line -> L = row
        rr l
        srl h
        rr l
        srl h
        rr l
        ld c,DEV
        ld b,DV_ROW
        out (c),l
        ld a,BAT_COL
        ld b,DV_COL
        out (c),a
        ld b,DV_CELL
        out (c),e
        inc a
        ld b,DV_COL
        out (c),a
        ld b,DV_CELL
        out (c),e
        ret

; ---- data -------------------------------------------------------------------
; Sprites, ground and pipe patterns: the same as the Spectrum version's.
spr_up:                         ; wings up: 16 x 8 pixels, 2 bytes a line
        defb $04,$20          ;      #    #
        defb $87,$E1          ; #    ######    #
        defb $C5,$A3          ; ##   # ## #   ##
        defb $EF,$F7          ; ### ######## ###
        defb $7D,$BE          ;  ##### ## #####
        defb $3E,$7C          ;   #####  #####
        defb $0F,$F0          ;     ########
        defb $02,$40          ;       #  #
spr_dn:                         ; wings down
        defb $04,$20          ;      #    #
        defb $07,$E0          ;      ######
        defb $05,$A0          ;      # ## #
        defb $7F,$FE          ;  ##############
        defb $FF,$FF          ; ################
        defb $ED,$B7          ; ### ## ## ## ###
        defb $CE,$73          ; ##  ###  ###  ##
        defb $83,$C1          ; #     ####     #
gpat:                           ; ground: 8 lines x 4 nibbles (one 16-pixel repeat)
        defb $F,$F,$F,$F      ; ################
        defb $8,$3,$8,$3      ; #     ###     ##
        defb $0,$E,$0,$E      ;     ###     ###
        defb $3,$8,$3,$8      ;   ###     ###
        defb $E,$0,$E,$0      ; ###     ###
        defb $8,$3,$8,$3      ; #     ###     ##
        defb $0,$E,$0,$E      ;     ###     ###
        defb $8,$8,$8,$8      ; #   #   #   #
ginit:                          ; the same pattern as whole bytes, for the first fill
        defb $FF,$FF
        defb $83,$83
        defb $0E,$0E
        defb $38,$38
        defb $E0,$E0
        defb $83,$83
        defb $0E,$0E
        defb $88,$88
body_e:  defb $0F,$BF,$FF,$E0,$00   ; |    ##### #################             |  x even
body_o:  defb $00,$FB,$FF,$FE,$00   ; |        ##### #################         |  x odd
cap_e:  defb $7F,$BF,$FF,$FE,$00   ; | ######## #####################         |  x even
cap_o:  defb $07,$FB,$FF,$FF,$E0   ; |     ######## #####################     |  x odd

code_end:
