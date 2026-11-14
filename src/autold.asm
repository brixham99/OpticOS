; autold.asm - the end of con_enter's J"" rule (console.asm), kept here
; where there is room: the line becomes LOAD "" and is drawn again as that.
m_ald_s:
ce_set: ld hl,ce_ld
        ld de,EBUF
        ld bc,7
        ldir
        ld a,7
        ld (CON_LEN),a
        jp redraw
ce_ld:  defm "LOAD \"\""
m_ald_e:
