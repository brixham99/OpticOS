; list.asm - OpticBASIC LIST: detokeniser with indenting (phase 3)
m_lst_s:
; ---------------------------------------------------- LIST
; pr_kw: print keyword A
pr_kw:  ld hl,kw_tab
        sub $80
        jr z,pk_p
        ld b,a
pk_s:   bit 7,(hl)
        inc hl
        jr z,pk_s
        djnz pk_s
pk_p:   ld a,(hl)
        and $7F
        call pr_ch
        bit 7,(hl)
        inc hl
        jr z,pk_p
        ret
pr_ch:  ld (LSTCH),a
        rst 16
        ret
; pr_sep: a space between two words (or after a keyword)
pr_sep: ld a,(LSTCH)
        cp ' '+$80
        jr z,ps_y
        call is_alnum
        jr nc,ps_y
        cp '"'
        jr z,ps_y
        cp ')'
        jr z,ps_y
        cp '$'
        jr z,ps_y
        cp '%'
        ret nz
ps_y:   ld a,' '
        jr pr_ch
; ln_has: HL = line -> Z if token A appears in it (HL kept)
ln_has: push hl
        ld c,a
        inc hl
lh_lp:  ld a,(hl)
        cp c
        jr z,lh_e
        cp 13
        jr z,lh_n
        call tk_len
        jr lh_lp
lh_n:   or a
lh_e:   pop hl
        ret
; ln_open: HL = line -> A = +1 if it opens a block, 0 otherwise; first
; token in B
ln_open: inc hl
        ld b,(hl)
        dec hl
        ld a,b
        cp T_IF
        jr z,lo_if
        cp T_FOR
        jr z,lo_for
        cp T_DEF
        jr z,lo_def
        ld a,b
        push hl
        ld hl,lo_tab
        ld c,7
lo_l:   cp (hl)
        jr z,lo_y
        inc hl
        dec c
        jr nz,lo_l
        pop hl
        xor a
        ret
lo_y:   pop hl
        ld a,1
        ret
lo_if:  ld a,T_THEN
        jr lo_x
lo_for: ld a,T_NEXT
        jr lo_x
lo_def: ld a,'='
lo_x:   call ln_has
        ld a,0
        ret z
        inc a
        ret
lo_tab: defb T_WHILE,T_REPEAT,T_TRY,T_CASE,T_ELSEIF  ; and the first two of lc_tab
lc_tab: defb T_WHEN,T_OTHERWISE,T_ENDCASE,T_ELSE,T_CATCH,T_ELSEIF,T_ENDIF,T_WEND,T_UNTIL,T_NEXT,T_ENDPROC,T_ENDFN,T_ENDTRY
; ln_close: B = first token -> Z if the line closes (or splits) a block
ln_close: ld hl,lc_tab
        ld c,13
lc_l:   ld a,b
        cp (hl)
        ret z
        inc hl
        dec c
        jr nz,lc_l
        inc c
        ret
; list_line: HL = line -> printed with indent (LSTLV) and canonical spacing
list_line:
        push hl
        call ln_open
        ld c,a
        push bc
        call ln_close
        ld hl,LSTLV
        jr nz,ll_1
        ld a,(hl)
        or a
        jr z,ll_1
        dec (hl)
ll_1:   ld a,(hl)
        add a,a
        jr z,ll_3
        ld b,a
ll_2:   ld a,' '
        rst 16
        djnz ll_2
ll_3:   pop bc
        ld a,b
        cp T_ELSE
        jr z,ll_4
        cp T_CATCH
        jr nz,ll_5
ll_4:   ld c,1
ll_5:   ld a,(hl)
        add a,c
        ld (hl),a
        ld a,' '
        ld (LSTCH),a
        pop hl
        inc hl
ll_lp:  ld a,(hl)
        cp 13
        jp z,pr_eol
        inc hl
        cp $80
        jr c,ll_nk
        push hl
        push af
        call pr_sep
        pop af
        push af
        call pr_kw
        pop af
        pop hl
        cp T_REM
        jp z,ll_rw
        cp T_SQR
        jr nc,ll_lp
        ld a,' '+$80            ; a space is owed after the keyword
        ld (LSTCH),a
        jr ll_lp
ll_nk:  cp 8
        jp nc,ll_ch
        dec a
        jr z,ll_id
        cp 6
        jr z,ll_lk
        cp 5
        jr z,ll_st
        cp 4
        jr z,ll_fl
        push af                 ; 2 3 4: 16-bit literal
        call pr_sep
        pop af
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        push hl
        ex de,hl
        cp 1
        jr z,ll_dec
        ld c,'$'
        ld b,4
        cp 2
        jr z,ll_hx
        ld c,'%'
        ld b,16
ll_hx:  push hl
        ld a,c
        call pr_ch
        pop hl
        call pr_base
        jr ll_px
ll_dec: call pr_dec
ll_px:  ld a,'0'
        ld (LSTCH),a
        pop hl
        jr ll_lp
ll_lk:  inc hl
        inc hl
        jr ll_lp
ll_fl:  call pr_sep
        push hl
        call fp_str
        call pr_buf
        pop hl
        ld de,5
        add hl,de
        jp ll_lp
ll_st:  call pr_sep
        ld a,'"'
        call pr_ch
        ld b,(hl)
        inc hl
        inc b
        jr ls_n
ls_l:   ld a,(hl)
        inc hl
        push af
        rst 16
        pop af
        cp '"'
        jr nz,ls_n
        rst 16
ls_n:   djnz ls_l
        ld a,'"'
        call pr_ch
        jp ll_lp
ll_id:  call pr_sep
        ld c,(hl)               ; type
        inc hl
        inc hl
        ld b,(hl)
        inc hl
        call pr_buf
        ld a,c
        and 3
        jr z,li_1
        dec a
        ld a,'%'
        jr z,li_0
        ld a,'$'
li_0:   call pr_ch
li_1:   ld a,'a'
        ld (LSTCH),a
        jp ll_lp
ll_ch:  sub 8
        cp 5
        jr nc,ll_c1
        push hl
        add a,a
        ld e,a
        ld d,0
        ld hl,op2_tab
        add hl,de
        ld a,(hl)
        call pr_ch
        inc hl
        ld a,(hl)
        pop hl
        jr ll_c2
ll_c1:  add a,8
        cp T_CMT
        jr nz,ll_c0
        ld a,$27
        rst 16
        jr ll_rw
ll_c0:  ld c,a
        ld a,(LSTCH)
        cp ' '+$80
        ld a,c
        jr nz,ll_c2
        cp ':'                  ; the owed space is dropped before these
        jr z,ll_c2
        cp ','
        jr z,ll_c2
        cp ';'
        jr z,ll_c2
        cp ')'
        jr z,ll_c2
        ld a,' '
        rst 16
        ld a,c
ll_c2:  call pr_ch
        jp ll_lp
ll_rw:  ld a,(hl)               ; comment text to the end of the line
        cp 13
        jr z,pr_eol
        rst 16
        inc hl
        jr ll_rw
op2_tab: defb "<=>=<><<>>"
; pr_buf: print B characters from HL (HL past them, B = 0)
pr_buf: inc b
        dec b
        ret z
pb_l:   ld a,(hl)
        inc hl
        call pr_ch
        djnz pb_l
        ret
pr_eol:  ld a,13
        rst 16
        ret
; pr_base: HL = value, B = 4 (hex) or 16 (binary) digits, leading 0s dropped
pr_base: ld c,0
        ld d,b
pbs_l:  ld a,d
        cp 4
        ld a,0
        jr nz,pbs_b
        add hl,hl
        rla
        add hl,hl
        rla
        add hl,hl
        rla
pbs_b:  add hl,hl
        rla
        ld e,a
        or c
        jr z,pbs_n
        ld c,1
        ld a,e
        add a,'0'
        cp '9'+1
        jr c,pbs_p
        add a,7
pbs_p:  rst 16
pbs_n:  djnz pbs_l
        dec c
        ret z
        ld a,'0'
        rst 16
        ret
m_lst_e:
