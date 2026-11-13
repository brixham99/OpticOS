; legacy.asm - the legacy loader shim (spec 3.4): loads a Sinclair-
; tokenised BASIC program at $5CCB and interprets the loader subset.
; Keyword token values and the tape header layout are published facts.
TK_VAL   equ $B0
TK_PEEK  equ $BE
TK_USR   equ $C0
TK_BIN   equ $C4
TK_AT    equ $AC
TK_SCR   equ $AA
TK_CODE  equ $AF
LG_PSEP  equ $5B4E              ; PRINT: last item was a separator
m_leg_s:

; LOAD "" typed at the console: fetch a program and run it
lg_cmd_load:
        ld a,$FF
        ld (LG_NAME),a
lg_prog:
        xor a
        ld (LG_WANT),a
        call lg_fetch
        ld hl,LEGPROG           ; PROG, VARS for PEEK 23635-style loaders
        ld (PROG),hl
        ld de,(HDRBUF+15)
        add hl,de
        ld (VARS),hl
        ld hl,(HDRBUF+13)       ; auto-start line
        bit 7,h
        jp nz,con_ok
        call lg_goto
        jp lg_stmt

m_leg_e1:
m_tcmd_s:
; lg_fetch: find a header of type LG_WANT (and name LG_NAME unless $FF),
; printing each header seen, then load its data block.
lg_fetch:
lf_hdr: ld ix,HDRBUF
        ld de,17
        xor a
        scf
        call LD_BYTES
        jr nc,lf_hdr
        ld a,2
        call CHAN_OPEN
        ld a,(HDRBUF)
        ld hl,msg_prog
        or a
        jr z,lf_p
        ld hl,msg_bytes
lf_p:   call pr_msgs
        ld hl,HDRBUF+1
        ld b,10
lf_n:   ld a,(hl)
        rst 16
        inc hl
        djnz lf_n
        ld a,13
        rst 16
        ld a,(LG_WANT)
        ld hl,HDRBUF
        cp (hl)
        jr nz,lf_hdr
        ld a,(LG_NAME)
        inc a
        jr z,lf_ok
        ld hl,LG_NAME
        ld de,HDRBUF+1
        ld b,10
lf_c:   ld a,(de)
        cp (hl)
        jr nz,lf_hdr
        inc hl
        inc de
        djnz lf_c
lf_ok:  ld de,(HDRBUF+11)       ; length
        ld ix,LEGPROG
        ld a,(HDRBUF)
        or a
        jr z,lf_ld
        ld ix,(HDRBUF+13)       ; CODE: start from the header ...
        ld hl,(LG_DEST)         ; ... unless one was given
        ld a,h
        or l
        jr z,lf_ld
        push hl
        pop ix
lf_ld:  ld a,$FF
        scf
        call LD_BYTES
        ret c
        rst 8
        defb ERR_TAPE

m_tcmd_e:
m_leg_s2:
; lg_goto: HL = line number; set up the first line >= it
lg_goto:
        ex de,hl
        ld hl,(PROG)
lgg_lp: push hl
        ld bc,(VARS)
        and a
        sbc hl,bc
        pop hl
        jp nc,con_ok            ; ran off the end
        ld a,(hl)
        cp d
        jr c,lgg_nx
        jr nz,lg_line
        inc hl
        ld a,(hl)
        dec hl
        cp e
        jr nc,lg_line
lgg_nx: inc hl
        inc hl
        ld c,(hl)
        inc hl
        ld b,(hl)
        inc hl
        add hl,bc
        jr lgg_lp
lg_line:                        ; HL = start of a line
        inc hl
        inc hl
        ld c,(hl)
        inc hl
        ld b,(hl)
        inc hl
        ld (CH_ADD),hl
        add hl,bc
        ld (NXTLIN),hl
        ret

; ---- statement loop
lg_ret: ld (CH_ADD),hl
lg_stmt:
        ld hl,(ATTR_P)          ; each statement starts with permanent colours
        ld (ATTR_T),hl
        ld hl,(CH_ADD)
ls_sk:  ld a,(hl)
        cp ' '
        jr z,ls_inc
        cp ':'
        jr nz,ls_2
ls_inc: inc hl
        jr ls_sk
ls_2:   cp 13
        jr nz,ls_3
        ld hl,(NXTLIN)
        push hl
        ld bc,(VARS)
        and a
        sbc hl,bc
        pop hl
        jp nc,con_ok
        call lg_line
        jr lg_stmt
ls_3:   inc hl
        ld (CH_ADD),hl
        ld hl,lg_stab
ls_f:   ld c,(hl)
        inc c
        dec c
        jr z,lg_unsup
        inc hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        cp c
        jr nz,ls_f
        ld hl,lg_ret
        push hl
        push de
        ld hl,(CH_ADD)
        ret                     ; handler: HL = text after the keyword
lg_unsup:
        rst 8
        defb ERR_LEG

lg_stab:
        defb $E7
        defw lg_border
        defb $D9
        defw lg_ink
        defb $DA
        defw lg_paper
        defb $DB
        defw lg_flash
        defb $DC
        defw lg_bright
        defb $FB
        defw lg_cls
        defb $FD
        defw lg_clear
        defb $F4
        defw lg_poke
        defb $F9
        defw lg_rand
        defb $EF
        defw lg_load
        defb $F5
        defw lg_print
        defb $EA
        defw lg_rem
        defb $EC
        defw lg_gotos
        defb $F7
        defw lg_run
        defb 0

lg_border:
        call lg_expr
        ld a,e
        and 7
        out ($FE),a
        ld b,a
        rlca
        rlca
        rlca
        ld c,a
        ld a,b
        cp 4
        ld a,7                  ; light borders get black lower-screen ink
        jr c,lb_1
        xor a
lb_1:   or c
        ld (BORDCR),a
        ret
lg_ink: ld c,16
        jr lg_colr
lg_paper:
        ld c,17
        jr lg_colr
lg_flash:
        ld c,18
        jr lg_colr
lg_bright:
        ld c,19
lg_colr:
        push bc
        call lg_expr
        pop bc
        push hl
        ld a,e
        ld hl,ATTR_P
        call set_colour
        pop hl
        ret
lg_cls: push hl
        call CLS
        pop hl
        ret
lg_clear:                       ; CLEAR n: RAMTOP = n, fresh stack below it
        call lg_expr
        ld (CH_ADD),hl
        ex de,hl
        ld (RAMTOP),hl
        ld sp,hl
        ld hl,con_err
        push hl
        ld (ERR_SP),sp
        ld hl,(CH_ADD)
        jp lg_ret
lg_poke:
        call lg_expr
        push de
        call lg_comma
        call lg_expr
        ld a,e
        pop de
        ld (de),a
        ret
lg_rand:
        call lg_skip
        cp ':'
        jr z,lr_f
        cp 13
        jr z,lr_f
        call lg_expr
        ld a,d
        or e
        jr nz,lr_s
lr_f:   ld de,(FRAMES)
lr_s:   ld (SEED),de
        ret
lg_rem: ld hl,(NXTLIN)
        dec hl                  ; the line's ENTER
        ret
lg_run: call lg_skip
        ld de,0
        cp ':'
        jr z,lg_gt
        cp 13
        jr z,lg_gt
lg_gotos:
        call lg_expr
lg_gt:  ex de,hl
        call lg_goto
        ld hl,(CH_ADD)
        ret

; LOAD "name" [CODE [start[,len]] | SCREEN$]
lg_load:
        call lg_skip
        cp '"'
        jp nz,lg_unsup
        inc hl
        ld de,LG_NAME
        ld a,(hl)
        cp '"'
        ld a,$FF
        jr z,ll_any
        push hl
        ld h,d
        ld l,e
        ld b,10
ll_sp:  ld (hl),' '
        inc hl
        djnz ll_sp
        pop hl
        ld b,10
ll_nm:  ld a,(hl)
        cp '"'
        jr z,ll_q
        inc hl
        ld (de),a
        inc de
        djnz ll_nm
ll_nq:  ld a,(hl)
        inc hl
        cp '"'
        jr nz,ll_nq
        jr ll_kw
ll_any: ld (de),a
ll_q:   inc hl
ll_kw:  ld de,0
        ld (LG_DEST),de
        call lg_skip
        cp TK_SCR
        jr z,ll_scr
        cp TK_CODE
        jr z,ll_code
        pop de                  ; a program: chain to it
        jp lg_prog
ll_scr: inc hl
        ld de,$4000
        ld (LG_DEST),de
        jr ll_go
ll_code:
        inc hl
        call lg_skip
        cp ':'
        jr z,ll_go
        cp 13
        jr z,ll_go
        call lg_expr
        ld (LG_DEST),de
        call lg_skip
        cp ','
        jr nz,ll_go
        inc hl
        call lg_expr            ; length: the header's length is used
ll_go:  ld a,3
        ld (LG_WANT),a
        push hl
        call lg_fetch
        pop hl
        ret

; PRINT with strings, numbers, AT, TAB-free separators ; , '
lg_print:
        ld a,2
        call CHAN_OPEN
        xor a
lp_set: ld (LG_PSEP),a
lp_lp:  call lg_skip
        cp 13
        jr z,lp_end
        cp ':'
        jr z,lp_end
        inc hl
        cp ';'
        ld b,1
        jr z,lp_sep
        cp ','
        jr z,lp_com
        cp $27
        jr z,lp_apo
        cp '"'
        jr z,lp_str
        cp TK_AT
        jr z,lp_at
        dec hl
        call lg_expr
        push hl
        ex de,hl
        call pr_dec
        pop hl
        xor a
        jr lp_set
lp_com: ld a,6
        rst 16
        ld a,1
        jr lp_set
lp_apo: ld a,13
        rst 16
        ld a,1
        jr lp_set
lp_sep: ld a,b
        jr lp_set
lp_str: ld a,(hl)
        inc hl
        cp '"'
        jr z,lp_s2
        rst 16
        jr lp_str
lp_s2:  ld a,(hl)               ; "" inside a string prints one quote
        cp '"'
        jr nz,lp_set0
        rst 16
        inc hl
        jr lp_str
lp_set0:
        xor a
        jr lp_set
lp_at:  call lg_expr
        push de
        call lg_comma
        call lg_expr
        ld a,22
        rst 16
        pop bc
        ld a,c
        rst 16
        ld a,e                  ; 32-column loaders: double the column
        add a,a
        rst 16
        ld a,1
        jr lp_set
lp_end: ld a,(LG_PSEP)
        or a
        ret nz
        ld a,13
        rst 16
        ret

; ---- expressions: 16-bit integers.  Numbers use the hidden 5-byte form.
lg_expr:
        call lg_term
lx_lp:  call lg_skip
        cp '+'
        jr z,lx_add
        cp '-'
        ret nz
        inc hl
        push de
        call lg_term
        ex (sp),hl
        and a
        sbc hl,de
        jr lx_res
lx_add: inc hl
        push de
        call lg_term
        ex (sp),hl
        add hl,de
lx_res: ex de,hl
        pop hl
        jr lx_lp
lg_term:
        call lg_fact
lt_lp:  call lg_skip
        cp '*'
        ret nz
        inc hl
        push de
        call lg_fact
        ex (sp),hl
        ld b,h                  ; HL = BC * DE
        ld c,l
        ld hl,0
        ld a,16
lt_m:   add hl,hl
        ex de,hl
        add hl,hl
        ex de,hl
        jr nc,lt_n
        add hl,bc
lt_n:   dec a
        jr nz,lt_m
        ex de,hl
        pop hl
        jr lt_lp
lg_fact:
        call lg_skip
        inc hl
        cp '('
        jr z,lf_par
        cp TK_USR
        jr z,lf_usr
        cp TK_PEEK
        jr z,lf_peek
        cp TK_VAL
        jr z,lf_val
        cp TK_BIN
        jr z,lg_fact
        cp '0'
        jr c,lf_bad
        cp '9'+1
        jr nc,lf_bad
lf_num: ld a,(hl)
        inc hl
        cp $0E
        jr nz,lf_num
        ld a,(hl)               ; small-integer form: 00 sign lo hi 00
        or a
        jr nz,lf_bad
        inc hl
        inc hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        inc hl
        ret
lf_bad: jp lg_unsup
lf_par: call lg_expr
        call lg_skip
        cp ')'
        jr nz,lf_bad
        inc hl
        ret
lf_peek:
        call lg_fact
        ld a,(de)
        ld e,a
        ld d,0
        ret
lf_usr: call lg_fact            ; call machine code: BC = address in,
        push hl                 ; BC = result out
        ld hl,lfu_r
        push hl
        push de
        ld b,d
        ld c,e
        ld iy,ERR_NR
        ret
lfu_r:  ld d,b
        ld e,c
        pop hl
        ret
lf_val: call lg_skip            ; VAL "digits"
        cp '"'
        jr nz,lf_bad
        inc hl
        ld de,0
lv_lp:  ld a,(hl)
        inc hl
        cp '"'
        ret z
        sub '0'
        cp 10
        jr nc,lf_bad
        push hl
        ld h,d
        ld l,e
        add hl,hl
        add hl,hl
        add hl,de
        add hl,hl
        ld e,a
        ld d,0
        add hl,de
        ex de,hl
        pop hl
        jr lv_lp

lg_comma:
        call lg_skip
        cp ','
        jr nz,lf_bad
        inc hl
        ret
lg_skip:
        ld a,(hl)
        cp ' '
        ret nz
        inc hl
        jr lg_skip

m_leg_e2:
m_num_s:
; pr_dec: HL unsigned, through RST 16, no leading zeros
pr_dec: ld e,0
        ld bc,-10000
        call pd_dig
        ld bc,-1000
        call pd_dig
        ld bc,-100
        call pd_dig
        ld bc,-10
        call pd_dig
        ld a,l
        add a,'0'
        rst 16
        ret
pd_dig: ld a,'0'-1
pd_l:   inc a
        add hl,bc
        jr c,pd_l
        sbc hl,bc
        cp '0'
        jr nz,pd_p
        bit 0,e
        ret z
pd_p:   ld e,1
        rst 16
        ret
m_num_e:
