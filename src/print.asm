; print.asm - 64-column output (channels K and S) using the 4x8 font.
; PR_OUT must stay in page $09 so that POKE 23739,111 (low byte of the S
; channel output address) turns it into the RET at $096F.
m_prt_s:
PR_OUT:
pr_out: ld c,a
        ld a,(PR_CTRL)
        or a
        jr nz,po_param
        ld a,c
        cp 32
        jr c,po_ctrl
        cp 128
        jr c,po_glyph
        ld a,'?'                ; block graphics and UDGs arrive in phase 3
po_glyph:
        push af
        ld a,(S_POSN)
        cp 64
        call nc,pr_nl           ; wrap a full line before printing
        pop af
        call draw_glyph
        ld hl,(S_POSN)
        call attr_addr
        ld a,(MASK_T)
        ld c,a
        ld a,(ATTR_T)
        ld b,a
        xor (hl)
        and c
        xor b                   ; ATTR_T, keeping MASK_T bits from the screen
        ld (hl),a
        ld hl,S_POSN
        inc (hl)
        ret

po_ctrl:
        cp 13
        jp z,pr_nl
        cp 8
        jr z,po_bs
        cp 6
        jr z,po_comma
        cp 16
        ret c
        cp 24
        ret nc
        ld (PR_CTRL),a          ; INK..OVER take one byte, AT and TAB two
        ld a,$FF
        ld (PR_P1),a
        ret

po_param:                       ; A = pending code, C = parameter
        ld b,a
        cp 22
        jr nc,po_two
        xor a
        ld (PR_CTRL),a
        ld a,c
        ld c,b
        ld hl,ATTR_T
        jp set_colour
po_two: ld a,(PR_P1)
        inc a
        jr nz,po_two2
        ld a,c
        ld (PR_P1),a
        ret
po_two2:
        xor a
        ld (PR_CTRL),a
        ld a,b
        cp 23
        ld a,(PR_P1)
        jr z,po_tab
        cp 24
        jr nc,po_oos
        ld h,a
        ld a,c
        cp 64
        jr nc,po_oos
        ld l,a
        ld (S_POSN),hl
        ret
po_oos: rst 8
        defb ERR_SCREEN
po_tab: and 63
        ld hl,S_POSN
        cp (hl)
        push af
        call c,pr_nl
        pop af
        ld (S_POSN),a
        ret

po_bs:  ld hl,(S_POSN)          ; cursor left, back up a row at column 0
        ld a,l
        or a
        jr z,po_bs2
        dec l
        jr po_sto
po_bs2: ld a,h
        or a
        ret z
        dec h
        ld l,63
po_sto: ld (S_POSN),hl
        ret

po_comma:
        ld a,(S_POSN)
        add a,16
        and $F0
        cp 64
        jr nc,pr_nl
        ld (S_POSN),a
        ret

pr_nl:  ld hl,(S_POSN)
        ld l,0
        inc h
        ld a,h
        cp 24
        jr c,pn_ok
        dec h
        push hl
        call scroll
        pop hl
pn_ok:  ld (S_POSN),hl
        ret

; draw_glyph: A = 32..127 at S_POSN.  The glyph is staged in GLYPHBUF
; (nibble-swapped when its side differs from the column's, inverted for
; INVERSE), then merged into the screen through mask C (OVER: XOR).
draw_glyph:
        sub 32
        ld b,a
        and $FE
        ld l,a
        ld h,0
        add hl,hl
        add hl,hl
        ld de,FONT
        add hl,de
        ex de,hl                ; DE = glyph pair (8 bytes, one page)
        ld hl,(S_POSN)
        ld a,l
        xor b
        rra                     ; carry = glyph side differs from column
        ld c,$F0
        bit 0,l
        jr z,dg_e
        ld c,$0F
dg_e:   push hl
        ld hl,GLYPHBUF
        ld b,8
        jr c,dg_sw
dg_cp:  ld a,(de)
        ld (hl),a
        inc e
        inc l
        djnz dg_cp
        jr dg_bd
dg_sw:  ld a,(de)
        rrca
        rrca
        rrca
        rrca
        ld (hl),a
        inc e
        inc l
        djnz dg_sw
dg_bd:  ld a,(P_FLAG)
        bit 2,a
        jr z,dg_nv
        ld l,GLYPHBUF & $FF
        ld b,8
dg_iv:  ld a,(hl)
        cpl
        ld (hl),a
        inc l
        djnz dg_iv
dg_nv:  pop hl
        call pos_addr
        ld de,GLYPHBUF
        ld b,8
        ld a,(P_FLAG)
        rra
        jr c,dg_ov
dg_nm:  ld a,(de)
        xor (hl)
        and c
        xor (hl)
        ld (hl),a
        inc e
        inc h
        djnz dg_nm
        ret
dg_ov:  ld a,(de)
        and c
        xor (hl)
        ld (hl),a
        inc e
        inc h
        djnz dg_ov
        ret

; pos_addr: H = row 0-23, L = column 0-63 -> HL = top screen byte
pos_addr:
        ld a,l
        srl a
        ld l,a
        ld a,h
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
; attr_addr: H = row, L = column 0-63 -> HL = attribute byte
attr_addr:
        srl l
        ld a,h
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

; scroll: text rows 1-23 up one row, row 23 cleared to ATTR_P
scroll: ld c,0
sc_r:   ld h,c
        ld l,0
        call pos_addr
        ex de,hl
        ld h,c
        inc h
        ld l,0
        call pos_addr
        ld b,8
sc_l:   push bc
        push hl
        push de
        ld bc,32
        ldir
        pop de
        pop hl
        pop bc
        inc h
        inc d
        djnz sc_l
        inc c
        ld a,c
        cp 23
        jr c,sc_r
        ld hl,$5820
        ld de,$5800
        ld bc,736
        ldir
        ld a,(ATTR_P)
        ld b,32
sc_a:   ld (de),a
        inc de
        djnz sc_a
        ld hl,$50E0
        ld c,8
sc_c:   push hl
        ld b,32
sc_c2:  ld (hl),0
        inc l
        djnz sc_c2
        pop hl
        inc h
        dec c
        jr nz,sc_c
        ret

; set_colour: C = control code 16-21, A = value, HL = ATTR_P or ATTR_T
; (its mask follows at HL+1).  8 (and 9) mean transparent.
set_colour:
        ld b,a
        ld a,c
        sub 20
        jr nc,sc_flag
        push hl
        add a,4
        add a,a
        ld e,a
        ld d,0
        ld hl,sc_tab
        add hl,de
        ld c,(hl)               ; field mask
        inc hl
        ld e,(hl)               ; field shift
        pop hl
        ld a,b
        cp 8
        jr nc,sc_tr
        inc e
sc_sh:  dec e
        jr z,sc_sd
        rlca
        jr sc_sh
sc_sd:  and c
        ld b,a
        ld a,(hl)
        xor b
        and c
        xor (hl)
        ld (hl),a
        inc hl
        ld a,c
        cpl
        and (hl)
        ld (hl),a
        ret
sc_tr:  inc hl
        ld a,c
        or (hl)
        ld (hl),a
        ret
sc_flag:                        ; A = 0 INVERSE (P_FLAG bit 2), 1 OVER (bit 0)
        ld c,4
        or a
        jr z,sf_1
        ld c,1
sf_1:   ld hl,P_FLAG
        ld a,b
        or a
        ld a,c
        jr z,sf_off
        or (hl)
        ld (hl),a
        ret
sf_off: cpl
        and (hl)
        ld (hl),a
        ret
sc_tab: defb $07,0,$38,3,$80,7,$40,6

; print_a: RST 16 - send A to the current channel; BC, DE, HL preserved
print_a:
        push hl
        push de
        push bc
        ld hl,pa_ret
        push hl
        ld hl,(CURCHL)
        ld e,(hl)
        inc hl
        ld d,(hl)
        ex de,hl
        jp (hl)
pa_ret: pop bc
        pop de
        pop hl
        ret
m_prt_e:
