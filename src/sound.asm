; sound.asm - BEEPER at $03B5.  DE = number of cycles, HL = period value
; (period = 8*HL + 241 T-states, the documented contract).  Uses IX and
; AF'; returns with interrupts enabled.
m_snd_s:
BEEPER: di
        ld a,l
        and 3
        ld c,a                  ; remainder 0-3 -> that many NOPs
        srl h
        rr l
        srl h
        rr l                    ; HL = period / 4 (16 T per loop pass)
        ld a,3
        sub c
        ld c,a
        ld b,0
        ld ix,bp_nops
        add ix,bc
        ld a,l
        or a
        ld a,h
        jr z,bp_l0
        inc a
bp_l0:  ld h,a                  ; H = outer passes, L = inner count
        ld a,(BORDCR)
        rra
        rra
        rra
        and 7
        or 8
        ex af,af'
        sla e                   ; count half-cycles
        rl d
bp_loop:
        ld b,h
        ld c,l
        jp (ix)
bp_nops:
        nop
        nop
        nop
bp_dly: dec c
        jr nz,bp_dly
        dec b
        jr nz,bp_dly
        ex af,af'
        xor $10
        out ($FE),a
        ex af,af'
        jr bp_f1                ; padding: 46 T so a half-cycle is 4*HL+120
bp_f1:  jr bp_f2
bp_f2:  jr bp_f3
bp_f3:  jp bp_f4
bp_f4:  dec de
        ld a,d
        or e
        jr nz,bp_loop
        ei
        ret
m_snd_e:
