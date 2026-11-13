; clear.asm - phase 5c: CLEAR [ramtop]
m_clr_s:
; CLEAR: forget the variables, open loops and PROC calls.  CLEAR n also
; moves RAMTOP to n (the stacks, direct line and heap move with it); typed
; directly, the rest of the line is not run.
st_clear:
        rst $18
        call is_end
        jr z,clr_v
        rst $30                 ; DE = new RAMTOP
        call ws_sel             ; HL = n - the workspace below it
        ld a,(bc)
        add a,d
        ld h,a
        ld l,e
        jp nc,err_nomem
        ld bc,(VARSB)
        sbc hl,bc
        jp c,err_nomem
        ld (RAMTOP),de
        call ws_lay
        call clr_v
        ld sp,(RAMTOP)
        ld hl,con_err
        push hl
        ld (ERR_SP),sp
        ld hl,(CURLN)
        ld a,h
        or l
        jp z,console
        jp rs_after
clr_v:  call clr_vars
        jp stk_reset
m_clr_e:
