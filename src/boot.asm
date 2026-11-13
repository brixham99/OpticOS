; boot.asm - cold start: RAM test, RAMTOP, system variables, channels.
m_boot_s:
boot:   out ($FE),a             ; A = 0: black border, speaker off
        ld a,$3F
        ld i,a
        ld hl,$4000             ; test and clear RAM upwards until a
bt_mem: ld (hl),$AA             ; byte fails to hold both patterns
        ld a,(hl)
        cp $AA
        jr nz,bt_top
        ld (hl),$55
        ld a,(hl)
        cp $55
        jr nz,bt_top
        ld (hl),0
        inc hl
        ld a,h
        or l
        jr nz,bt_mem
bt_top: dec hl
        ld (P_RAMT),hl          ; $7FFF (16K) or $FFFF (48K)
        ld de,-168              ; 21 UDGs live above RAMTOP
        add hl,de
        ld (RAMTOP),hl
        ld sp,hl
        inc hl
        ld (UDG),hl
        ld iy,ERR_NR
        ld hl,chan_init
        ld de,CHANTAB
        ld bc,21
        ldir
        ld hl,strm_init         ; offsets are < 256: expand to words
        ld de,STRMS
        ld b,7
bt_st:  ld a,(hl)
        ld (de),a
        inc hl
        inc de
        xor a
        ld (de),a
        inc de
        djnz bt_st
        ld hl,CHANTAB
        ld (CHANS),hl
        ld hl,CHANTAB+5         ; current channel: S
        ld (CURCHL),hl
        ld hl,$0523             ; REPDEL 35 frames, REPPER 5
        ld (REPDEL),hl
        ld hl,$3C00
        ld (CHARS),hl
        ld hl,$5D50
        ld (PROG),hl
        ld (VARS),hl
        ld (E_LINE),hl
        ld a,$FF
        ld (KS_LAST),a
        ld (ERR_NR),a
        ld a,$07                ; white ink on black paper, black border
        ld (ATTR_P),a
        ld (BORDCR),a
        ld a,64
        ld (OMODE),a
        im 1
        ei
        call CLS
        ld hl,$5800             ; row 0: colour bar, 16 swatches of two
        ld b,0                  ; attribute cells (paper = ink, no pixels)
bt_bar: ld a,b
        and 7
        ld c,a
        add a,a
        add a,a
        add a,a
        or c
        bit 3,b
        jr z,bt_nb
        or $40                  ; second half BRIGHT
bt_nb:  ld (hl),a
        inc l
        ld (hl),a
        inc l
        inc b
        bit 4,b
        jr z,bt_bar
        ld a,2                  ; row 1 blank, banner and version on
        ld (S_POSN+1),a         ; rows 2-3, row 4 blank, prompt on row 5
        ld hl,banner
        call pr_msg
        ld a,13
        call pr_out
        ld hl,banner2
        call pr_msg
        ld a,13
        call pr_out
        ld a,13
        call pr_out
        ld de,0                 ; seed RND from FRAMES
        call fp_randomize
        call ws_init
        call chime
        jp console

banner: defm "OpticOS (c) 2026 Optica Technolog"
        defb 'y'+$80
banner2: defm "OpticBASIC v0."
        defb '1'+$80

chan_init:                      ; Sinclair layout: out, in, letter
        defw PR_OUT, key_in
        defb 'K'
        defw PR_OUT, key_in
        defb 'S'
        defw POKE_RET, key_in
        defb 'R'
        defw POKE_RET, key_in
        defb 'P'
        defb $80
strm_init:                      ; streams -3..3 -> K S R K K S P
        defb 1, 6, 11, 1, 1, 6, 16
m_boot_e:
