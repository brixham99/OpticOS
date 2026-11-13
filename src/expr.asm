; expr.asm - OpticBASIC expression evaluator (phase 3), on tokens at
; CH_ADD, results on the value stack.  Priorities, loosest first:
;   OR XOR / AND / = <> < > <= >= / << >> / + - / * / DIV MOD /
;   unary - + NOT / ^ (right-associative) / primaries
m_exp_s:
ev_expr: ld hl,d_or
lvl:    push hl
        call lv_nx
lv_l:   pop hl
        push hl
        inc hl
        inc hl
lv_s:   ld c,(hl)
        inc c
        dec c
        jr z,lv_x
        inc hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        push hl
        ld hl,(CH_ADD)
        ld a,(hl)
        pop hl
        cp c
        jr nz,lv_s
        push de
        rst $20
        pop de
        pop hl
        push hl
        push de
        call lv_nx
        pop hl
        call jphl
        jr lv_l
lv_x:   pop hl
        ret
lv_nx:  ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        jp (hl)
d_or:   defw ev_and
        defb T_OR
        defw op_or
        defb T_XOR
        defw op_xor
        defb 0
ev_and: ld hl,d_and
        jr lvl
d_and:  defw ev_cmp
        defb T_AND
        defw op_and
        defb 0
ev_cmp: ld hl,d_cmp
        jr lvl
d_cmp:  defw ev_sh
        defb '='
        defw op_eq
        defb T_NE
        defw op_ne
        defb '<'
        defw op_lt
        defb '>'
        defw op_gt
        defb T_LE
        defw op_le
        defb T_GE
        defw op_ge
        defb 0
ev_sh:  ld hl,d_sh
        jr lvl
d_sh:   defw ev_add
        defb T_SHL
        defw op_shl
        defb T_SHR
        defw op_shr
        defb 0
ev_add: ld hl,d_add
        jr lvl
d_add:  defw ev_mul
        defb '+'
        defw op_add
        defb '-'
        defw op_sub
        defb 0
ev_mul: ld hl,d_mul
        jp lvl
d_mul:  defw ev_una
        defb '*'
        defw op_mul
        defb '/'
        defw op_div
        defb T_DIV
        defw op_idiv
        defb T_MOD
        defw op_mod
        defb 0

ev_una: rst $18
        cp '-'
        jr z,eu_neg
        cp '+'
        jr z,eu_pl
        cp T_NOT
        jr nz,ev_pow
        rst $20
        call ev_una
        call pop_int
        ld a,e
        cpl
        ld e,a
        ld a,d
        cpl
        ld d,a
        jp push_int
eu_pl:  rst $20
        jr ev_una
eu_neg: rst $20
        call ev_una
        call ev_top
        call num_chk
        jp fp_neg
ev_pow: call ev_prim
        rst $18
        cp '^'
        ret nz
        rst $20
        call ev_una
        ld bc,fp_pow
        jr bin_n

; ---------------------------------------------------- operators
op_sub: ld bc,fp_sub
        jr bin_n
op_mul: ld bc,fp_mul
        jr bin_n
op_div: ld bc,fp_div
bin_n:  push bc
        call ev_2
        call num_chk
        ex de,hl
        call num_chk
        ex de,hl
        pop bc
        jr bn_c
op_add: call ev_2
        call ty2
        or a
        jp nz,s_cat
        call ev_2
        ld bc,fp_add
bn_c:   call jpbc
        jp ev_pop
jpbc:   push bc
        ret
; int2: two numbers as 16-bit integers -> DE = left, BC = right,
; HL = left slot (now the top)
int2:   call pop_int
        push de
        call ev_top
        push hl
        call num_chk
        call fp_get_int
        jp c,err_ovf
        pop hl
        pop bc
        ret
op_and: call int2
        ld a,e
        and c
        ld e,a
        ld a,d
        and b
        jr oi_d
op_or:  call int2
        ld a,e
        or c
        ld e,a
        ld a,d
        or b
        jr oi_d
op_xor: call int2
        ld a,e
        xor c
        ld e,a
        ld a,d
        xor b
oi_d:   ld d,a
        jp fp_set_int
op_shl: call int2
        inc c
os_l:   dec c
        jr z,oi_s
        sla e
        rl d
        jr os_l
op_shr: call int2
        inc c
or_l:   dec c
        jr z,oi_s
        sra d
        rr e
        jr or_l
oi_s:   jp fp_set_int
op_idiv: call idiv
        jp fp_set_int
op_mod: call idiv
        ld d,b
        ld e,c
        jp fp_set_int
; idiv: signed 16-bit division of the top two -> DE = quotient,
; BC = remainder (sign of the dividend), HL = result slot
idiv:   call int2
        ld a,b
        or c
        jp z,err_div0
        push hl
        ld a,d
        xor b
        push af                 ; quotient sign (bit 7)
        push de                 ; remainder sign (bit 7 of D)
        bit 7,d
        call nz,neg_de
        bit 7,b
        jr z,id_1
        xor a
        sub c
        ld c,a
        sbc a,a
        sub b
        ld b,a
id_1:   ld hl,0                 ; HL = remainder, DE = dividend -> quotient
        ld a,16
id_l:   sla e
        rl d
        adc hl,hl
        sbc hl,bc
        jr nc,id_2
        add hl,bc
        jr id_3
id_2:   inc e
id_3:   dec a
        jr nz,id_l
        ld b,h
        ld c,l
        pop af
        bit 7,a
        jr z,id_4
        xor a
        sub c
        ld c,a
        sbc a,a
        sub b
        ld b,a
id_4:   pop af
        rla
        call c,neg_de
        pop hl
        ret
neg_de: xor a
        sub e
        ld e,a
        sbc a,a
        sub d
        ld d,a
        ret
; comparisons -> -1 (true) or 0
op_eq:  ld c,2
        jr op_c
op_ne:  ld c,5
        jr op_c
op_lt:  ld c,1
        jr op_c
op_gt:  ld c,4
        jr op_c
op_le:  ld c,3
        jr op_c
op_ge:  ld c,6
op_c:   push bc
        call cmp2
        pop bc
        inc a                   ; 0 1 2 for < = >
        ld b,a
        inc b
        ld a,$80
oc_m:   rlca
        djnz oc_m
        and c
        ld de,0
        jr z,oc_w
        dec de
oc_w:   call fp_set_int
        jp ev_pop
; cmp2: compare the two top entries (numbers or strings) -> A = $FF, 0, 1
; for <, =, >; HL = the lower entry
cmp2:   call ev_2
        push hl
        call ty2
        or a
        jr nz,c2_s
        call fp_cmp
        pop hl
        ret
c2_s:   call s_cmp
        pop hl
        ret
; s_cmp: HL, DE = string entries -> A = $FF, 0, 1 for <, =, >
s_cmp:  inc hl
        inc hl
        inc de
        inc de
        ld b,(hl)
        ld a,(de)
        ld c,a
        push bc
        ld a,b
        cp c
        jr c,sc_0
        ld a,c
sc_0:   ld b,a
        inc hl
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        ex de,hl
        inc hl
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        ex de,hl
        inc b
scm_l:   dec b
        jr z,sc_len
        ld a,(de)
        cp (hl)                 ; right - left
        inc hl
        inc de
        jr z,scm_l
        pop bc
        jr z,scm_r               ; (never: Z handled above)
        ccf                     ; CF: left < right
        jr scm_r
sc_len: pop bc
        ld a,b
        cp c
        jr z,sc_eq
scm_r:   ld a,$FF
        ret c
        ld a,1
        ret
sc_eq:  xor a
        ret
; s_cat: join the top two strings
s_cat:  call ev_2
        inc de
        inc de
        ld a,(de)
        or a
        jp z,ev_pop             ; + ""
        ld c,a
        inc hl
        inc hl
        ld a,(hl)
        or a
        jr z,sk_r               ; "" + b
        add a,c
        jr c,err_strl
        push af
        ld de,0
        call s_alloc
        push de
        push de
        call ev_2
        ex (sp),hl
        ex de,hl
        ex (sp),hl
        call sk_cp
        pop hl
        call sk_cp
        pop bc
        pop af
        push bc
        push af
        call ev_2
        pop af
        pop de
        inc hl
        inc hl
        ld (hl),a
        inc hl
        ld (hl),e
        inc hl
        ld (hl),d
        jp ev_pop
sk_r:   call ev_2
        ex de,hl
        ld bc,5
        ldir
        jp ev_pop
; sk_cp: HL = string entry, DE = destination -> its chars copied, DE past
sk_cp:  inc hl
        inc hl
        ld c,(hl)
        ld b,0
        inc hl
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        inc c
        dec c
        ret z
        ldir
        ret
err_strl: rst 8
        defb ERR_STRL

; ---------------------------------------------------- primaries
ev_prim: rst $18
        cp '('
        jr nz,ep_1
        rst $20
        call ev_expr
rparen: ld a,')'
        jp expect
ep_1:   cp 1
        jp z,ep_id
        cp 5
        jr z,ep_fl
        jr nc,ep_2
        cp 2
        jp c,err_syn
        inc hl                  ; 16-bit literal: unsigned small integer
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        ld (CH_ADD),hl
        jp push_u
ep_fl:  inc hl
        push hl
        ld de,5
        add hl,de
        ld (CH_ADD),hl
        call ev_push
        ex de,hl
        pop hl
        ld bc,5
        ldir
        ret
ep_2:   cp 6
        jr nz,ep_3
        inc hl                  ; string literal: points into the line
        ld c,(hl)
        inc hl
        push hl
        ld b,0
        add hl,bc
        ld (CH_ADD),hl
        call ev_push
        pop de
        ld (hl),b
        inc hl
        ld (hl),1
        inc hl
        ld (hl),c
        inc hl
        ld (hl),e
        inc hl
        ld (hl),d
        ret
ep_3:   cp T_FN
        jr z,ep_fn
        sub T_SQR
        jp c,err_syn
        cp T_PI-T_SQR
        jr nc,ep_o
        push af                 ; numeric function of one argument
        rst $20
        call ev_una
        call ev_top
        call num_chk
        pop af
        ld de,fnu_tab
        jr ep_j
ep_o:   sub T_PI-T_SQR
        cp T_FREE-T_PI+1
        jp nc,err_syn
        push af
        rst $20
        pop af
        call ev_top
        ld de,fno_tab
ep_j:   push hl
        add a,a
        ld l,a
        ld h,0
        add hl,de
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        ex (sp),hl
        ret
ep_fn:  rst $20
        rst $18
        cp 1
        jp nz,err_syn
        call var_find
        jp fn_call
ep_id:  call var_find
        jr c,ep_nf
        bit 2,a
        call nz,arr_elem
        jp val_push
ep_nf:  jp fn_call              ; not a variable: perhaps an FN by name
; push_u: DE = 0..65535 -> pushed
push_u: call ev_push
        ld (hl),0
        inc hl
        ld (hl),0
        inc hl
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ld (hl),0
        ret
; push_int: DE = signed 16-bit -> pushed
push_int: call ev_push
        jp fp_set_int
push_a: ld e,a
        ld d,0
        jr push_u
; str_arg: a string operand (as for a unary function) on top -> HL = it
str_una: call ev_una
        call ev_top
        jp str_chk
; parenthesised arguments
arg1s:  ld a,'('                ; ( string
        call expect
        call ev_expr
        call ev_top
        jp str_chk
argn:   ld a,','                ; , number -> DE (0-255 checked: A = 0)
        call expect
ev_u8:  call ev_expr
pop_u8: call pop_int
        or d
        jp nz,err_arg
        ret

; ---------------------------------------------------- functions
f_pi:   call ev_push
fp_pi:  ex de,hl                ; HL = destination
        ld hl,kt_tab+5*(K_PI-6)
        ld bc,5
        ldir
        ret
f_rnd:  call ev_push
        call fp_rnd
        rst $18
        cp '('
        ret nz
        rst $20
        call ev_expr
        call rparen
        call ev_2               ; RND(n): 1 + INT(RND * n)
        push hl
        call fp_mul
        pop hl
        push hl
        call fp_int
        pop hl
        ld de,kt_tab
        call fp_add
        jp ev_pop
f_len:  call str_una
        inc hl
        inc hl
        ld a,(hl)
fl_set: call ev_pop
        jr push_a
f_asc:  call str_una
        inc hl
        inc hl
        ld a,(hl)
        or a
        jr z,fl_set
        inc hl
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        ld a,(hl)
        jr fl_set
f_peek: call ev_una
        call pop_int
        ld a,(de)
        jp push_a
f_err:  ld a,(ERRV)
        jp push_a
f_true: ld de,-1
        jp push_int
f_false: ld de,0
        jp push_int
f_frames: ld de,(FRAMES)
        jp push_u
f_lefts: call arg1s
        call argn
        call rparen
        call ev_top
        inc hl
        inc hl
        ld a,e
        cp (hl)
        ret nc
        ld (hl),a
        ret
f_rights: call arg1s
        call argn
        call rparen
        call ev_top
        inc hl
        inc hl
        ld a,(hl)
        sub e
        ret c
        ret z
        ld (hl),e
fs_adv: inc hl                  ; move the pointer on by A
        add a,(hl)
        ld (hl),a
        ret nc
        inc hl
        inc (hl)
        ret
f_mids: call arg1s              ; MID$(s$, start [, length])
        call argn
        ld a,e
        or a
        jp z,err_arg
        push de
        ld e,255
        rst $18
        cp ','
        call z,argn
        call rparen
        pop bc                  ; C = start, E = length
        call ev_top
        inc hl
        inc hl
        ld a,(hl)
        dec c
        sub c                   ; characters from start on
        jr nc,fm_1
        xor a
fm_1:   cp e
        jr c,fm_2
        ld a,e
fm_2:   ld (hl),a
        ld a,c
        jr fs_adv
f_chrs: call ev_una
        call pop_u8
        ld a,e
        push af
        call ev_push
        ld a,1
        jr fc_go
f_strs: call ev_una
        call ev_top
        call num_chk
        call fp_str
        push hl
        push bc
        ld a,b
        call fc_new
        pop bc
        pop hl
        ld c,b
        ld b,0
        ldir
        ret
fc_go:  call fc_new
        pop af
        ld (de),a
        ret
; fc_new: replace the top entry with a new A-character string -> DE = chars
fc_new: push af
        ld de,0
        call s_alloc
        call ev_top
        pop af
        ld (hl),0
        inc hl
        ld (hl),1
        inc hl
        ld (hl),a
        inc hl
        ld (hl),e
        inc hl
        ld (hl),d
        ret
f_inkeys: call ev_push
        ld b,5
fi_z:   ld (hl),0
        inc hl
        djnz fi_z
        dec hl
        dec hl
        dec hl
        dec hl
        inc (hl)                ; "" so far
        ld hl,FLAGS
        bit 5,(hl)
        ret z
        res 5,(hl)
        ld a,(LAST_K)
        push af
        ld a,1
        jr fc_go
f_val:  call str_una
fv_top: inc hl                  ; HL = string entry on top -> its value
        inc hl
        ld a,(hl)
        cp 32
        jr c,fv_1
        ld a,31
fv_1:   ld c,a
        ld b,0
        inc hl
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        ld de,LINEBUF
        inc c
        dec c
        jr z,fv_2
        ldir
fv_2:   xor a
        ld (de),a
        call ev_top
        push hl
        ld b,5
fv_z:   ld (hl),a
        inc hl
        djnz fv_z
        pop de
        ld hl,LINEBUF
fv_sp:  ld a,(hl)
        cp ' '
        jr nz,fv_3
        inc hl
        jr fv_sp
fv_3:   cp '-'
        push af
        jr nz,fv_4
        inc hl
fv_4:   push de
        call fp_val
        pop hl
        pop af
        ret nz
        jp fp_neg
f_max:  ld c,4
        db $11                  ; ld de,nn: skips "ld c,1"
f_min:  ld c,1
        push bc
        ld a,'('
        call expect
        call ev_expr
mx_l:   rst $18
        cp ','
        jr nz,fm_e
        rst $20
        call ev_expr
        call ev_2
        call num_chk
        ex de,hl
        call num_chk
        push hl
        push de
        call fp_cmp             ; new vs best
        pop de
        pop hl
        inc a
        ld b,a
        inc b
        ld a,$80
fx_m:   rlca
        djnz fx_m
        pop bc
        push bc
        and c
        jr z,fx_k
        ld bc,5
        ldir
fx_k:   call ev_pop
        jr mx_l
fm_e:   pop bc
        jp rparen
m_exp_e:
