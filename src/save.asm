; save.asm - SA-BYTES at $04C2.  IX = start, DE = length, A = flag.
; Standard ROM tape encoding: pilot, two sync pulses, flag, data, parity.
SA_PILB equ 161                 ; 13*B + 78 = 2171 T pilot half-pulse
SA_S1   equ 46
SA_S2   equ 52
SA_B0   equ 60
SA_B1   equ 126
m_sav_s:
SA_BYTES:
        ld hl,tape_ret
        push hl
        ld hl,3223              ; data block pilot (half-pulses)
        bit 7,a
        jr nz,sa_d
        ld hl,8063              ; header pilot
sa_d:   ex af,af'
        di
        ld c,$02                ; red border, MIC low
sa_pil: ld b,SA_PILB
        call sa_half
        dec hl
        ld a,h
        or l
        jr nz,sa_pil
        ld b,SA_S1
        call sa_half
        ld b,SA_S2
        call sa_half
        ld a,c
        xor $03                 ; data stripes: blue / yellow
        ld c,a
        ex af,af'
        ld l,a                  ; first byte: the flag
        ld h,0                  ; H = running parity
sa_lp:  call sa_byte
        ld a,d
        or e
        jr z,sa_par
        ld l,(ix+0)
        inc ix
        dec de
        jr sa_lp
sa_par: ld l,h
        call sa_byte
        ld b,SA_B0
        call sa_half            ; closing edge
        scf
        ret

sa_byte:                        ; send L MSB first, fold into parity H
        ld a,h
        xor l
        ld h,a
        scf
        rl l                    ; carry = bit 7, marker bit in bit 0
sab_b:  ld b,SA_B0
        jr nc,sab_1
        ld b,SA_B1
sab_1:  call sa_half
        ld b,SA_B0
        jr nc,sab_2
        ld b,SA_B1
sab_2:  call sa_half
        sla l
        jr nz,sab_b
        ret

sa_half:                        ; wait 13*B, then flip MIC and border
        djnz sa_half            ; (carry is preserved throughout)
        ld a,c
        cpl
        ld c,a
        out ($FE),a
        ret

; Tape-trap layout (v1.0.1).  Emulators that fast-load or fast-save .tap
; files trap the tape routines at fixed addresses and return through fixed
; points.  From Fuse's public source (tape.c, z80/opcodes_base.c): the save
; trap fires on the EX AF,AF' at $04D0 (A = flag, IX, DE as on entry, the
; exit handler on the stack) and resumes at $053E, which must be a RET; the
; load trap fires on a RET NZ at $056B and resumes at the RET at $05E2.
; Either RET pops the handler pushed on entry, tape_ret at $053F, which
; other trapping interfaces (e.g. Spectranet) also return into.  tape_ret
; can run twice without harm.  check_layout.py checks these bytes.
m_sav_g:                        ; (zero-filled gap up to $053E)
        org $053E
trap_ret:
        ret                     ; $053E: save traps resume here
; tape_ret ($053F): common exit for SA-BYTES and LD-BYTES: restore the
; border, re-enable interrupts and report BREAK (error D) if SPACE is held.
tape_ret:
        ei
        push af
        ld a,(BORDCR)
        rra
        rra
        rra
        and 7
        out ($FE),a
        ld a,$7F
        in a,($FE)
        rra                     ; carry clear = SPACE held
        jr nc,tr_brk
        pop af
        ret
tr_brk: rst 8
        defb ERR_BREAK
m_sav_e:
