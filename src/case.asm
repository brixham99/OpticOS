; case.asm - phase 5c: CASE (see flow.asm)
m_cas_s:
; CASE expr OF / WHEN v [, v ...] / OTHERWISE / ENDCASE.  The prepass links
; CASE -> WHEN -> ... -> OTHERWISE -> ENDCASE like IF -> ELSEIF -> ENDIF.
; The selector stays on the value stack only while the WHEN values are
; compared; a WHEN or OTHERWISE reached at the end of a branch goes to
; ENDCASE (st_else).
st_case: call rd_link           ; DE = the first WHEN
        push de
        call ev_expr
        ld a,T_OF
        call expect
        pop hl
cw_l:   call lk_chk
        ld (CURLN),hl
        inc hl
        ld a,(hl)
        inc hl
        ld (CH_ADD),hl
        cp T_ENDCASE
        jr z,cw_x
        push af
        call rd_link            ; DE = the next branch
        pop af
        cp T_OTHERWISE
        jr z,cw_y
        push de
cw_v:   call ev_expr
        call cmp2               ; selector vs value
        call ev_pop
        or a
        jr z,cw_m
        rst $18
        cp ','
        jr nz,cw_e
        rst $20
        jr cw_v
cw_e:   pop hl
        jr cw_l
cw_m:   pop de                  ; a match: skip the rest of the list
cw_y:   call ev_pop             ; drop the selector and run this branch
        ld hl,(CH_ADD)
        jp xt_s
cw_x:   call ev_pop             ; no branch matched
        ld hl,(CURLN)
        jp go_after
m_cas_e:
