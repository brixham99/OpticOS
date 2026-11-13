; misc.asm - phase 5: BEEP, OUT, DPOKE, CALL, SWAP.
m_msc_s:
; BEEP duration, pitch (semitones from middle C), through BEEPER:
; f = 261.63 * 2^(pitch/12), HL = 437500/f - 30, DE = f * duration
st_beep: call ev_expr
        ld a,','
        call expect
        call ev_expr
        ld de,693               ; pitch * ln 2 / 12
        call k_mul
        ld de,12000
        call push_int
        call op_div
        call ev_top             ; a copy of it
        push hl
        call ev_push
        ex de,hl
        pop hl
        ld bc,5
        ldir
        call ev_top
        call fp_neg
        call ev_top
        call fp_exp
        ld de,1672              ; 437500 / 261.63
        call k_mul
        call pop_int
        ld hl,-30
        add hl,de
        push hl
        call ev_top
        call fp_exp
        call op_mul             ; duration * 2^(pitch/12)
        ld de,262
        call k_mul
        call pop_int
        pop hl
        jp BEEPER
k_mul:  call push_int
        jp op_mul

; OUT port, byte / DPOKE address, word / CALL address
st_out: rst $30
        push de
        call argn
        pop bc
        out (c),e
        ret
st_dpoke: rst $30
        push de
        ld a,','
        call expect
        rst $30
        pop hl
        ld (hl),e
        inc hl
        ld (hl),d
        ret
st_call: rst $30
        ex de,hl
        jp (hl)

; SWAP a, b: two variables (or elements) of the same type
st_swap: rst $18
        cp 1
        jp nz,err_syn
        call var_ref
        push hl
        push af
        ld a,','
        call expect
        rst $18
        cp 1
        jp nz,err_syn
        call var_ref
        pop bc
        cp b
        jp nz,err_type
        pop de                  ; DE = first, HL = second
        push af
        call tsz                ; BC = size
        push de
        push hl
swp_l:   ld a,(de)
        ld b,(hl)
        ld (hl),a
        ld a,b
        ld (de),a
        inc hl
        inc de
        dec c
        jr nz,swp_l
        pop hl
        pop de
        pop af
        cp 2
        ret nz
        call sw_bp              ; strings: point each block back at its owner
        ex de,hl
; sw_bp: HL = string descriptor (length, address); its heap block's
; back-pointer follows the characters and the length byte
sw_bp:  push hl
        ld a,(hl)
        inc hl
        ld c,(hl)
        inc hl
        ld b,(hl)
        pop hl
        or a
        ret z
        push hl
        ld l,a
        ld h,0
        inc hl
        add hl,bc
        pop bc
        ld (hl),c
        inc hl
        ld (hl),b
        ret
m_msc_e:
