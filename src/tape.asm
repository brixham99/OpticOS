; tape.asm - phase 5 tape commands: SAVE / LOAD / VERIFY with CODE forms.
m_tp_s:
; ---------------------------------------------------- tape
; tp_name: string expression -> LG_NAME, 10 characters padded with
; spaces, or $FF for "" (any).  Z if the name was "".
tp_name: call ev_expr
        call ev_pop
        call str_chk
        inc hl
        inc hl
        ld c,(hl)
        inc hl
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        ld a,c
        or a
        push af
        ld de,LG_NAME
        ld b,10
tn_l:   ld a,' '
        inc c
        dec c
        jr z,tn_s
        ld a,(hl)
        inc hl
        dec c
tn_s:   ld (de),a
        inc de
        djnz tn_l
        pop af
        ret nz
        dec a
        ld (LG_NAME),a
        xor a
        ret
; tp_sig: the 4-byte signature in front of the program, as on tape
tp_sig: ld hl,ob_sig
        ld de,OPROG-4
        ld bc,4
        ldir
        ret
ob_sig: defb "OB",1,0

; SAVE "name" [CODE start, length]
st_save:
        call tp_name
        jp z,err_arg
        ld hl,LG_NAME
        ld de,HDRBUF+1
        ld bc,10
        ldir
        call tk
        cp T_CODE
        jr z,ss_c
        call tp_sig             ; a program: signature, lines, sentinel
        ld hl,(PEND)
        ld de,OPROG-5
        or a
        sbc hl,de
        ld (HDRBUF+15),hl       ; param 2: program length
        ld de,OPROG-4
        ld bc,$8000             ; param 1: no auto-start
        xor a
        jr ss_go
ss_c:   call skip1
        call ev_expr
        call pop_int
        push de
        ld a,','
        call expect
        call ev_expr
        call pop_int
        ex de,hl                ; HL = length
        pop de                  ; DE = start
        ld bc,$8000
        ld (HDRBUF+15),bc
        ld b,d
        ld c,e
        ld a,3
ss_go:  ld (HDRBUF),a           ; A = type, DE = start, HL = length, BC = param 1
        ld (HDRBUF+11),hl
        ld (HDRBUF+13),bc
        push de
        push hl
        ld ix,HDRBUF
        ld de,17
        xor a
        call SA_BYTES
        ld b,50                 ; a second's gap before the data
ss_w:   halt
        djnz ss_w
        pop de
        pop ix
        ld a,$FF
        jp SA_BYTES

; LOAD "name" [CODE [start]] / VERIFY "name" [CODE [start]]
st_verify:
        ld a,1
        jr sl_go
st_load: xor a
sl_go:  ld (LG_VF),a
        call tp_name
        ld hl,0
        ld (LG_DEST),hl
        call tk
        cp T_CODE
        jr nz,sl_p
        call skip1
        call tk
        cp 13
        jr z,sl_c
        cp ':'
        jr z,sl_c
        call ev_expr
        call pop_int
        ld (LG_DEST),de
sl_c:   ld a,3
sl_f:   ld (LG_WANT),a
        jp lg_fetch
sl_p:   ld a,(LG_VF)
        or a
        jp z,lg_prog            ; LOAD: an OpticOS or a Sinclair program
        call tp_sig             ; VERIFY: against the program in place
        ld hl,OPROG-4
        ld (LG_DEST),hl
        xor a
        jr sl_f
; ob_load: an OpticOS program block has loaded at LEGPROG: move it up
; to OPROG (its last byte is the sentinel) and start afresh.
ob_load:
        ld bc,(HDRBUF+11)
        ld hl,OPROG-5
        add hl,bc
        push hl                 ; the new PEND
        ex de,hl
        ld hl,LEGPROG-1
        add hl,bc
        dec bc
        dec bc
        dec bc
        dec bc
        lddr
        pop de
        call ws_ld
        jp console
m_tp_e:
