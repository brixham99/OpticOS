; =====================================================================
; OpticBASIC 128 extension ROM: screen modes (phase 1)
; (c) 2026 Optica Technology Design.  Clean-room, for a 128K Spectrum with
; OpticOS (branch opticos128-screen) in ROM slot 0 and this ROM in slot 1.
;
;   SCREEN 0        the ordinary display (cleared, as CLS)
;   SCREEN 1        64 x 48 chunky pixels: 2 x 2 chunky pixels share one
;                   attribute cell (two colours per cell)
;   SCREEN 2        32 x 24 cells, each one colour (attribute only, no clash)
;   SCREEN FLIP     double buffering: draw the changes on the hidden screen,
;                   wait for the frame, show it.  The first FLIP turns it on;
;                   SCREEN n turns it off (every PLOT / CLS then shows at once)
;   PLOT x,y[,c]    in SCREEN 1/2: colour c 0-15, or INK + 8 * BRIGHT
;   CLS             in SCREEN 1/2: every pixel PAPER + 8 * BRIGHT
;   POINT(x,y)      colour 0-15 in SCREEN 1/2; 1/0 (ink pixel) in SCREEN 0
; Origin bottom left, as PLOT.  Any return to the console (end of a program,
; an error, BREAK) gives back SCREEN 0 (OpticOS's console entry).
;
; How OpticOS gets here: ext_hook (a statement name that is not a PROC),
; xgo with E = 0 PLOT / 1 CLS / 2 a name used as a function.  Calls into
; OpticOS go through a 17-byte RAM trampoline in HDRBUF (only used by tape
; commands), which comes back through x_rst's OUT and our RET at x_rst+5.
;
; RAM: everything lives in bank 7 above its screen, paged in at $C000 only
; inside this ROM (interrupts off, own stack), so OpticOS's own memory in
; bank 0 is untouched:
;   $C000-$DAFF  screen 1          $DC00-$E7FF  framebuffer (cell-major)
;   $E800-$EAFF  dirty flags       $EB00/$F200  dirty lists, screen 5 / 7
;   $F900-$F9FF  variables         $FA00-$FFFF  stack
; Framebuffer: cell (cx, cy) has its four chunky pixels in pages
; FBP + 4 * (cy >> 3) + k (k = 0 TL, 1 TR, 2 BL, 3 BR) at low byte
; (cy & 7) << 5 | cx, which is also the cell's screen low byte.  SCREEN 2
; uses page k = 0 only.
; =====================================================================
        include "os.inc"        ; OpticOS addresses (from build/opticos.sym)

CH_ADD  equ $5C5D
ATTR_P  equ $5C8D
SMODE   equ $5CA0
VID     equ $5BE0
HDRBUF  equ $5B50
TRAMP   equ HDRBUF
TR_N0   equ TRAMP+2
TR_T    equ TRAMP+10
TR_N1   equ TRAMP+13

FBP     equ $DC
DFLP    equ $E8
LIST0   equ $EB00
LIST1   equ $F200
VARS    equ $F900
lp0     equ VARS                ; list ends
lp1     equ VARS+2
b7sp    equ VARS+4              ; OpticOS's SP while we are in bank 7
FRAMES  equ $5C78
pcol    equ VARS+6              ; colour for PLOT / CLS
rbase   equ VARS+7              ; render: screen base ($40 / $C0)
rmask   equ VARS+8              ; render: dirty bit (1 / 2)
mode    equ VARS+9              ; 1 or 2
B7STK   equ $0000               ; top of bank 7

        org $0000               ; RST 0 while this ROM is paged: boot OpticOS
        di
        ld bc,$7FFD
        xor a
        ld de,$FFFF
        jp OS_boot-2
        org $0038               ; IM 1 while this ROM is paged (SCREEN FLIP's HALT):
        push af                 ; FRAMES still counts (no keyboard scan here)
        push hl
        ld hl,FRAMES
        inc (hl)
        jr nz,im_x
        inc l
        inc (hl)
        jr nz,im_x
        inc l
        inc (hl)
im_x:   pop hl
        pop af
        ei
        ret
        org OS_boot-2
        out (c),a
        org OS_ext_back-2
ret_os: out (c),a               ; back to OpticOS: next fetch is its ext_back
        jp ext_stmt
        org OS_xgo+10
ret_x:  out (c),a               ; back to OpticOS at x_back (RET)
        jp ext_x
        org OS_x_rst+5
        ret                     ; the way back from a call into OpticOS

        org $1000
; ---------------------------------------------------------------- entry
; ext_stmt: a statement name that is not a PROC
ext_stmt:
        ld hl,(CH_ADD)          ; $01 type hash length name
        inc hl
        inc hl
        inc hl
        ld de,n_screen
        call namecmp
        jr z,es_scr
        ld a,(SMODE)            ; not ours: OpticOS's "No such PROC or FN"
        and 8
        ld bc,$7FFD
        scf
        jp ret_os
es_scr: call tr_set
        call far
        dw OS_id_skip           ; step over SCREEN
        ld hl,(CH_ADD)
        ld a,(hl)
        cp 1
        jr nz,es_n
        inc hl
        inc hl
        inc hl
        ld de,n_flip
        call namecmp
        jp nz,os_syn
        call far
        dw OS_id_skip
        call flip
        jp back_ok
es_n:   call far                ; SCREEN n
        dw OS_ev_expr
        call far
        dw OS_pop_int
        ld a,d
        or a
        jp nz,os_rng
        ld a,e
        cp 3
        jp nc,os_rng
        or a
        jr nz,es_12
        xor a                   ; SCREEN 0: screen 5, then OpticOS's CLS
        ld (SMODE),a
        call tr_set
        call far
        dw OS_CLS
        jp back_ok
es_12:  ld (SMODE),a            ; SCREEN 1 / 2: screen 5 on show, PLOT shows at once
        call tr_set
        call paper_col
        ld d,a
        call b7_in
        ld a,(SMODE)
        ld (mode),a
        cp 2
        call z,clr_bits         ; SCREEN 2: blank bitmaps on both screens
        call fill
        call render0
        call b7_out
back_ok: or a                   ; NC: done
back:   ld a,(SMODE)            ; ROM 0, RAM bank 0, the screen on show
        and 8
        ld bc,$7FFD
        jp ret_os

; ext_x: E = 0 PLOT, 1 CLS (SCREEN 1/2 only), 2 a name used as a function
ext_x:  ld a,e
        cp 2
        jp z,x_fn
        call tr_set
        ld a,e
        or a
        jr nz,x_cls
        call far                ; PLOT x, y [, c]
        dw OS_ev_expr
        call far
        dw OS_pop_int
        push de
        ld a,','
        call expect
        call far
        dw OS_ev_expr
        call far
        dw OS_pop_int
        push de
        call ink_col
        ld hl,(CH_ADD)
        ld a,(hl)
        cp ','
        jr nz,xp_c
        inc hl
        ld (CH_ADD),hl
        call far
        dw OS_ev_expr
        call far
        dw OS_pop_int
        ld a,d
        or a
        jp nz,os_rng
        ld a,e
        cp 16
        jp nc,os_rng
        ld h,e
        jr xp_d
xp_c:   ld h,a                  ; H = colour
xp_d:   pop de                  ; y
        pop bc                  ; x
        push hl
        call xy_chk             ; -> B = x, C = row from the top (or error)
        pop de                  ; D = colour
        call b7_in
        call plot
        call auto_show
        call b7_out
        jp back_ok
x_cls:  call paper_col          ; CLS
        ld d,a
        call b7_in
        call fill
        call auto_show
        call b7_out
        jp back_ok

; x_fn: POINT(x, y)?  VID = $01 type hash length name
x_fn:   ld hl,(VID)
        inc hl
        inc hl
        inc hl
        ld de,n_point
        call namecmp
        jr z,xf_pt
        ld a,(SMODE)            ; not ours: OpticOS's "No such variable"
        and 8
        or $10
        ld bc,$7FFD
        jp ret_x
xf_pt:  call tr_set
        ld a,'('
        call expect
        call far
        dw OS_ev_expr
        call far
        dw OS_pop_int
        push de
        ld a,','
        call expect
        call far
        dw OS_ev_expr
        call far
        dw OS_pop_int
        push de
        ld a,')'
        call expect
        pop de
        pop bc
        ld a,(SMODE)
        and 3
        jr nz,xf_c
        ld a,b                  ; SCREEN 0: the pixel at (x, y), 256 x 192
        or d
        jp nz,os_rng
        ld a,e
        cp 192
        jp nc,os_rng
        ld a,191
        sub e
        ld b,a                  ; B = row, C = x
        call pix0               ; HL = byte, A = mask
        and (hl)
        ld e,0
        jr z,xf_p
        inc e
        jr xf_p
xf_c:   call xy_chk
        call pix_addr           ; HL = framebuffer byte (bank 7)
        di
        ld a,(SMODE)
        and 8
        ld d,a
        or $17
        ld bc,$7FFD
        out (c),a
        ld e,(hl)
        ld a,d
        or $10
        out (c),a               ; (bank 0, ROM 1 again)
        ei
xf_p:   ld d,0
        call far
        dw OS_push_u
        pop hl                  ; drop xfn's return (it would raise the error)
        jp back_ok

; ---------------------------------------------------------------- helpers
; tr_set: the RAM trampoline, for the screen on show now
tr_set: push hl
        push de
        push bc
        ld hl,tr_code
        ld de,TRAMP
        ld bc,17
        ldir
        ld a,(SMODE)
        and 8
        ld (TR_N0),a
        or $10
        ld (TR_N1),a
        pop bc
        pop de
        pop hl
        ret
tr_code: push af                ; ROM 0 (same RAM bank and screen) ...
        ld a,0
        ld bc,$7FFD
        out (c),a
        pop af
        call 0                  ; ... call ...
        ld a,0
        jp OS_x_rst             ; ... and ROM 1 back via OpticOS's OUT and our RET
; far: call the OpticOS routine whose address follows the CALL (A, DE, HL
; and the flags pass both ways, except that A is lost on the way back)
far:    ex (sp),hl
        push de
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        ld (TR_T),de
        pop de
        ex (sp),hl
        jp TRAMP
os_rng: call far
        dw OS_err_rng
os_syn: call far
        dw OS_err_syn
; expect: A = the token that must come next
expect: ld hl,(CH_ADD)
        cp (hl)
        jp nz,os_syn
        inc hl
        ld (CH_ADD),hl
        ret
; namecmp: HL = identifier length byte, DE = length-prefixed name; Z if equal
namecmp: ld a,(de)
        ld b,a
        inc b
nc_lp:  ld a,(de)
        cp (hl)
        ret nz
        inc de
        inc hl
        djnz nc_lp
        ret
; ink_col / paper_col: the colour from ATTR_P (+ 8 for BRIGHT) -> pc_hold
ink_col: ld a,(ATTR_P)
        ld b,a
        and 7
        jr col_b
paper_col: ld a,(ATTR_P)
        ld b,a
        rrca
        rrca
        rrca
        and 7
col_b:  bit 6,b
        jr z,col_s
        or 8
col_s:  ret
; xy_chk: BC = x, DE = y -> B = x, C = row from the top; range by mode
xy_chk: ld a,b
        or d
        jp nz,os_rng
        ld a,(SMODE)
        and 3
        cp 1
        ld a,64
        ld h,48
        jr z,xy_1
        ld a,32
        ld h,24
xy_1:   dec a
        cp c
        jp c,os_rng
        ld a,h
        dec a
        cp e
        jp c,os_rng
        sub e
        ld b,c
        ld c,a
        ret
; pix0: C = x, B = row (0-191) -> HL = screen 5 byte, A = the pixel's mask
pix0:   ld a,b
        and $C0
        rrca
        rrca
        rrca
        or $40
        ld h,a
        ld a,b
        and 7
        or h
        ld h,a
        ld a,b
        and $38
        rlca
        rlca
        ld l,a
        ld a,c
        rrca
        rrca
        rrca
        and $1F
        or l
        ld l,a
        ld a,c
        and 7
        ld b,a
        ld a,$80
        ret z
p0_l:   rrca
        djnz p0_l
        ret
; pix_addr: B = x, C = row -> HL = framebuffer byte (mode 1: pixel, 2: cell)
pix_addr:
        ld a,(SMODE)
        and 3
        cp 1
        jr z,pa_1
        ld a,c                  ; SCREEN 2: page FBP + 4 (cy >> 3), low (cy & 7) << 5 | cx
        and $18
        rrca
        add a,FBP
        ld h,a
        ld a,c
        and 7
        rrca
        rrca
        rrca
        or b
        ld l,a
        ret
pa_1:   ld a,c                  ; SCREEN 1: low ((y >> 1) & 7) << 5 | x >> 1
        and $0E
        rlca
        rlca
        rlca
        rlca
        ld l,a
        ld a,b
        srl a
        or l
        ld l,a
        ld a,c                  ; page FBP + 4 (y >> 4) + 2 (y & 1) + (x & 1)
        and $30
        rrca
        rrca
        ld h,a
        ld a,c
        and 1
        add a,a
        or h
        ld h,a
        ld a,b
        and 1
        or h
        add a,FBP
        ld h,a
        ret
; ---------------------------------------------------------------- bank 7
; b7_in: bank 7 at $C000, interrupts off, our stack (the caller's return kept)
b7_in:  pop hl                  ; (D = colour for PLOT / CLS; BC, DE kept)
        di
        push bc
        pop ix
        ld a,(SMODE)
        and 8
        or $17
        ld bc,$7FFD
        out (c),a
        ld (b7sp),sp
        ld sp,B7STK
        ld a,d
        ld (pcol),a
        push ix
        pop bc
        jp (hl)
b7_out: pop hl
        ld sp,(b7sp)
        ld a,(SMODE)
        and 8
        or $10
        ld bc,$7FFD
        out (c),a
        ei
        jp (hl)
; plot: B = x, C = row, pcol = colour; mark the cell if it changed
plot:   call pix_addr
        ld a,(pcol)
        cp (hl)
        ret z
        ld (hl),a
        ld a,h                  ; cell: TL page, low
        and $FC
        ld d,a
        ld e,l
; mark: D = TL page, E = low; put the cell on both lists (once each)
mark:   ld a,d
        sub FBP
        rrca
        rrca
        add a,DFLP
        ld h,a
        ld l,e
        ld a,(hl)
        bit 0,a
        jr nz,mk_1
        set 0,(hl)
        push hl
        ld hl,(lp0)
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ld (lp0),hl
        pop hl
mk_1:   bit 1,(hl)
        ret nz
        set 1,(hl)
        ld hl,(lp1)
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ld (lp1),hl
        ret
; fill: every pixel = pcol, every cell on both lists
fill:   ld hl,FBP*256
        ld de,FBP*256+1
        ld bc,3071
        ld a,(pcol)
        ld (hl),a
        ldir
        ld hl,DFLP*256          ; flags: listed on both
        ld de,DFLP*256+1
        ld bc,767
        ld (hl),3
        ldir
        ld hl,LIST0
        ld de,LIST1
        ld b,FBP
fl_t:   ld c,0
fl_l:   ld (hl),c
        inc hl
        ld (hl),b
        inc hl
        ex de,hl
        ld (hl),c
        inc hl
        ld (hl),b
        inc hl
        ex de,hl
        inc c
        jr nz,fl_l
        ld a,b
        add a,4
        ld b,a
        cp FBP+12
        jr nz,fl_t
        ld (lp0),hl
        ld (lp1),de
        ret
; clr_bits: zero both screens' bitmaps (SCREEN 2)
clr_bits: ld hl,$4000
        ld de,$4001
        ld bc,6143
        ld (hl),0
        ldir
        ld hl,$C000
        ld de,$C001
        ld bc,6143
        ld (hl),0
        ldir
        ret
; auto_show: unless SCREEN FLIP is on, draw the changes on screen 5 now
auto_show: ld a,(SMODE)
        rla
        ret c
render0: ld a,$40
        ld (rbase),a
        ld a,1
        ld (rmask),a
        ld hl,(lp0)
        ld de,LIST0
        ld (lp0),de
        jr render
render1: ld a,$C0
        ld (rbase),a
        ld a,2
        ld (rmask),a
        ld hl,(lp1)
        ld de,LIST1
        ld (lp1),de
; render: draw the cells DE .. HL-1 on the screen at rbase; clear their bit
render: ld (rd_end),hl
rd_lp:  ld hl,(rd_end)
        or a
        sbc hl,de
        ret z
        ld a,(de)
        ld l,a                  ; low
        inc de
        ld a,(de)
        ld h,a                  ; TL page
        inc de
        push de
        push hl
        ld a,h                  ; clear this screen's bit
        sub FBP
        rrca
        rrca
        add a,DFLP
        ld d,a
        ld e,l
        ld a,(rmask)
        cpl
        ex de,hl
        and (hl)
        ld (hl),a
        ex de,hl
        ld a,(mode)
        cp 2
        jp z,rd_m2
        ld d,(hl)               ; p0 TL
        inc h
        ld e,(hl)               ; p1 TR
        inc h
        ld b,(hl)               ; p2 BL
        inc h
        ld c,(hl)               ; p3 BR
        ld a,d                  ; H = ink (commonest), L = paper (next)
        cp e
        jr nz,s_g1
        cp b
        jr nz,s_pb
        cp c
        jr nz,s_pc
        ld h,d                  ; all four the same
        ld l,d
        ld de,$FFFF
        jr s_at
s_pb:   ld h,d
        ld l,b
        jr s_pat
s_pc:   ld h,d
        ld l,c
        jr s_pat
s_g1:   cp b
        jr z,s_pe
        cp c
        jr z,s_pe
        ld a,e
        cp b
        jr z,s_a1
        cp c
        jr z,s_a1
        ld a,b
        cp c
        jr z,s_a2
s_pe:   ld h,d
        ld l,e
        jr s_pat
s_a1:   ld h,e
        ld l,d
        jr s_pat
s_a2:   ld h,b
        ld l,d
s_pat:  ld a,d                  ; patterns: ink where a pixel = H
        xor h
        sub 1
        sbc a,a
        and $F0
        ld d,a
        ld a,e
        xor h
        sub 1
        sbc a,a
        and $0F
        or d
        ld d,a
        ld a,b
        xor h
        sub 1
        sbc a,a
        and $F0
        ld e,a
        ld a,c
        xor h
        sub 1
        sbc a,a
        and $0F
        or e
        ld e,a
s_at:   ld a,h                  ; C = TA[ink << 4 | paper]
        add a,a
        add a,a
        add a,a
        add a,a
        or l
        ld l,a
        ld h,TA/256
        ld c,(hl)
        pop hl                  ; H = TL page, L = screen low byte
        ld a,h
        sub FBP                 ; 4 * third
        add a,a
        ld b,a                  ; 8 * third
        ld a,(rbase)
        add a,b
        ld h,a
        ld (hl),d
        inc h
        ld (hl),d
        inc h
        ld (hl),d
        inc h
        ld (hl),d
        inc h
        ld (hl),e
        inc h
        ld (hl),e
        inc h
        ld (hl),e
        inc h
        ld (hl),e
        ld a,b
        rrca
        rrca
        rrca
        ld b,a
        ld a,(rbase)
        add a,$18
        add a,b
        ld h,a
        ld (hl),c
        pop de
        jp rd_lp
rd_m2:  ld e,(hl)               ; SCREEN 2: one colour per cell, attribute only
        ld d,TA2/256
        ld a,(de)
        ld c,a
        pop hl                  ; H = TL page, L = screen low byte
        ld a,h
        sub FBP
        rrca
        rrca                    ; third
        ld b,a
        ld a,(rbase)
        add a,$18
        add a,b
        ld h,a
        ld (hl),c
        pop de
        jp rd_lp
; flip: SCREEN FLIP
flip:   ld a,(SMODE)
        and 3
        jp z,os_rng
        call b7_in
        ld a,(SMODE)
        or $80
        ld (SMODE),a
        ld a,(SMODE)
        bit 3,a
        jr nz,fp_5
        call render1            ; screen 5 on show: draw on bank 7's
        jr fp_w
fp_5:   call render0
fp_w:   ei
        halt
        di
        ld a,(SMODE)
        xor 8
        ld (SMODE),a
        and 8
        or $17
        ld bc,$7FFD
        out (c),a
        call b7_out
        ret
rd_end  equ VARS+10

n_screen: db 6, "screen"
n_flip: db 4, "flip"
n_point: db 5, "point"

        org $3E00
TA2:    ; SCREEN 2: colour -> attribute (ink = paper, BRIGHT)
        include "ta2.inc"
        org $3F00
TA:     ; SCREEN 1: [ink << 4 | paper] -> attribute (BRIGHT from the ink unless black)
        include "ta.inc"
