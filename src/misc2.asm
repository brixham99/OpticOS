; misc2.asm - POKE, WAIT, RANDOMIZE (moved out of basic.asm in phase 5c)
m_ms2_s:
st_poke: rst $30
        push de
        call argn
        pop hl
        ld (hl),e
        ret
st_wait: rst $30
sw_l:   ld a,d
        or e
        ret z
        ei
        halt
        call brk_chk
        dec de
        jr sw_l
; brk_chk: report "Break" if CAPS SHIFT + SPACE is held (A lost)
brk_chk: ld a,$7F
        in a,($FE)
        rra
        ret c
        ld a,$FE
        in a,($FE)
        rra
        ret c
        rst 8
        defb ERR_BREAK
st_randomize:
        ld de,0
        rst $18
        call is_end
        jr z,sr_go
        rst $30
sr_go:  jp fp_randomize
m_ms2_e:
