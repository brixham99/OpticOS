; strfn2.asm - phase 5 functions: INSTR ERR$ IN USR DPEEK JOY.
m_sf2_s:
; INSTR(a$, b$ [, start]): position of b$ in a$ from start, or 0
f_instr: call arg1s
        ld a,','
        call expect
        call ev_expr
        ld e,1
        rst $18
        cp ','
        call z,argn
        call rparen
        ld a,e
        or a
        jp z,err_arg
        push af
        call ev_2               ; HL = a$, DE = b$
        ex de,hl
        call str_chk
        call s_ld               ; HL = b$ characters, C = length
        ld b,c
        ex de,hl
        call s_ld               ; HL = a$ characters, C = length
        pop af
        dec a                   ; A = offset
in_l:   push af
        add a,b
        jr c,in_no
        cp c
        jr z,in_ok
        jr nc,in_no
in_ok:  pop af
        push af
        push hl
        push de
        push bc
        add a,l
        ld l,a
        adc a,h
        sub l
        ld h,a
        inc b
        dec b
        jr z,in_f
in_c:   ld a,(de)
        cp (hl)
        jr nz,in_f
        inc hl
        inc de
        djnz in_c
in_f:   pop bc
        pop de
        pop hl
        jr z,in_y
        pop af
        inc a
        jr in_l
in_y:   pop af
        inc a
        jr in_r
in_no:  pop af
        xor a
in_r:   call ev_pop
        call ev_pop
        jp push_a
; s_ld: HL = string entry -> HL = characters, C = length
s_ld:   inc hl
        inc hl
        ld c,(hl)
        inc hl
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        ret
; ERR$: the message of the last error, "" if none
f_errs: call ev_push
        ld a,(ERRV)
        or a
        jr z,fe_0
        ld c,a
        ld hl,err_tab
fe_l:   ld a,(hl)
        inc hl
        cp c
        jr z,fe_f
        inc a
        jr z,fe_0
fes_s:   bit 7,(hl)
        inc hl
        jr z,fes_s
        jr fe_l
fe_0:   call ev_top
        ld (hl),a
        inc hl
        ld (hl),1
        inc hl
        ld (hl),0
        ret
fe_f:   push hl
        ld b,0
fes_n:   inc b
        bit 7,(hl)
        inc hl
        jr z,fes_n
        ld a,b
        call fc_new
        pop hl
fe_c:   ld a,(hl)
        and $7F
        ld (de),a
        inc de
        bit 7,(hl)
        inc hl
        jr z,fe_c
        ret
; IN(port), USR(address) (-> BC), DPEEK(address), JOY (Kempston)
f_in:   call una_int
        ld b,d
        ld c,e
        in a,(c)
        jp push_a
f_usr:  call una_int
        ex de,hl
        call jphl
        ld d,b
        ld e,c
        jp push_u
f_dpeek: call una_int
        ex de,hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        jp push_u
f_joy:  in a,($1F)
        and $1F
        jp push_a
una_int: call ev_una
        jp pop_int
m_sf2_e:
