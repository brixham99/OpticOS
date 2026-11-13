; flow.asm - phase 5c: CASE, EXIT, ERROR n [, msg$], CLEAR [ramtop], and the
; PROC-name lookup used by RUN, RESTORE and SAVE ... AUTO.
m_ext_s:
; EXIT WHILE / EXIT REPEAT / EXIT FOR: on after the matching WEND, UNTIL or
; NEXT, found by counting the loop keywords forwards (each closing keyword
; is its opening one + 1).  EXIT FOR also drops the FOR frame.
st_exit: rst $18
        ld c,a
        rst $20
        cp T_FOR
        call z,cs_pop           ; the FOR frame (BC is kept)
        ld b,1
        ld hl,(CH_ADD)
xt_l:   ld a,(hl)
        cp 13
        jr nz,xt_t
        ld hl,(CURLN)
        call nxl
        ld (CURLN),hl
        ld a,(hl)
        or a
        jp z,err_struc
        inc hl
        jr xt_l
xt_t:   sub c
        jr nz,xt_3
        inc b
xt_3:   dec a
        jr nz,xt_n
        dec b
        jr z,xt_f
xt_n:   call tk_len
        jr xt_l
xt_f:   call tk_len             ; then the rest of that statement
xt_s:   ld (CH_ADD),hl
        ld a,(hl)
        call is_end
        jp z,go_st
        call tk_len
        jr xt_s
m_ext_e:
