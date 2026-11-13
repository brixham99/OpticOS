; stubs.asm - compatibility entry points at their published addresses.
m_stb_s:
; CHAN-OPEN ($1601): A = stream -3..15 -> CURCHL
CHAN_OPEN:
        add a,3                 ; stream -3 is entry 0
        add a,a
        ld l,a
        ld h,0
        ld de,STRMS
        add hl,de
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        or h
        jr z,co_bad
        dec hl
        ld de,(CHANS)
        add hl,de
        ld (CURCHL),hl
        ret
co_bad: rst 8
        defb ERR_STRM
m_stb_e:
        include "basic.asm"
        include "gfx.asm"
secJ1_end:

        org $203C
m_stb_s2:
; PR-STRING ($203C): DE = text, BC = length, through RST 16
PR_STRING:
        ld a,b
        or c
        ret z
        ld a,(de)
        rst 16
        inc de
        dec bc
        jr PR_STRING
m_stb_e2:
m_tkt_s:
        include "gen/tokens.inc"
m_tkt_e:
secJ2_end:

        org $22AA
m_stb_s3:
; PIXEL-ADD ($22AA): B = y (0 = bottom of the 176-line BASIC area),
; C = x -> HL = screen byte, A = x AND 7 (0 = leftmost pixel)
PIXEL_ADD:
        ld a,175
        sub b
        jr nc,pa_ok
        rst 8
        defb ERR_RANGE
pa_ok:  ld b,a
        and $07
        ld h,a
        ld a,b
        rra
        rra
        rra
        and $18
        or h
        or $40
        ld h,a
        ld a,b
        rla
        rla
        and $E0
        ld l,a
        ld a,c
        rra
        rra
        rra
        and $1F
        or l
        ld l,a
        ld a,c
        and 7
        ret
m_stb_e3:
