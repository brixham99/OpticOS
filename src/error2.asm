; error2.asm - phase 5c: ERROR n [, msg$] and pfind (see flow.asm)
m_err2_s:
; ERROR n [, msg$]: raise error n; msg$ (up to 28 characters) becomes its
; message for ERR$ and the error report.
st_error: call ev_u8
        push de
        ld a,$FF
        ld (EMSGN),a
        rst $18
        cp ','
        jr nz,er_x
        rst $20
        call ev_expr
        call ev_pop
        call str_chk
        inc hl
        inc hl
        ld a,(hl)
        or a
        jr z,er_x
        cp 28
        jr c,er_1
        ld a,28
er_1:   ld c,a
        ld b,0
        inc hl
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        ld de,EMBUF
        ldir
        dec de
        ex de,hl
        set 7,(hl)
        pop de
        push de
        ld a,e
        ld (EMSGN),a
er_x:   pop de
        ld a,e
        jp err_a
; pfind: a PROC name at CH_ADD -> HL = its DEF line, CH_ADD past the name
pfind:  rst $18
        cp 1
        jp nz,err_syn
        ld hl,(CH_ADD)
        ld (VID),hl
        call sym_find
        jp c,err_noprc
        push hl
        call id_skip
        pop hl
        ret
m_err2_e:
