; isr.asm - IM 1 frame interrupt at $0038.  Does not use IY (spec 2).
ISR:    push af
        push bc
        push de
        push hl
        ld hl,FRAMES
        inc (hl)
        jr nz,isr_k
        inc hl
        inc (hl)
        jr nz,isr_k
        inc hl
        inc (hl)
isr_k:  call kscan
        pop hl
        pop de
        pop bc
        pop af
        ei
        ret
m_isr_e:
