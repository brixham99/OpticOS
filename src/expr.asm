; expr.asm - expression evaluator and PRINT (phase 2 seed of phase 3).
; Works on plain text at CH_ADD for now; phase 3 feeds it tokens.
; Values are 5-byte numbers on the value stack VSTK (VSP = next free).
; Grammar (Sinclair-like priorities):
;   expr  = term { (+|-) term }
;   term  = fact { (*|/) fact }
;   fact  = - fact | prim { ^ uprim }
;   uprim = - uprim | prim
;   prim  = number | ( expr ) | PI | RND | function uprim
m_exp_s:
err_syn: rst 8
        defb ERR_SYN
; nxc: skip spaces at CH_ADD -> A = next character
nxc:    ld hl,(CH_ADD)
nx_1:   ld a,(hl)
        cp ' '
        jr nz,nx_2
        inc hl
        jr nx_1
nx_2:   ld (CH_ADD),hl
        ret
; skip1: step over the current character
skip1:  ld hl,(CH_ADD)
        inc hl
        ld (CH_ADD),hl
        ret
; ev_push: HL = new top slot on the value stack
ev_push: ld hl,(VSP)
        push hl
        ld de,5
        add hl,de
        ld a,l
        cp (VSTKE & 255)+1
        jr nc,err_syn           ; too deeply nested
        ld (VSP),hl
        pop hl
        ret
; ev_top: HL = top value
ev_top: ld hl,(VSP)
        ld de,-5
        add hl,de
        ret
; ev_bin: BC = fp routine; applies it to the top two values, pops one
ev_bin: call ev_top
        ld (VSP),hl
        ex de,hl
        ld hl,-5
        add hl,de
        push bc
        ret

ev_expr: call ev_term
ee_l:   call nxc
        ld bc,fp_add
        cp '+'
        jr z,ee_op
        ld bc,fp_sub
        cp '-'
        ret nz
ee_op:  push bc
        call skip1
        call ev_term
        pop bc
        call ev_bin
        jr ee_l
ev_term: call ev_fact
et_l:   call nxc
        ld bc,fp_mul
        cp '*'
        jr z,et_op
        ld bc,fp_div
        cp '/'
        ret nz
et_op:  push bc
        call skip1
        call ev_fact
        pop bc
        call ev_bin
        jr et_l
ev_fact: call nxc
        cp '-'
        jr nz,ev_pow
        call skip1
        call ev_fact
ev_ngt: call ev_top
        jp fp_neg
ev_pow: call ev_prim
ep_l:   call nxc
        cp '^'
        ret nz
        call skip1
        call ev_upr
        ld bc,fp_pow
        call ev_bin
        jr ep_l
ev_upr: call nxc
        cp '-'
        jr nz,ev_prim
        call skip1
        call ev_upr
        jr ev_ngt
ev_prim: call nxc
        cp '('
        jr nz,epr_1
        call skip1
        call ev_expr
        call nxc
        cp ')'
        jp nz,err_syn
        jp skip1
epr_1:  cp '.'
        jr z,epr_n
        sub '0'
        cp 10
        jr nc,epr_f
epr_n:  call ev_push
        ex de,hl
        ld hl,(CH_ADD)
        call fp_val
        jp c,err_syn
        ld (CH_ADD),hl
        ret
epr_f:  ld de,fn_tab             ; function or constant name
        ld hl,(CH_ADD)
epr_l:  ld a,(de)
        or a
        jp z,err_syn
        push hl
        call cd_match
        jr z,epr_g
        pop hl
        inc de
        inc de
        jr epr_l
epr_g:  pop af
        ld (CH_ADD),hl
        ex de,hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        bit 7,d
        jr nz,epr_0
        push de                 ; function of one argument
        call ev_upr
        call ev_top
        ret                     ; into the fp routine with HL = top
epr_0:  res 7,d                 ; no argument: routine fills a new slot
        push de
        jp ev_push
; constant PI
fp_pi:  ex de,hl
        ld hl,kt_tab+5*(K_PI-6)
        ld bc,5
        ldir
        ret
fn_tab: defm "SQ"
        defb 'R'+$80
        defw fp_sqr
        defm "SI"
        defb 'N'+$80
        defw fp_sin
        defm "CO"
        defb 'S'+$80
        defw fp_cos
        defm "TA"
        defb 'N'+$80
        defw fp_tan
        defm "AT"
        defb 'N'+$80
        defw fp_atn
        defm "AS"
        defb 'N'+$80
        defw fp_asn
        defm "AC"
        defb 'S'+$80
        defw fp_acs
        defm "EX"
        defb 'P'+$80
        defw fp_exp
        defm "L"
        defb 'N'+$80
        defw fp_ln
        defm "LO"
        defb 'G'+$80
        defw fp_log
        defm "IN"
        defb 'T'+$80
        defw fp_int
        defm "AB"
        defb 'S'+$80
        defw fp_abs
        defm "SG"
        defb 'N'+$80
        defw fp_sgn
        defm "P"
        defb 'I'+$80
        defw fp_pi+$8000
        defm "RN"
        defb 'D'+$80
        defw fp_rnd+$8000
        defb 0

; cd_match: HL = text, DE = bit-7-terminated word (upper case).
; Z = match with HL after the word; DE is after the word either way.
cd_match:
        ld a,(hl)
        cp 'a'
        jr c,cdm_1
        cp 'z'+1
        jr nc,cdm_1
        sub 32
cdm_1:  ld c,a
        ld a,(de)
        inc de
        ld b,a
        and $7F
        cp c
        jr nz,cdm_n
        inc hl
        bit 7,b
        jr z,cd_match
        xor a
        ret
cdm_n:  bit 7,b
        jr nz,cdm_x
        ld a,(de)
        inc de
        ld b,a
        jr cdm_n
cdm_x:  or 1
        ret

; ---------------------------------------------------- PRINT
; PRINT items: "text", expressions; ';' joins, ',' moves to the next
; 16-column zone; a trailing ; or , keeps the cursor on the line.
cmd_print:
pr_lp:  call nxc
        or a
        jr z,pc_nl
        cp ';'
        jr z,pr_sep
        cp ','
        jr z,pr_cm
        cp '"'
        jr z,pr_str
        ld hl,VSTK
        ld (VSP),hl
        call ev_expr
        ld hl,VSTK
        call fp_str
pr_s1:  ld a,(hl)
        push hl
        push bc
        rst 16
        pop bc
        pop hl
        inc hl
        djnz pr_s1
pr_aft: call nxc                ; after an item: ; , or the end
        or a
        jr z,pc_nl
        cp ';'
        jr z,pr_sep
        cp ','
        jp nz,err_syn
pr_cm:  ld a,' '                ; to the next 16-column zone
        rst 16
        ld a,(S_POSN)
        and 15
        jr nz,pr_cm
pr_sep: call skip1
        call nxc
        or a
        ret z
        jr pr_lp
pc_nl:  ld a,13
        rst 16
        ret
pr_str: call skip1
ps_l:   ld hl,(CH_ADD)
        ld a,(hl)
        or a
        jp z,err_syn            ; no closing quote
        inc hl
        ld (CH_ADD),hl
        cp '"'
        jr nz,ps_c
        ld a,(hl)               ; "" inside a string is one quote
        cp '"'
        jr nz,pr_aft
        inc hl
        ld (CH_ADD),hl
ps_c:   rst 16
        jr ps_l
m_exp_e:
