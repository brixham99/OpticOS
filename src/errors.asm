; errors.asm - RST 8 handler and messages.
ERR_SCREEN equ $04
ERR_DIV0   equ $05
ERR_OVFL   equ $06
ERR_RANGE  equ $0A
ERR_ARG    equ $0B
ERR_SYN    equ $0D
ERR_BREAK  equ $0C
ERR_STRM   equ $17
ERR_TAPE   equ $1A
ERR_CALC   equ $40
ERR_LEG    equ $41
ERR_OK     equ $FF
m_err_s:
err_rst:                        ; RST 8: the byte after the RST is the code
        pop hl
        ld a,(hl)
        ld (ERR_NR),a
        ld sp,(ERR_SP)
        ret                     ; into the handler whose address is at ERR_SP

; err_show: print the message for ERR_NR on a fresh line
err_show:
        ld a,(S_POSN)
        or a
        ld a,13
        call nz,pr_out
        ld a,(ERR_NR)
        ld c,a
        ld hl,err_tab
es_lp:  ld a,(hl)
        inc hl
        cp c
        jp z,pr_msg
        inc a                   ; $FF ends the table (after the OK entry)
        jr z,es_unk
es_sk:  bit 7,(hl)
        inc hl
        jr z,es_sk
        jr es_lp
es_unk: ld hl,msg_err
        call pr_msg
        ld a,c
pr_hex: push af
        rrca
        rrca
        rrca
        rrca
        call ph_d
        pop af
ph_d:   and $0F
        add a,'0'
        cp '9'+1
        jr c,ph_o
        add a,7
ph_o:   jp pr_out

; pr_msg: print a bit-7-terminated string at HL directly to the screen
pr_msg: ld a,(hl)
        push hl
        and $7F
        call pr_out
        pop hl
        bit 7,(hl)
        inc hl
        jr z,pr_msg
        ret
; pr_msgs: the same through RST 16 (the current channel)
pr_msgs:
        ld a,(hl)
        and $7F
        rst 16
        bit 7,(hl)
        inc hl
        jr z,pr_msgs
        ret

err_tab:
        defb ERR_BREAK
        defm "Brea"
        defb 'k'+$80
        defb ERR_TAPE
        defm "Tape: bad or missing bloc"
        defb 'k'+$80
        defb ERR_STRM
        defm "No such strea"
        defb 'm'+$80
        defb ERR_RANGE
        defm "Value outside rang"
        defb 'e'+$80
        defb ERR_SCREEN
        defm "Position off scree"
        defb 'n'+$80
        defb ERR_DIV0
        defm "Division by zer"
        defb 'o'+$80
        defb ERR_OVFL
        defm "Overflo"
        defb 'w'+$80
        defb ERR_ARG
        defm "Bad argumen"
        defb 't'+$80
        defb ERR_SYN
        defm "Syntax erro"
        defb 'r'+$80
        defb ERR_CALC
        defm "Calculator not supporte"
        defb 'd'+$80
        defb ERR_LEG
        defm "Legacy BASIC: unsupported statemen"
        defb 't'+$80
        defb ERR_OK
        defm "O"
        defb 'K'+$80
        defb $FF                ; never matched: ERR_OK entry above catches $FF
msg_err:
        defm "Error "
        defb '$'+$80
msg_prog:
        defm "Program:"
        defb ' '+$80
msg_bytes:
        defm "Bytes:"
        defb ' '+$80
m_err_e:
