; strfn.asm - phase 5 functions: HEX$ UPPER$ STRING$.
m_sfn_s:
; HEX$(n): four hex digits
f_hexs: call una_int
        push de
        call ev_push
        ld a,4
        call fc_new             ; DE = characters
        pop hl
        ld a,h
        call hx2
        ld a,l
hx2:    push af
        rrca
        rrca
        rrca
        rrca
        call hx1
        pop af
hx1:    and 15
        add a,$90
        daa
        adc a,$40
        daa
        ld (de),a
        inc de
        ret
; UPPER$(s$)
f_uppers: call str_una
        inc hl
        inc hl
        ld a,(hl)
        or a
        ret z
        push af
        ld de,0
        call s_alloc            ; the source is still on the stack (a GC root)
        push de
        call ev_top
        call sk_cp
        pop de
        pop af
        push de
        ld b,a
up_l:   ld a,(de)
        cp 'a'
        jr c,up_n
        cp 'z'+1
        jr nc,up_n
        sub 32
        ld (de),a
up_n:   inc de
        djnz up_l
        jr sg_e
; STRING$(n, s$)
f_strings:
        ld a,'('
        call expect
        call ev_u8
        push de
        ld a,','
        call expect
        call ev_expr
        call rparen
        call ev_top
        call str_chk
        inc hl
        inc hl
        pop bc                  ; C = n
        ld b,c
        ld c,(hl)
        push bc                 ; B = n
        xor a
        inc b
sg_m:   dec b
        jr z,sg_d
        add a,c
        jp c,err_strl
        jr sg_m
sg_d:   pop bc
        or a
        jr nz,sg_a
        ld (hl),a               ; nothing to repeat: ""
        ret
sg_a:   push bc
        ld de,0
        call s_alloc
        pop bc
        ld c,b                  ; C = n
        push de
sg_c:   push bc
        call ev_top
        call sk_cp
        pop bc
        dec c
        jr nz,sg_c
sg_e:   pop hl                  ; start; DE = end
        ex de,hl
        or a
        sbc hl,de
        ld a,l
; st_set: the top entry becomes the string of A characters at DE
st_set: call ev_top
        inc hl
        inc hl
        ld (hl),a
        inc hl
        ld (hl),e
        inc hl
        ld (hl),d
        ret
m_sfn_e:
