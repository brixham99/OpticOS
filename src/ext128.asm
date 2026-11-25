; ext128.asm - OpticOS 128 extension hook (11 bytes here + a 3-byte JP in
; basic.asm). A statement that starts with a name that is not a PROC comes
; here before "No such PROC or FN". Port $7FFD bit 4 pages the 128K's ROM
; slot 1, and execution carries on at ext_back in whichever ROM is then
; paged:
; * 48K: the port is odd, so the ULA ignores it; this code goes on, and
;   carry (set) gives the error as before.
; * 128K with OpticOS in both ROM slots: the same code is in slot 1, so the
;   same thing happens.
; * 128K with an extension ROM in slot 1: the extension has a JP at ext_back.
;   It reads the statement at CH_ADD (the name token), and gives control back
;   by running OUT (C),A with A = 0 (ROM 0, RAM bank 0) and BC = $7FFD, from
;   ext_back-2 in its own ROM, so the next fetch is ext_back here: NC = it ran
;   the statement (back to the run loop), C = not its name (the error).
; Published interface for extension ROMs: ext_back's address, CH_ADD at the
; name token, and the stack holding the run loop's return address.
ext_hook:
        ld a,(SMODE)            ; ROM slot 1, RAM bank 0 at $C000, and the screen
        and 8                   ; on show stays on show (SCREEN FLIP's bit 3)
        or $10
        ld bc,$7FFD
        scf
        out (c),a
ext_back:
        ret nc
        rst 8
        defb ERR_NOPRC
