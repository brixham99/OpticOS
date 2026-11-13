; input.asm - phase 5: INPUT, and READ / RESTORE (DATA is skipped like REM).
m_in_s:
; ---------------------------------------------------- INPUT ["prompt";] v [, v ...]
; Each variable gets its own input line, edited like the console line.
st_input:
        rst $18
        cp 6
        jr nz,in_v
        call ev_expr            ; the prompt
        call ev_pop
        call s_print
        ld a,';'
        call expect
in_v:   ld bc,in_get
; v_list: for each variable of a comma list, BC (A = its type) pushes
; the value to store
v_list: push bc
        rst $18
        cp 1
        jp nz,err_syn
        call var_ref            ; HL = value, A = type
        pop bc
        push bc
        push hl
        push af
        call jpbc
        pop af
        pop hl
        call val_store
        pop bc
        rst $18
        cp ','
        ret nz
        rst $20
        jr v_list
in_get: push af
        call con_inp            ; EBUF, CON_LEN
        call ev_push
        ld (hl),0
        inc hl
        ld (hl),1
        inc hl
        ld a,(CON_LEN)
        ld (hl),a
        inc hl
        ld de,EBUF
        ld (hl),e
        inc hl
        ld (hl),d
        pop af
        cp 2
        ret z
        call ev_top
        jp fv_top               ; numeric: as VAL

; ---------------------------------------------------- READ v [, v ...]
; DATAP: 0 = before the first DATA line, else the next item or the $0D
; that ends a DATA line.  DATA must start its line.
st_read:
        ld bc,rd_get
        jr v_list
rd_get: ld hl,(DATAP)
        ld a,h
        or l
        jr nz,rd_p
        ld hl,OPROG
        jr rd_ln
rd_p:   ld a,(hl)
        cp 13
        jr nz,rd_it
        inc hl                  ; $0D, length: the next line
        inc hl
rd_ln:  ld a,(hl)
        or a
        jr z,rd_no
        inc hl
        ld a,(hl)
        inc hl
        cp T_DATA
        jr z,rd_it
        dec hl
        dec hl
        call nxl
        jr rd_ln
rd_no:  rst 8
        defb ERR_DATA
rd_it:  ld de,(CH_ADD)
        push de
        ld (CH_ADD),hl
        call ev_expr
        rst $18
        cp ','
        jr nz,rd_e
        rst $20
        jr rd_s
rd_e:   cp 13
        jp nz,err_syn
rd_s:   ld (DATAP),hl
        pop de
        ld (CH_ADD),de
        ret
st_restore:
        ld hl,0
        ld (DATAP),hl
        ret
st_data equ st_rem
m_in_e:

