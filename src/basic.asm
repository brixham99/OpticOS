; basic.asm - OpticBASIC interpreter core (phase 3): the run loop, the
; statements, the structure prepass, PROC/FN calls, TRY/CATCH and errors.
; Program lines: [length] tokens $0D [length] (length counts both length
; bytes), from OPROG to a $00 at PEND.  The DEF table follows PEND.
m_bas_s:
; ---------------------------------------------------- run loop
; run_direct: run the tokenised line at TKB
run_direct:
        ld hl,0
        ld (CURLN),hl
        ld hl,(TKB)
        ld (CH_ADD),hl
        jr run_st
run_line: ld a,(hl)             ; HL = line
        or a
        jr z,run_end
        ld (CURLN),hl
        inc hl
        ld (CH_ADD),hl
run_st: ld a,$7F                ; BREAK = CAPS SHIFT + SPACE
        in a,($FE)
        rra
        jr c,rs_go
        ld a,$FE
        in a,($FE)
        rra
        jr c,rs_go
        rst 8
        defb ERR_BREAK
rs_go:  call stmt
rs_after: call tk
        cp ':'
        jr nz,ra_1
        call skip1
        jr run_st
ra_1:   cp 13
        jr z,next_line
        cp T_ELSE
        jp nz,err_syn
next_line:
        ld hl,(CURLN)
        ld a,h
        or l
        jr z,run_end
        call nxl
        jr run_line
run_end: jp console
; go_line / go_after / go_next: from a statement handler (called from the
; run loop) continue at line HL / the line after HL / the next line
go_after: call nxl
go_line: pop af
        jr run_line
go_next: pop af
        jr next_line
go_st:  pop af                  ; continue with the statement at CH_ADD
        jr run_st
; stmt: one statement at CH_ADD
stmt:   call tk
        cp ':'
        ret z
        cp 13
        ret z
        cp T_CMT
        jr z,st_rem
        cp 1
        jr z,st_id
        sub $80
        jp c,err_syn
        cp T_NSTMT
        jp nc,err_syn
        push af
        call skip1
        pop af
        add a,a
        ld l,a
        ld h,0
        ld de,st_tab
        add hl,de
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        jp (hl)
st_rem: pop af
        jr next_line
; an identifier: an assignment, or a PROC called by its bare name
st_id:  inc hl                  ; "name =" is always an assignment
        ld a,(hl)
        bit 2,a
        jr nz,si_arr
        call tk_len0
        ld a,(hl)
        cp '='
        jr z,st_let
si_pc:  ld hl,(CH_ADD)
        ld (VID),hl
        call sym_find
        jr nc,proc_call
        rst 8
        defb ERR_NOPRC
st_let: call tk
        cp 1
        jp nz,err_syn
st_let2: call var_ref
        push hl
        push af
        ld a,'='
        call expect
        call ev_expr
        pop af
        pop hl
        jp val_store
si_arr: ld hl,(CH_ADD)          ; name(...): a PROC if one is defined
        ld (VID),hl
        call sym_find
        jr c,st_let2
; proc_call: DEF line in HL, CH_ADD at the identifier of the call
proc_call:
        push hl
        call id_skip
        call args
        pop hl
        push hl
        push bc                 ; B = argument count
        ld a,F_PROC
        ld c,5
        call cs_push
        call fr_save
        pop bc
        pop hl
        call bind
        ld a,(hl)
        cp '='
        jp z,err_syn
        ld hl,(CURLN)
        jp go_after
tk_len0: ld hl,(CH_ADD)
        jp tk_len
id_skip: call tk_len0
        ld (CH_ADD),hl
        ret
; fr_save: HL = frame -> return CH_ADD and line stored at frame+1;
; HL = frame+5
fr_save: inc hl
        ld de,(CH_ADD)
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ld de,(CURLN)
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ret
; args: optional "(a, b)" or bare "a, b" -> values pushed, B = count
args:   ld b,0
        call tk
        call is_end
        ret z
        cp '('
        push af
        jr nz,ag_l
        call skip1
ag_l:   push bc
        call ev_expr
        pop bc
        inc b
        call tk
        cp ','
        jr nz,ag_e
        call skip1
        jr ag_l
ag_e:   pop af
        ret nz
        push bc
        call rparen
        pop bc
        ret
; bind: HL = DEF line, B = argument values on the value stack -> each
; parameter made LOCAL and given its value; values popped; CH_ADD (and
; HL) after the parameter list, CURLN = the DEF line
bind:   ld (CURLN),hl
        ld de,5
        add hl,de               ; past length, DEF, link slot
        ld a,(hl)
        cp T_PROC
        jr z,bd_s
        cp T_FN
        jr nz,bd_0
bd_s:   inc hl
bd_0:   ld (CH_ADD),hl
        ld a,b
        ld (BCN),a
        ld l,b                  ; first argument = VSP - 5*count
        ld h,0
        ld d,h
        ld e,l
        add hl,hl
        add hl,hl
        add hl,de
        ex de,hl
        ld hl,(VSP)
        or a
        sbc hl,de
        ld (BAF),hl
        ld (BAP),hl
        call id_skip
        call tk
        cp '('
        jr nz,bd_l
        call skip1
bd_l:   call tk
        cp 1
        jr nz,bd_e
        ld a,(BCN)
        or a
        jp z,err_arg            ; more parameters than arguments
        dec a
        ld (BCN),a
        call var_ref
        push hl
        push af
        call loc_save
        pop af
        pop hl
        ld de,(BAP)
        push de
        call val_put
        pop hl
        ld de,5
        add hl,de
        ld (BAP),hl
        call tk
        cp ','
        jr nz,bd_e
        call skip1
        jr bd_l
bd_e:   cp ')'
        call z,skip1
        ld a,(BCN)
        or a
        jp nz,err_arg           ; more arguments than parameters
        ld hl,(BAF)
        ld (VSP),hl
        jp tk
; fn_call: an FN (VID = its identifier, CH_ADD past it) -> its value pushed
fn_call: call sym_find
        jp c,err_novar
        ld de,(CSB)             ; keep the machine stack clear of it
        ex de,hl
        ld bc,96
        add hl,bc
        sbc hl,sp
        jp nc,err_nomem
        ex de,hl
        push hl
        ld b,0
        ld hl,(VID)
        inc hl
        bit 2,(hl)
        call nz,args
        pop hl
        push hl
        push bc
        ld a,F_FN
        ld c,7
        call cs_push
        call fr_save
        pop bc
        ex (sp),hl              ; HL = DEF line, stack = frame+5
        call bind
        ld a,(hl)
        cp '='
        jr nz,fc_ml
        pop hl                  ; DEF f(x) = expression
        call skip1
        call ev_expr
        jr fn_unw
fc_ml:  ld hl,(CURLN)
        call nxl
        ex (sp),hl              ; HL = frame+5, stack = first line
        push hl
        ld hl,2                 ; SP inside run_line's call below
        add hl,sp
        ex de,hl
        pop hl
        ld (hl),e
        inc hl
        ld (hl),d
        pop hl
        call run_line           ; RETURN comes back here (SP restored)
        ret
; fn_unw: unwind to the FN frame and return to its caller's text
fn_unw: call unw_pf
        cp F_FN
        jp nz,err_endp
        jp fr_ret
; unw_pf: pop frames down to the nearest PROC or FN frame
; -> HL = frame, A = type
unw_pf: call cs_pop
        jp c,err_endp
        cp F_PROC
        ret z
        cp F_FN
        ret z
        jr unw_pf
; sym_find: VID = identifier -> HL = DEF line (CF clear) or CF set
sym_find:
        call prepass
        ld hl,(PEND)
sf_l:   inc hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        ld a,d
        or e
        scf
        ret z
        push hl
        push de
        ex de,hl
        ld de,5
        add hl,de
        ld a,(hl)
        cp T_PROC
        jr z,sym_1
        cp T_FN
        jr nz,sym_2
sym_1:   inc hl
sym_2:   ld de,(VID)
        inc hl                  ; both at the type byte
        inc de
        ld a,(de)
        xor (hl)
        and 3
        jr nz,sf_n
        inc hl
        inc de
        inc hl                  ; skip hash
        inc de
        ld a,(de)
        cp (hl)
        jr nz,sf_n
        ld b,a
sf_c:   inc hl
        inc de
        ld a,(de)
        cp (hl)
        jr nz,sf_n
        djnz sf_c
        pop hl
        pop de
        or a
        ret
sf_n:   pop de
        pop hl
        jr sf_l

; ---------------------------------------------------- prepass
; prepass: (if the program changed) match the block keywords, filling the
; link slots, and build the DEF table.  Variables are cleared.
prepass: ld a,(PPF)
        or a
        ret z
        ld hl,(CURLN)
        push hl
        ld hl,0
        push hl                 ; block stack sentinel
        push hl
        ld hl,(PEND)
        inc hl
        ld (TMP),hl             ; DEF table pointer
        ld hl,OPROG
pp_l:   ld a,(hl)
        or a
        jp z,pp_end
        ld (CURLN),hl
        inc hl
        ld a,(hl)
        dec hl
        cp T_IF
        jr z,pp_if
        cp T_WHILE
        jr z,pp_push
        cp T_REPEAT
        jr z,pp_push
        cp T_TRY
        jr z,pp_push
        cp T_DEF
        jr z,pp_def
        cp T_ELSEIF
        jr z,pp_elif
        cp T_ELSE
        jr z,pp_elif
        cp T_ENDIF
        jr z,pp_endif
        cp T_WEND
        jr z,pp_wend
        cp T_UNTIL
        jp z,pp_until
        cp T_CATCH
        jp z,pp_catch
        cp T_ENDTRY
        jp z,pp_endtry
        cp T_ENDPROC
        jp z,pp_endp
        cp T_ENDFN
        jp z,pp_endp
pp_nx:  call nxl
        jr pp_l
pp_if:  ld a,T_THEN
        call ln_has
        jr z,pp_nx
        ld a,T_IF
pp_push: push hl                ; the block stack: line, type pairs
        push af
        jr pp_nx
pp_def: ld de,(TMP)             ; add to the DEF table
        ex de,hl
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ld (TMP),hl
        push de
        ld de,(HP)
        call cphd
        pop hl
        jp nc,err_nomem
        ld a,'='
        call ln_has
        jr z,pp_nx              ; DEF f(x) = ...: one line
        ld a,T_DEF
        jr pp_push
; pp_top: the open block -> DE = its line, A = its type (still on the
; stack: SP+2 = type/flags, SP+4 = line)
pp_elif: pop af                 ; ELSEIF / ELSE after IF or ELSEIF
        pop de
        push de
        push af
        cp T_IF
        jr z,pe_1
        cp T_ELSEIF
        jr nz,pp_bad
pe_1:   call pp_link
        pop af
        pop de
        inc hl
        ld a,(hl)
        dec hl
        cp T_ELSE
        jr z,pe_2
        ld a,T_ELSEIF
pe_2:   push hl
        push af
        jr pp_nx
pp_endif: pop af
        pop de
        cp T_IF
        jr z,pi_1
        cp T_ELSEIF
        jr z,pi_1
        cp T_ELSE
        jr nz,pp_bad
pi_1:   call pp_link
        jr pp_nx
pp_wend: pop af
        pop de
        cp T_WHILE
        jr nz,pp_bad
        call pp_link            ; WHILE -> WEND
        ex de,hl
        call pp_link            ; WEND -> WHILE
        ex de,hl
        jr pp_nx
pp_until: pop af
        pop de
        cp T_REPEAT
        jr nz,pp_bad
        ex de,hl
        call pp_link            ; UNTIL -> REPEAT
        ex de,hl
        jp pp_nx
pp_catch: pop af
        pop de
        cp T_TRY
        jr nz,pp_bad
        call pp_link
        ld a,T_CATCH
        push hl
        push af
        jp pp_nx
pp_endtry: pop af
        pop de
        cp T_CATCH
        jr nz,pp_bad
        call pp_link
        jp pp_nx
pp_endp: pop af                 ; closes a DEF only at the top of its body
        pop de
        push de
        push af
        cp T_DEF
        jp nz,pp_nx
        pop af
        pop de
        call pp_link
        jp pp_nx
pp_unc: ld (CURLN),hl
pp_bad: rst 8
        defb ERR_STRUC
; pp_link: the link slot of line DE := HL
pp_link: push de
        inc de
        inc de
        inc de
        ex de,hl
        ld (hl),e
        inc hl
        ld (hl),d
        ex de,hl
        pop de
        ret
pp_end: pop af                  ; the sentinel must be next
        pop de
        ld a,d
        or e
        ex de,hl
        jr nz,pp_unc            ; an unclosed block: CURLN = its line
        ld hl,(TMP)
        ld (hl),a
        inc hl
        ld (hl),a
        inc hl
        ld (VARSB),hl
        call clr_vars
        xor a
        ld (PPF),a
        pop hl
        ld (CURLN),hl
        ret

; ---------------------------------------------------- statements
st_print:
sp_lp:  call tk
        call is_end
        jp z,pr_eol
        cp ';'
        jr z,sp_semi
        cp ','
        jr z,sp_com
        cp $27
        jr z,sp_nl
        cp T_AT
        jr z,sp_at
        cp T_TAB
        jr z,sp_tab
        call ev_expr
        call ev_pop
        call is_str
        jr z,sp_str
        call fp_str
        call pr_buf
        jr sp_lp
sp_str: call s_print
        jr sp_lp
sp_semi: call skip1
        call tk
        call is_end
        ret z
        jr sp_lp
sp_com: ld a,6
        rst 16
        jr sp_semi
sp_nl:  call skip1
        call pr_eol
        call tk
        call is_end
        ret z
        jr sp_lp
sp_at:  call skip1
        call ev_expr
        call pop_u8
        ld a,22
        rst 16
        ld a,e
        rst 16
        call argn
        ld a,e
        rst 16
        jr sp_lp
sp_tab: call skip1
        ld a,'('
        call expect
        call ev_expr
        call pop_u8
        call rparen
        ld a,23
        rst 16
        ld a,e
        rst 16
        xor a
        rst 16
        jp sp_lp
; s_print: HL = string entry -> printed
s_print: inc hl
        inc hl
        ld b,(hl)
        inc hl
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        jp pr_buf
st_if:  call rd_link
si_go:  push de
        call ev_expr
        call pop_num
        call fp_tst0
        pop de
        push af
        call tk
        cp T_THEN
        jr z,si_one
        pop af
        ret nz                  ; true: on into the block
        ex de,hl                ; false: to the next branch
si_br:  call lk_chk
        inc hl
        ld a,(hl)
        dec hl
        cp T_ELSEIF
        jp nz,go_after          ; ELSE or ENDIF: carry on after it
        ld (CURLN),hl
        inc hl
        inc hl
        ld (CH_ADD),hl
        call rd_link
        jr si_go
si_one: call skip1              ; IF ... THEN statements [ELSE statements]
        pop af
        jp nz,go_st
        ld hl,(CH_ADD)
so_l:   ld a,(hl)
        cp 13
        jp z,go_next
        cp T_ELSE
        jr z,so_e
        call tk_len
        jr so_l
so_e:   inc hl
        ld (CH_ADD),hl
        call rd_link
        jp go_st
fp_tst0: ld a,(hl)              ; NZ if the number at HL is not zero
        or a
        ret nz
        inc hl
        inc hl
        ld a,(hl)
        inc hl
        or (hl)
        ret
; lk_chk: HL = a link: 0 means the block was never matched
lk_chk: ld a,h
        or l
        ret nz
        jp err_struc
st_elseif:                      ; reached at the end of a branch: to ENDIF
st_else: call rd_link
        ex de,hl
se_l:   call lk_chk
        inc hl
        ld a,(hl)
        dec hl
        cp T_ENDIF
        jp z,go_after
        inc hl
        inc hl
        inc hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        ex de,hl
        jr se_l
st_endif: ret
st_while: call rd_link
        push de
        call ev_expr
        call pop_num
        call fp_tst0
        pop hl
        ret nz
        call lk_chk
        jp go_after
st_wend: call rd_link
        ex de,hl
        call lk_chk
        jp go_line
st_repeat: ret
st_until: call rd_link
        push de
        call ev_expr
        call pop_num
        call fp_tst0
        pop hl
        ret nz
        call lk_chk
        jp go_after
st_for: call tk
        cp 1
        jp nz,err_syn
        call var_ref
        cp 2
        jp nc,err_type
        push hl
        push af
        ld a,'='
        call expect
        call ev_expr
        pop af
        pop hl
        push hl
        push af
        call val_store
        ld a,T_TO
        call expect
        call ev_expr
        call tk
        cp T_STEP
        jr nz,sf_one
        call skip1
        call ev_expr
        jr sf_fr
sf_one: ld de,1
        call push_int
sf_fr:  ld a,F_FOR
        ld c,18
        call cs_push
        inc hl
        pop af
        pop de
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ld (hl),a
        inc hl
        push hl                 ; limit, step go here
        call ev_2               ; HL = limit, DE = step
        call num_chk
        ex de,hl
        call num_chk
        pop bc
        push hl
        ex de,hl
        ld d,b
        ld e,c
        ld bc,5
        ldir
        pop hl
        ld bc,5
        ldir
        ex de,hl
        push hl
        call ev_pop
        call ev_pop
        pop hl
        dec hl                  ; fr_save stores from HL+1
        jp fr_save
; NEXT [v]: the frame is +1 var, +3 type, +4 limit, +9 step, +14 text,
; +16 line
st_next: ld hl,(CSP)
        ld de,(CSB)
        call cphd
        jp nc,err_next
        ld a,(hl)
        cp F_FOR
        jp nz,err_next
        call tk
        cp 1
        jr nz,sn_go
        push hl
        call var_ref
        ex de,hl
        ld hl,(CSP)
        inc hl
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        or a
        sbc hl,de
        pop hl
        jr z,sn_go
        ld (CH_ADD),hl          ; a different loop: leave it
        call cs_pop
        jr st_next
sn_go:  ld ix,(CSP)
        ld l,(ix+1)
        ld h,(ix+2)
        ld a,(ix+3)
        call val_push           ; v
        call ev_push
        ex de,hl
        push ix
        pop hl
        ld bc,9
        add hl,bc
        ld bc,5
        ldir                    ; step
        call ev_2
        call fp_add
        call ev_pop
        call ev_top
        push hl
        push ix
        pop hl
        ld bc,4
        add hl,bc
        ex de,hl
        pop hl
        call fp_cmp             ; v - limit
        ld b,(ix+10)            ; bit 7 = sign of step
        ld c,a
        ld l,(ix+1)
        ld h,(ix+2)
        ld a,(ix+3)
        push bc
        call val_store
        pop bc
        ld a,c
        bit 7,b
        jr z,sn_p
        neg
sn_p:   dec a
        jp z,cs_pop             ; past the limit: the loop is over
        ld l,(ix+14)
        ld h,(ix+15)
        ld (CH_ADD),hl
        ld l,(ix+16)
        ld h,(ix+17)
        ld (CURLN),hl
        ret
st_def: call rd_link
        ld a,d
        or e
        jp z,go_next
        ex de,hl
        jp go_after
st_endproc:
        call unw_pf
        cp F_PROC
        jp nz,err_endp
        jp fr_ret
st_return:
        call tk
        call is_end
        jr nz,sr_v
        ld hl,(CSP)             ; is it a PROC?
sr_l:   ld de,(CSB)
        call cphd
        jp nc,err_endp
        ld a,(hl)
        cp F_PROC
        jr z,st_endproc
        cp F_FN
        jr z,st_endfn
        call fr_len
        jr sr_l
sr_v:   call ev_expr
        jr fn_ret
st_endfn: ld de,0
        call push_int
fn_ret: call fn_unw
        ld e,(hl)
        inc hl
        ld d,(hl)
        ex de,hl
        ld sp,hl
        ret
fr_len: ld e,a
        ld d,0
        push hl
        ld hl,fsz-1
        add hl,de
        ld e,(hl)
        pop hl
        add hl,de
        ret
st_local: call tk
        cp 1
        jp nz,err_syn
        call var_ref
        call loc_save
        call tk
        cp ','
        ret nz
        call skip1
        jr st_local
st_try: call rd_link
        push de
        ld a,F_TRY
        ld c,7
        call cs_push
        pop de
        inc hl
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ex de,hl
        ld hl,2
        add hl,sp
        ex de,hl
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ld de,(VSP)
        ld (hl),e
        inc hl
        ld (hl),d
        ret
st_catch: call cs_pop           ; finished the TRY part: drop its frame
        jp c,err_struc
        cp F_TRY
        jr nz,st_catch
        call rd_link
        ex de,hl
        jp go_after
st_endtry: ret
err_struc: rst 8
        defb ERR_STRUC
st_error: call ev_expr
        call pop_u8
        ld a,e
err_a:  ld (ERR_NR),a
        ld sp,(ERR_SP)
        ret
st_end: pop af
        jp run_end
st_stop: rst 8
        defb ERR_STOP
st_dim: call tk
        cp 1
        jp nz,err_syn
        call var_find
        jp nc,err_redim
        ld a,(VTY)
        bit 2,a
        jp z,err_syn
        ld a,'('
        call expect
        ld hl,1
        ld (TMP),hl             ; element count
        ld hl,DIMB
        ld b,0
sd_l:   push hl
        push bc
        call ev_expr
        call pop_int
        or a
        jp nz,err_subs
        inc de
        pop bc
        pop hl
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        push hl
        push bc
        ld bc,(TMP)
        call mul16
        jp c,err_nomem
        ld (TMP),hl
        pop bc
        inc b
        ld a,b
        cp 4
        jp nc,err_subs
        call tk
        pop hl
        cp ','
        jr nz,sd_e
        push hl
        call skip1
        pop hl
        jr sd_l
sd_e:   push bc
        call rparen
        ld a,(VTY)
        and 3
        call tsz
        ld de,(TMP)
        call mul16
        jp c,err_nomem
        pop bc
        push bc
        ld c,b
        ld b,0
        add hl,bc
        add hl,bc
        inc hl
        jp c,err_nomem
        ld b,h
        ld c,l
        call var_new
        pop bc
        ld (hl),b
        inc hl
        ex de,hl
        ld hl,DIMB
        ld c,b
        sla c
        ld b,0
        ldir
        call tk
        cp ','
        ret nz
        call skip1
        jp st_dim
err_redim: rst 8
        defb ERR_REDIM
st_cls: jp CLS
st_run: ld a,1                  ; prepass always (it clears the variables)
        ld (PPF),a
        call prepass
        call stk_reset
        ld hl,OPROG
        jp go_line
st_list: ld hl,OPROG            ; the whole program, marker included
        ld b,0
        jp lst
st_auto: ld hl,EMODE            ; AUTO: typed lines go into the program
        set 0,(hl)
        ret
st_new: call p_new
        jp st_end
st_border: call ev_expr
        call pop_u8
        ld a,e
        and 7
        out ($FE),a
        add a,a
        add a,a
        add a,a
        ld (BORDCR),a
        ret
st_ink: ld c,16
        db $11                  ; ld de,nn: skips "ld c,17"
st_paper: ld c,17
        push bc
        call ev_expr
        call pop_u8
        pop bc
        ld a,e
        ld hl,ATTR_P
        call set_colour
        ld a,(ATTR_P)
        ld (ATTR_T),a
        ret
st_poke: call ev_expr
        call pop_int
        push de
        call argn
        pop hl
        ld (hl),e
        ret
st_wait: call ev_expr
        call pop_int
sw_l:   ld a,d
        or e
        ret z
        ei
        halt
        ld a,$7F
        in a,($FE)
        rra
        jr c,sw_n
        ld a,$FE
        in a,($FE)
        rra
        jr c,sw_n
        rst 8
        defb ERR_BREAK
sw_n:   dec de
        jr sw_l
st_randomize:
        ld de,0
        call tk
        call is_end
        jr z,sr_go
        call ev_expr
        call pop_int
sr_go:  jp fp_randomize

; ---------------------------------------------------- program lines (editor)
; p_ins: insert the tokenised line at TKB before line HL -> HL = it
p_ins:  push hl
        call clr_vars
        pop hl
        ld (TMP),hl
        ld de,(PEND)
        ex de,hl
        or a
        sbc hl,de
        inc hl
        push hl                 ; bytes to move up (sentinel included)
        ld hl,(TKB)
        ld c,(hl)
        ld b,0
        ld hl,(PEND)
        push hl
        add hl,bc
        push hl
        ld de,67
        add hl,de
        ld de,(HP)
        call cphd               ; it must stay clear of the heap
        jp nc,err_nomem
        pop de
        ld (PEND),de
        pop hl
        pop bc
        lddr
        ld de,(TMP)
        ld hl,(TKB)
        ld c,(hl)
        ld b,0
        ldir
        ld hl,(TMP)
        jr p_fix
; p_del: delete line HL (HL kept)
p_del:  ld c,(hl)
        ld b,0
        push hl
        push bc
        ld hl,(PEND)
        or a
        sbc hl,bc
        ld (PEND),hl
        pop bc
        pop de
        push de
        or a
        sbc hl,de
        inc hl
        push hl
        ld h,d
        ld l,e
        add hl,bc
        pop bc
        ldir
        pop hl
; p_fix: after a change: sentinel, empty DEF table, variables cleared
p_fix:  push hl
        ld hl,(PEND)
        xor a
        ld (hl),a
        inc hl
        ld (hl),a
        inc hl
        ld (hl),a
        inc hl
        ld (VARSB),hl
        inc a
        ld (PPF),a
        call clr_vars
        pop hl
        ret
; con_line: EBUF holds an entered line (0-terminated, length CON_LEN).
; Edit pending: it replaces the current line (empty: deletes it).
; AUTO mode: it goes in after the current line (empty: AUTO ends).
; Otherwise it runs at once.
con_line:
        call stk_reset
        ld hl,0
        ld (CURLN),hl
        ld a,(CON_LEN)
        ld c,a
        ld hl,EMODE
        bit 1,(hl)
        jr nz,cl_rep
        bit 0,(hl)
        jr nz,cl_ins
        inc c
        dec c
        ret z
        ld de,(TKB)
        call cl_tok
        jp run_direct
cl_ins: inc c
        dec c
        jr nz,ci_go
        res 0,(hl)
        ret
ci_go:  call cl_ptk
        ld hl,(CURL)
        ld a,h
        or l
        ld hl,OPROG
        jr z,cin_1
        ld hl,(CURL)
        call nxl
cin_1:   call p_ins
cl_cur: ld (CURL),hl
        jp elist
cl_rep: res 1,(hl)
        inc c
        dec c
        jr nz,cr_go
        ld hl,(CURL)            ; empty: delete the line
        call p_del
        call prv
        jr cl_cur
cr_go:  call cl_ptk
        ld hl,(CURL)
        call p_del
        call p_ins
        jr cl_cur
; cl_ptk: tokenise EBUF as a program line at TKB: [length] tokens [length]
cl_ptk: ld de,(TKB)
        inc de
        call cl_tok
        ld a,l
        ld de,(TKB)
        ld (de),a
        dec hl
        add hl,de
        ld (hl),a
        ret
; cl_tok: tokenise EBUF to DE -> HL = bytes from TKB + 1 (at most 255)
cl_tok: ld hl,EBUF
        call tokenise
        ld hl,(TKB)
        ex de,hl
        or a
        sbc hl,de
        inc hl
        ld a,h
        or a
        jp nz,err_nomem
        ret
; con_err: RST 8 lands here (SP = ERR_SP).  A TRY on the control stack
; catches the error; otherwise it is reported with its line.
con_err:
        ld sp,LINEBUF+64        ; keep clear of the stack being unwound
        ld a,(ERR_NR)
        ld (ERRV),a
        cp ERR_BREAK
        jr z,ce_rep
        cp ERR_STOP
        jr z,ce_rep
ce_l:   call cs_pop
        jr c,ce_rep
        cp F_TRY
        jr nz,ce_l
        inc hl
        ld e,(hl)               ; CATCH line
        inc hl
        ld d,(hl)
        inc hl
        ld c,(hl)
        inc hl
        ld b,(hl)
        inc hl
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        ld (VSP),hl
        ld h,b
        ld l,c
        ld sp,hl
        ex de,hl
        call nxl
        jp run_line
ce_rep: ld sp,(RAMTOP)
        call err_show
        ld hl,(CURLN)
        ld a,h
        or l
        jp z,console
        ld (CURL),hl            ; the marker moves to the failing line
        ex de,hl
        ld hl,OPROG             ; line number = position in the program
        ld bc,1
cr_l:   call cphd
        jr nc,cr_p
        call nxl
        inc bc
        jr cr_l
cr_p:   push bc
        ld hl,msg_line
        call pr_msg
        pop hl
        call pr_dec
        jp console
msg_line: defm ", line"
        defb ' '+$80
m_bas_e:
