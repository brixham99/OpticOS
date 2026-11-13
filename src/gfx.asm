; gfx.asm - phase 5: PLOT, DRAW [TO].
; Graphics: 256 x 192 pixels, origin bottom left; COORDS = last point.
m_gfx_s:
; PLOT x, y
st_plot: call ev_u8
        push de
        call argn
        pop bc                  ; C = x
        ld b,e                  ; B = y
; plot: pixel (C, B) -> COORDS; INVERSE resets, OVER flips; the cell
; takes the temporary attribute
plot:   ld (COORDS),bc
        ld a,191
        sub b
        jr c,err_rng
        ld b,a
        call pa_ok              ; HL = byte, A = x AND 7
        ld b,a
        inc b
        ld a,1
pl_m:   rrca
        djnz pl_m
        ld b,a                  ; the pixel's bit
        ld a,(P_FLAG)
        ld c,(hl)
        bit 2,a
        jr nz,pl_i
        rra
        ld a,b
        jr c,pl_x
        or c
        jr pl_s
pl_x:   xor c
        jr pl_s
pl_i:   ld a,b
        cpl
        and c
pl_s:   ld (hl),a
        ld a,h                  ; the attribute cell
        rrca
        rrca
        rrca
        and 3
        or $58
        ld h,a
        jp attr_set             ; colours, with INK 8 / PAPER 8 etc. kept
err_rng: rst 8
        defb ERR_RANGE
; DRAW dx, dy (relative) / DRAW TO x, y
st_draw: rst $18
        cp T_TO
        jr z,dr_to
        rst $30                 ; dx
        push de
        ld a,','
        call expect
        rst $30                 ; dy
        pop hl
        ld bc,(COORDS)
        push bc
        ld b,0
        add hl,bc               ; x0 + dx
        ld a,h
        or a
        jr nz,err_rng
        ex de,hl
        pop bc
        ld c,b
        ld b,0
        add hl,bc               ; y0 + dy
        ld a,h
        or a
        jr nz,err_rng
        ld b,l
        ld c,e
        jr ln_chk
dr_to:  rst $20
        call ev_u8
        push de
        call argn
        pop bc
        ld b,e
ln_chk: ld a,b
        cp 192
        jr nc,err_rng
; ln_to: a line from COORDS to (C, B), stepping along the longer axis.
; DIMB: minor step (2), m, n, major step (2)
ln_to:  ld hl,(COORDS)          ; L = x0, H = y0
        ld a,c
        sub l
        ld c,1
        jr nc,ln_1
        neg
        ld c,-1
ln_1:   ld e,a                  ; E = |dx|, C = x step
        ld a,b
        sub h
        ld b,1
        jr nc,ln_2
        neg
        ld b,-1
ln_2:   ld d,a                  ; D = |dy|, B = y step
        cp e
        jr nc,ln_y
        ld h,0                  ; x major
        ld l,c
        ld c,0
        ld a,e
        ld e,d
        ld d,a
        jr ln_go
ln_y:   ld h,b                  ; y major
        ld l,0
        ld b,0
ln_go:  ld (DIMB+4),hl          ; major step (H = y, L = x)
        ld (DIMB),bc            ; minor step
        ld (DIMB+2),de          ; m, n
        ld a,d
        or a
        ret z
        ld b,d
        srl a
        ld c,a                  ; error term = n / 2
ln_lp:  push bc
        ld a,c
        ld hl,DIMB+2
        add a,(hl)
        inc hl
        jr c,ln_mn
        cp (hl)
        jr c,ln_mj
ln_mn:  sub (hl)
        ld de,(DIMB)
        call c_add
ln_mj:  pop bc
        ld c,a
        push bc
        ld de,(DIMB+4)
        call c_add
        call plot
        pop bc
        djnz ln_lp
        ret
; c_add: COORDS + step E (x), D (y) -> BC; A kept
c_add:  ld bc,(COORDS)
        push af
        ld a,c
        add a,e
        ld c,a
        ld a,b
        add a,d
        ld b,a
        ld (COORDS),bc
        pop af
        ret

m_gfx_e:
