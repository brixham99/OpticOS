; =====================================================================
; OpticOS - a clean-room 16K ROM for the ZX Spectrum 48K
; (c) 2026 Optica Technology.  Phase 1: boot, screen, keyboard, tape,
; compatibility entry points and the legacy loader shim.
;
; Build: pasmo --bin src/opticos.asm build/opticos.rom build/opticos.sym
; Fixed addresses are set with ORG; tools/check_layout.py verifies that
; no section runs into the next fixed point.
; =====================================================================

        include "sysvars.inc"

; ---------------------------------------------------------------- $0000
        org $0000
RESET:  di
        xor a
        ld de,$FFFF
        jp boot
        defb 0
; ---------------------------------------------------------------- $0008
        org $0008
RST8:   jp err_rst
; ---------------------------------------------------------------- $0010
        org $0010
RST16:  jp print_a
; ---------------------------------------------------------------- $0018
        org $0018
RST24:  ret                     ; reserved: interpreter GET-CHAR (phase 3)
; ---------------------------------------------------------------- $0020
        org $0020
RST32:  ret                     ; reserved: interpreter NEXT-CHAR (phase 3)
; ---------------------------------------------------------------- $0028
        org $0028
RST40:  rst 8                   ; the Sinclair calculator is not provided
        defb ERR_CALC
; ---------------------------------------------------------------- $0030
        org $0030
RST48:  ret                     ; reserved: workspace allocate (phase 3)
m_rst_e:

; ---------------------------------------------------------------- $0038
        org $0038
        include "isr.asm"

; ---------------------------------------------------------------- $0066
        org $0066
NMI:    push hl
        push af
        ld hl,(NMIADD)
        ld a,l
        or h
        jr z,nmi_x
        jp (hl)                 ; handler finds AF, HL on the stack
nmi_x:  pop af
        pop hl
        retn
m_nmi_e:

; ------------------------------------------------- section B $0070-$03B4
secB:
        include "boot.asm"
        include "keyboard.asm"
secB_end:

; ---------------------------------------------------------------- $03B5
        org $03B5
        include "sound.asm"
secC_end:

; ---------------------------------------------------------------- $04C2
        org $04C2
        include "save.asm"
secD_end:

; ---------------------------------------------------------------- $0556
        org $0556
        include "load.asm"
secE_end:

; ---------------------------------------------------------------- $05E3
        org $05E3
        include "edge.asm"
        include "errors.asm"
secF_end:

; ---------------------------------------------------------------- $096F
        org $096F
POKE_RET:
        ret                     ; POKE 23739,111 makes channel S output land here
; ---------------------------------------------------------------- $0970
        include "print.asm"
secG_end:

; ---------------------------------------------------------------- $0D6B
        org $0D6B
        include "cls.asm"
secH_end:

; ---------------------------------------------------------------- $0DAF
        org $0DAF
CL_ALL: jp CLS
        include "console.asm"
        include "legacy.asm"
secI_end:

; ---------------------------------------------------------------- $1601
        org $1601
        include "stubs.asm"

; ---------------------------------------------------------------- $3E80
        org FONT
m_font_s:
        incbin "../font/font4x8.bin"
m_font_e:
