; =====================================================================
; OpticOS - a clean-room 16K ROM for the ZX Spectrum 48K
; (c) 2026 Optica Technology Design.  Phase 1: boot, screen, keyboard, tape,
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
RST16:  jp x_txt                ; SCREEN 1/2: any text output returns to SCREEN 0 first
xt_jp:  jp print_a
err_brk: rst 8                  ; the extension ROM far-calls this for BREAK
        defb ERR_BREAK
; ---------------------------------------------------------------- $0018
        org $0018
RST24:
tk:     ld hl,(CH_ADD)          ; GET-CHAR: A = current token
        ld a,(hl)
        ret
; ---------------------------------------------------------------- $0020
        org $0020
RST32:
skip1:  ld hl,(CH_ADD)          ; NEXT-CHAR: step over a one-byte token
        inc hl
        ld (CH_ADD),hl
        ret
; ---------------------------------------------------------------- $0028
        org $0028
RST40:  jp fu_run                ; OpticOS's own maths byte-code (fptrans.asm);
                                ; the Sinclair calculator is not provided
; ---------------------------------------------------------------- $0030
        org $0030
RST48:
ev_int: call ev_expr            ; an expression as a 16-bit integer -> DE
        jp pop_int
m_rst_e:

; ---------------------------------------------------------------- $0038
        org $0038
        include "isr.asm"
; scr128: if SMODE is set, show screen 5 and clear it, then the usual RST 16.
; 21 bytes, exactly filling the gap up to NMI.  The final JR reaches xt_jp.
x_txt:  push af
        push bc
        ld a,(SMODE)
        or a
        jr z,xt_ok
        xor a
        ld (SMODE),a
        ld bc,$7FFD
        out (c),a
xt_ok:  pop bc
        pop af
        jr xt_jp
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
        include "misc.asm"
secB_end:
; scr128 (5 bytes): DRAW in SCREEN 1/2 goes to the extension ROM
st_draw: ld e,3
        jp st_drx
; ---------------------------------------------------------------- $03B5
        org $03B5
        include "sound.asm"
        include "strfn.asm"
; scr128 (part, 19 bytes): xchk - in SCREEN 1/2 hand the statement to the
; 128K extension ROM, dropping the caller's own code; in SCREEN 0 return.
; xgo pages the extension ROM, keeping the screen on show; E = what to do
; (0 PLOT, 1 CLS, 2 a name used as a function, 3 DRAW).  The extension answers at
; xgo+12; without one (48K, or OpticOS in both slots) the RET runs.
xchk:   ld a,(SMODE)
        or a
        ret z
        pop hl
xgo:    ld a,(SMODE)
        and 8
        or $10
        ld bc,$7FFD
        out (c),a
x_back: ret
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
        include "misc2.asm"
        include "errors.asm"            ; its message table covers $0767-$0808, so no
        include "tape.asm"              ; code is fetched where LD-BLOCK-level traps sit
secF_end:
st_drx: call xchk
        jp st_draw0
; ---------------------------------------------------------------- $096F
        org $096F
POKE_RET:
        ret                     ; POKE 23739,111 makes channel S output land here
; ---------------------------------------------------------------- $0970
        include "print.asm"
        include "edit.asm"
        include "input.asm"
secG_end:

; ---------------------------------------------------------------- $0D6B
        org $0D6B
        include "cls.asm"
        include "ext128.asm"
secH_end:

; ---------------------------------------------------------------- $0DAF
        org $0DAF
CL_ALL: jp CLS
        include "console.asm"
        include "legacy.asm"
        include "list.asm"
        include "keyfn.asm"
secI_end:

; ---------------------------------------------------------------- $1601
        org $1601
        include "stubs.asm"
        include "fpcore.asm"
        include "fptrans.asm"
        include "fpconv.asm"
        include "expr.asm"
        include "vars.asm"
        include "tokenise.asm"
        include "strfn2.asm"
        include "flow.asm"
        include "error2.asm"
m_tkd_s:
        include "gen/tokdisp.inc"
m_tkd_e:
secK_end:

; ---------------------------------------------------------------- $3E80
        org FONT
m_font_s:
        incbin "../font/font4x8.bin"
m_font_e:
