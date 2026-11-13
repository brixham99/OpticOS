; edge.asm - LD-EDGE-2 ($05E3) and LD-EDGE-1 ($05E7).
; B = timing counter (incremented every 59 T after a 358 T delay),
; C bit 5 = last EAR level, bits 0-2 = border colour.
; Carry clear on return = time-out (B wrapped) or SPACE pressed.
m_edge_s:
LD_EDGE2:
        call LD_EDGE1
        ret nc
LD_EDGE1:
        ld a,22
le_dly: dec a
        jr nz,le_dly
        or a                    ; 358 T so far, carry clear
le_lp:  ld a,$7F                ; 59 T per sample
        inc b
        ret z
        in a,($FE)
        rrca                    ; carry = SPACE (bit 0), bit 5 = EAR (bit 6)
        ret nc
        xor c
        and $20
        jr z,le_lp
        ld a,c                  ; edge: flip level and border colour
        cpl
        ld c,a
        and 7
        xor 8
        out ($FE),a
        scf
        ret
ob_sig: defb "OB",1,0           ; (tape.asm) data at $0605, where SAVE-ETC-level traps sit
m_edge_e:

; lb_byte: read 8 bits into L (via full-cycle widths), fold into parity H
m_ld_s2:
lb_byte:
        ld l,1                  ; marker bit
lbb:    ld b,LB_BIT0
        call LD_EDGE2
        ret nc
        ld a,LB_BITTH
        cp b                    ; carry = long cycle = 1
        rl l
        jr nc,lbb
        ld a,h
        xor l
        ld h,a
        scf
        ret
m_ld_e2:
