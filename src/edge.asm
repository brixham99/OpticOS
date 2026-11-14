; edge.asm - LD-EDGE-2 ($05E3) and LD-EDGE-1 ($05E7).
; B = timing counter (incremented every 59 T after a 326 T delay),
; C = stripe state: CPL on every edge (bit 5 = last EAR level); le_col
; turns it into the border colour.  v1.0.3: the exit path after an edge is
; 32 T longer than before and the delay 32 T shorter, so the time from an
; edge being seen to the next sample is unchanged (and the 59 T loop too).
; Carry clear on return = time-out (B wrapped) or SPACE pressed.
m_edge_s:
LD_EDGE2:
        call LD_EDGE1
        ret nc
LD_EDGE1:
        ld a,20                 ; 20 x 16 T (+7 -5 +4) = 326 T, was 22 (358 T)
le_dly: dec a
        jr nz,le_dly
        or a                    ; 326 T so far, carry clear
le_lp:  ld a,$7F                ; 59 T per sample
        inc b
        ret z
        in a,($FE)
        rrca                    ; carry = SPACE (bit 0), bit 5 = EAR (bit 6)
        ret nc
        xor c
        and $20
        jr z,le_lp
        ld a,c                  ; edge: flip level and stripe state
        cpl
        ld c,a
        or 0                    ; 2 x 7 T: with le_col, 32 T more than the
        or 0                    ; old AND 7 / XOR 8 / OUT / SCF / RET
        jp le_col
        defb 0
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
