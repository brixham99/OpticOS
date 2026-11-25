; 32-column printer (xgo E=4, D = character) and hi-res CIRCLE backend.
; Font: fonts/optic8x8.bin (96 glyphs, codes 32-127, 8 bytes each).

; x_txt32: last text mode from OMODE, show screen 5, print.
; BC and HL were left for us to keep; DE is saved in the main ROM's xt_far.
x_txt32:
        push hl
        push bc
        call tr_set
        xor a
        ld (SMODE),a            ; both text modes have SMODE 0 (FLIP off)
        ld a,$10                ; ROM 1, bank 0, screen 5
        ld bc,$7FFD
        out (c),a
        ld a,(OMODE)
        and 32
        ld a,d
        jr nz,p32_go
        call sfar               ; last mode was 64-col
        dw OS_print_a
        jr p32_x
p32_go: call pr32
p32_x:  pop bc
        pop hl
        jp back_ok

; pr32: 32-column print of A at S_POSN (column 0-31, row 0-23).
pr32:   ld c,a
        ld a,(PR_CTRL)
        or a
        jr nz,p32_par
        ld a,c
        cp 32
        jr c,p32_ctl
        cp 128
        jr c,p32_gl
        ld a,'?'
p32_gl: push af
        ld a,(S_POSN)
        cp 32
        call nc,p32_nl
        pop af
        call draw8
        ld hl,(S_POSN)
        call attr8
        call aset
        ld hl,S_POSN
        inc (hl)
        ret

p32_ctl:
        cp 13
        jp z,p32_nl
        cp 8
        jr z,p32_bs
        cp 6
        jr z,p32_cm
        cp 16
        ret c
        cp 24
        ret nc
        ld (PR_CTRL),a
        ld a,$FF
        ld (PR_P1),a
        ret

p32_par:                        ; A = pending code, C = parameter
        ld b,a
        cp 22
        jr nc,p32_two
        xor a
        ld (PR_CTRL),a
        ld a,c
        ld c,b
        ld hl,ATTR_T
        call sfar
        dw OS_set_colour
        ret
p32_two:
        ld a,(PR_P1)
        inc a
        jr nz,p32_tw2
        ld a,c
        ld (PR_P1),a
        ret
p32_tw2:
        xor a
        ld (PR_CTRL),a
        ld a,b
        cp 23
        ld a,(PR_P1)
        jr z,p32_tab
        cp 24
        jr nc,p32_oos
        ld h,a
        ld a,c
        cp 32
        jr nc,p32_oos
        ld l,a
        ld (S_POSN),hl
        ret
p32_oos: call sfar
        dw OS_po_oos
p32_tab:
        and 31
        ld hl,S_POSN
        cp (hl)
        push af
        call c,p32_nl
        pop af
        ld (S_POSN),a
        ret

p32_bs: ld hl,(S_POSN)
        ld a,l
        or a
        jr z,p32_bs2
        dec l
        jr p32_sto
p32_bs2: ld a,h
        or a
        ret z
        dec h
        ld l,31
p32_sto: ld (S_POSN),hl
        ret

p32_cm: ld a,(S_POSN)
        add a,16
        and $F0
        cp 32
        jr nc,p32_nl
        ld (S_POSN),a
        ret

p32_nl: inc (iy+NLCT-ERR_NR)
        ld hl,(S_POSN)
        ld l,0
        inc h
        ld a,h
        cp 24
        jr c,p32_ok
        dec h
        push hl
        call sfar
        dw OS_scroll
        pop hl
p32_ok: ld (S_POSN),hl
        ret

; draw8: A = 32..127 at S_POSN, 8 x 8, INVERSE / OVER from P_FLAG.
draw8:  sub 32
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        ld de,font8
        add hl,de
        ex de,hl                ; DE = glyph
        ld a,(P_FLAG)
        ld c,a                  ; C = P_FLAG
        ld hl,(S_POSN)
        call pos8
        ld b,8
        bit 0,c
        jr nz,d8_ov
d8_nm:  ld a,(de)
        bit 2,c
        jr z,d8_n1
        cpl
d8_n1:  ld (hl),a
        inc de
        inc h
        djnz d8_nm
        ret
d8_ov:  ld a,(de)
        bit 2,c
        jr z,d8_o1
        cpl
d8_o1:  xor (hl)
        ld (hl),a
        inc de
        inc h
        djnz d8_ov
        ret

; pos8: H = row 0-23, L = column 0-31 -> HL = top screen byte
pos8:   ld a,h
        and 7
        rrca
        rrca
        rrca
        or l
        ld l,a
        ld a,h
        and $18
        or $40
        ld h,a
        ret

; attr8: H = row, L = column 0-31 -> HL = attribute byte
attr8:  ld a,h
        rrca
        rrca
        rrca
        ld h,a
        and $E0
        or l
        ld l,a
        ld a,h
        and 3
        or $58
        ld h,a
        ret

; aset: ATTR_T into (HL), MASK_T bits kept (same as main-ROM attr_set)
aset:   push bc
        ld bc,(ATTR_T)
        ld a,c
        xor (hl)
        and b
        xor c
        ld (hl),a
        pop bc
        ret

; plot_hi: B = x (0-255), C = row (0-191), already clipped.
; No CEXPL: like PLOT (OVER / INVERSE, ATTR_T / MASK_T).
; CEXPL set: ink pixel unless INVERSE; write INK+BRIGHT from pcol, leave PAPER.
plot_hi:
        push bc
        ld a,c
        ld c,b                  ; C = x
        ld b,a                  ; B = row
        call pix0               ; HL = byte, A = mask (B clobbered)
        ld b,a
        pop de                  ; keep nothing; D/E scratch
        ld a,(CEXPL)
        or a
        jr nz,ph_ex
        ld a,(P_FLAG)
        ld c,(hl)
        bit 2,a
        jr nz,ph_i
        rra
        ld a,b
        jr c,ph_x
        or c
        jr ph_s
ph_x:   xor c
        jr ph_s
ph_i:   ld a,b
        cpl
        and c
ph_s:   ld (hl),a
        ld a,h
        rrca
        rrca
        rrca
        and 3
        or $58
        ld h,a
        jp aset
ph_ex:  ld a,(P_FLAG)
        bit 2,a
        ld a,b
        jr nz,ph_ei
        or (hl)
        jr ph_es
ph_ei:  cpl
        and (hl)
ph_es:  ld (hl),a
        ld a,h
        rrca
        rrca
        rrca
        and 3
        or $58
        ld h,a
        ld a,(pcol)
        and 15
        ld b,a
        and 7
        ld c,a
        ld a,(hl)
        and $B8                 ; keep FLASH + PAPER
        or c
        bit 3,b
        jr z,ph_eb
        or $40
ph_eb:  ld (hl),a
        ret

; x_ed: editor width (E=5).  D = 0 lin_pos, 1 pos_lin, 2 cur_set.
; Called from main ROM (E=5) when OMODE=32.
x_ed:   ld a,d
        or a
        jr z,ed_lin
        dec a
        jr z,ed_pos
        ; cur_set: A was saved?  The hook will need to pass the new state
        ; in A or a sysvar.  For now treat A as already stored in CUR_VIS
        ; by the hook; draw an 8-pixel cursor at S_POSN.
        jp ed_cur

; lin_pos: HL = row*32 + column -> S_POSN (column 0-31)
ed_lin: ld a,l
        and 31
        ; HL was row*32+col; recover row: HL >> 5, but we only have the
        ; packed form.  Main-ROM lin_pos does: and mask; add hl,hl; add hl,hl;
        ; ld l,a  so the incoming HL is already in the pos_lin index form
        ; (row*width+col).  After two add hl,hl, H = row when width=64
        ; (because row*64+col << 2 = row<<8 + col<<2, L overwritten).
        ; For width 32: four add hl,hl would be needed to get row in H?
        ; row*32+col << 3 = row<<8 + col<<3.  Three shifts.
        add hl,hl
        add hl,hl
        add hl,hl
        ld l,a
        ld (S_POSN),hl
        jp back_ok

; pos_lin: S_POSN -> HL = row*32 + column
ed_pos: ld hl,(S_POSN)
        ld a,l
        ld l,h
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl               ; row*32
        or l
        ld l,a
        ; return HL to the caller of lin_pos/pos_lin.  back_ok keeps HL.
        jp back_ok

ed_cur: ld hl,(S_POSN)
        ld a,l
        cp 32
        jp nc,back_ok
        call pos8
        ld b,8
        ld c,$FF
ed_c1:  ld a,(hl)
        xor c
        ld (hl),a
        inc h
        djnz ed_c1
        jp back_ok

font8:  incbin "../fonts/optic8x8.bin"
