; fptrans.asm - OpticOS transcendental functions (phase 2).
; They are written as short programs for a tiny internal byte-code that
; works on the unpacked accumulator FA; see docs/maths.md for the codes.
; Coefficients are OpticOS's own Chebyshev fits (tools/fpcoef.py).
LD_     equ $00                 ; FA = src
ST_     equ $20                 ; Tn = FA
ADD_    equ $40                 ; FA = FA + src
SUB_    equ $60                 ; FA = FA - src
MUL_    equ $80                 ; FA = FA * src
DIV_    equ $A0                 ; FA = FA / src
POLY_   equ $C0                 ; FA = polynomial in FA, n coefficients follow
END_    equ $E0                 ; back to Z80 code after this byte
NEG_    equ $E1                 ; FA = -FA
        include "gen/kequ.inc"  ; src 0-6 = T0-T6, 6+ = constants
m_fpt_s:
; fu_run: call fu_run, then byte-code, then END_; Z80 code carries on
; after the END_ byte.
fu_run: pop hl
fr_lp:  ld a,(hl)
        inc hl
        ld c,a
        and $E0
        cp $E0
        jr z,fr_x
        cp $C0
        jr z,fr_poly
        push hl
        ld b,a
        ld a,c
        and $1F
        ld c,a
        ld a,b
        cp ST_
        jr z,fr_st
        ld de,FA
        or a
        jr z,fr_ld
        ld de,FB
fr_ld:  push bc
        ld a,c
        call fu_src
        pop af                  ; A = op
        or a
        jr z,fr_nx
        rrca
        rrca
        rrca
        rrca
        ld e,a
        ld d,0
        ld hl,fr_tab-4
        add hl,de
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        call jphl
fr_nx:  pop hl
        jr fr_lp
fr_st:  ld a,c
        call fu_tadr
        ex de,hl
        ld hl,FA
        ld bc,7
        ldir
        jr fr_nx
fr_x:   ld a,c
        and $1F
        jr nz,fr_neg
        jp (hl)
fr_neg: ld a,(FA+6)
        xor $80
        ld (FA+6),a
        jr fr_lp
fr_tab: defw fu_add, fu_sub, fu_mul, fu_div
; POLY n: Horner, x = FA, coefficients highest power first
fr_poly: ld a,c
        and $1F
        ld b,a
        push hl
        push bc
        ld hl,FA
        ld de,T6
        ld bc,7
        ldir
        pop bc
        pop hl
        ld de,FA
        push bc
        call fu_upi
        pop bc
fp_lp:  dec b
        jp z,fr_lp
        push bc
        push hl
        ld hl,T6
        ld de,FB
        ld bc,7
        ldir
        call fu_mul
        pop hl
        ld de,FB
        call fu_upi
        push hl
        call fu_add
        pop hl
        pop bc
        jr fp_lp
fu_upi: push hl                 ; unpack (HL) to DE, HL += 5
        call fu_unpack
        pop hl
        ld de,5
        add hl,de
        ret
; fu_tadr: A = temporary number -> HL = its address
fu_tadr: add a,a
        add a,a
        add a,a
        add a,FT & 255
        ld l,a
        ld h,FT >> 8
        ret
; fu_src: A = source (0-6 temporary, 6+ constant), DE = destination
fu_src: cp 6
        jr nc,fsr_k
        call fu_tadr
        ld bc,7
        ldir
        ret
fsr_k:  sub 6
        ld l,a
        add a,a
        add a,a
        add a,l
        ld l,a
        ld h,0
        ld bc,kt_tab
        add hl,bc
        jp fu_unpack
; fu_cmpk: compare FA with constant A (result as fu_cmp)
fu_cmpk: ld de,FB
        call fu_src
        jp fu_cmp

; ---------------------------------------------------- packed wrappers
; HL = number, replaced by the function's value
fp_sqr: ld bc,fu_sqr
        jr fp_un
fp_sin: ld bc,fu_sin
        jr fp_un
fp_cos: ld bc,fu_cos
        jr fp_un
fp_tan: ld bc,fu_tan
        jr fp_un
fp_atn: ld bc,fu_atn
        jr fp_un
fp_exp: ld bc,fu_exp
        jr fp_un
fp_log: ld bc,fu_log
        jr fp_un
fp_ln:  ld bc,fu_ln
fp_un:  push hl
        push bc
        ld de,FA
        call fu_unpack
        pop hl
        call jphl
        pop hl
        jp fp_stA
; fp_rnd: HL = destination for the next random number, 0 <= RND < 1
fp_rnd: push hl
        call fu_rnd
        pop hl
        jp fp_stA

; ---------------------------------------------------- SIN COS TAN
; fs_red: FA = x -> FA = x - q*pi/2 (two-part pi/2), A = q AND 3
fs_red: call fu_run
        defb ST_+0, MUL_+K_TWOPI, END_
        call fu_fix
        jp c,err_arg            ; |x| above about 102900
        ld a,e
        bit 7,c
        jr z,fsr_1
        neg
fsr_1:  and 3
        push af
        ld hl,FA
        call fu_from16
        call fu_run
        defb ST_+1, MUL_+K_PI2H, ST_+2, LD_+0, SUB_+2, ST_+0
        defb LD_+1, MUL_+K_PI2L, ST_+2, LD_+0, SUB_+2, END_
        pop af
        ret
fu_cos: ld a,1
        jr fs_g
fu_sin: xor a
fs_g:   push af
        call fs_red
        pop bc
        add a,b
        push af
        rra
        jr c,fs_c
        call fs_sinr
        jr fs_k
fs_c:   call fs_cosr
fs_k:   pop af
        and 2
        ret z
        jr fu_neg
fs_sinr: call fu_run            ; sin r = r * S(r*r)
        defb ST_+0, MUL_+0, POLY_+5
        include "gen/poly_sin.inc"
        defb MUL_+0, END_
        ret
fs_cosr: call fu_run            ; cos r = C(r*r)
        defb ST_+0, MUL_+0, POLY_+6
        include "gen/poly_cos.inc"
        defb END_
        ret
fu_tan: call fs_red
        push af
        call fu_run
        defb ST_+3, END_
        call fs_sinr
        call fu_run
        defb ST_+4, LD_+3, END_
        call fs_cosr
        pop af
        rra
        jr c,ft_odd
        call fu_run             ; sin r / cos r
        defb ST_+5, LD_+4, DIV_+5, END_
        ret
ft_odd: call fu_run             ; -cos r / sin r
        defb DIV_+4, NEG_, END_
        ret
fu_neg: ld a,(FA+6)
        xor $80
        ld (FA+6),a
        ret

; ---------------------------------------------------- ATN
fu_atn: ld hl,FA+6
        ld a,(hl)
        ld (hl),0
        push af                 ; sign of x
        ld a,K_ONE
        call fu_cmpk
        push af                 ; A = 1 if |x| > 1
        dec a
        jr nz,fa_1
        call fu_run             ; x = 1/x
        defb ST_+3, LD_+K_ONE, DIV_+3, END_
fa_1:   ld a,K_TAN15
        call fu_cmpk
        dec a
        push af                 ; Z if x > tan(pi/12)
        jr nz,fa_2
        call fu_run             ; x = (x*sqr 3 - 1) / (x + sqr 3)
        defb ST_+3, MUL_+K_SQ3, SUB_+K_ONE, ST_+4, LD_+3, ADD_+K_SQ3, ST_+5
        defb LD_+4, DIV_+5, END_
fa_2:   call fu_run             ; atn t = t * A(t*t)
        defb ST_+0, MUL_+0, POLY_+6
        include "gen/poly_atn.inc"
        defb MUL_+0, END_
        pop af
        jr nz,fa_3
        call fu_run
        defb ADD_+K_PI6, END_
fa_3:   pop af
        dec a
        jr nz,fa_4
        call fu_run
        defb NEG_, ADD_+K_PI2, END_
fa_4:   pop af
        ld (FA+6),a
        ret

; ---------------------------------------------------- SQR
; Newton's method from a linear first guess, three steps.  Uses T0, T1.
fu_sqr: ld a,(FA+5)
        or a
        ret z
        ld a,(FA+6)
        or a
        jp nz,err_arg
        ld a,(FA+5)
        sub 128
        ld b,128
        bit 0,a
        jr z,fq_1
        dec b
        inc a
fq_1:   push af
        ld a,b
        ld (FA+5),a
        call fu_run
        defb ST_+0, MUL_+K_SQA, ADD_+K_SQB, ST_+1
        defb LD_+0, DIV_+1, ADD_+1, MUL_+K_HALF, ST_+1
        defb LD_+0, DIV_+1, ADD_+1, MUL_+K_HALF, ST_+1
        defb LD_+0, DIV_+1, ADD_+1, MUL_+K_HALF, END_
        pop af
        sra a
        ld hl,FA+5
        add a,(hl)
        ld (hl),a
        ret

; ---------------------------------------------------- EXP LN LOG
; EXP x = 2^n * e^f, n = nearest x/ln 2, f = x - n*ln 2 (two-part ln 2)
fu_exp: call fu_run
        defb ST_+0, MUL_+K_LOG2E, END_
        call fu_fix
        jr c,fe_big
        ld a,d
        or a
        jr nz,fe_big
        push de
        push bc
        ld hl,FA
        call fu_from16
        call fu_run
        defb ST_+1, MUL_+K_LN2H, ST_+2, LD_+0, SUB_+2, ST_+0
        defb LD_+1, MUL_+K_LN2L, ST_+2, LD_+0, SUB_+2, POLY_+9
        include "gen/poly_exp.inc"
        defb END_
        pop bc
        pop de
        ld a,(FA+5)
        ld l,a
        ld h,0
        bit 7,c
        jr nz,fe_n
        add hl,de
        jr fe_s
fe_n:   or a
        sbc hl,de
fe_s:   ld b,h
        ld c,l
        jp fu_sete
fe_big: ld a,(FA+6)
        or a
        jp z,err_ovf
        jp fu_zero
; LN x = e*ln 2 + LN m, m in [0.707, 1.414); LN m = s*P(s*s), s = (m-1)/(m+1)
fu_ln:  ld a,(FA+6)
        or a
        jp nz,err_arg
        ld a,(FA+5)
        or a
        jp z,err_arg
        sub 128
        ld e,a
        ld hl,(FA+3)
        ld bc,$B504
        or a
        sbc hl,bc
        ld a,128
        jr nc,fl_1
        inc a
        dec e
fl_1:   ld (FA+5),a
        push de
        call fu_run
        defb ST_+0, SUB_+K_ONE, ST_+1, LD_+0, ADD_+K_ONE, ST_+2, LD_+1, DIV_+2
        defb ST_+0, MUL_+0, POLY_+5
        include "gen/poly_ln.inc"
        defb MUL_+0, ST_+3, END_
        pop de
        ld a,e
        ld c,0
        or a
        jp p,fl_2
        neg
        ld c,$80
fl_2:   ld e,a
        ld d,0
        ld hl,FA
        call fu_from16
        call fu_run
        defb ST_+1, MUL_+K_LN2L, ADD_+3, ST_+3, LD_+1, MUL_+K_LN2H, ADD_+3, END_
        ret
fu_log: call fu_ln
        call fu_run
        defb MUL_+K_LN10I, END_
        ret

; ---------------------------------------------------- RND, RANDOMIZE
; 32-bit xorshift (13, 17, 5) in RNDS; RND = state / 2^32
fu_rnd: ld hl,(RNDS)             ; DE:HL = state
        ld de,(RNDS+2)
        ld b,13
        call xs_l
        ld b,17
        call xs_r
        ld b,5
        call xs_l
        ld (RNDS),hl
        ld (RNDS+2),de
        ld (FA+1),hl
        ld (FA+3),de
        xor a
        ld (FA),a
        ld (FA+6),a
        ld a,128
        ld (FA+5),a
        jp fu_norm
; xs_l / xs_r: DE:HL ^= DE:HL shifted B bits left / right
xs_l:   push de
        push hl
xl_1:   add hl,hl
        rl e
        rl d
        djnz xl_1
xs_x:   pop bc
        ld a,l
        xor c
        ld l,a
        ld a,h
        xor b
        ld h,a
        pop bc
        ld a,e
        xor c
        ld e,a
        ld a,d
        xor b
        ld d,a
        ret
xs_r:   push de
        push hl
xr_1:   srl d
        rr e
        rr h
        rr l
        djnz xr_1
        jr xs_x
; fp_randomize: DE = seed (0 = use FRAMES)
fp_randomize:
        ld a,d
        or e
        jr nz,frz_1
        ld de,(FRAMES)
frz_1:  ld (SEED),de
        ld (RNDS),de
        ld a,e
        cpl
        ld (RNDS+2),a
        ld a,d
        cpl
        ld (RNDS+3),a
        ret

; ---------------------------------------------------- power
; fp_pow: HL = x (receives x^y), DE = y.  Integer y (small-int form):
; repeated squaring; otherwise EXP (y * LN x), x > 0.  0^y: 0 for y > 0,
; division by zero for y < 0; 0^0 = 1.
fp_pow: ld a,(de)
        or a
        jr nz,fpw_f
        push hl                 ; x
        ex de,hl
        call si_val             ; C:D:E = y
        call si_mag             ; DE = |y|, C kept
        pop hl
        push hl
        ld a,c
        push af                 ; sign of y
        push de
        ld de,FA
        call fu_unpack
        call fu_run
        defb ST_+0, LD_+K_ONE, ST_+1, END_
        pop de
fpw_l:  ld a,d
        or e
        jr z,fpw_d
        srl d
        rr e
        jr nc,fpw_s
        push de
        call fu_run
        defb LD_+1, MUL_+0, ST_+1, END_
        pop de
fpw_s:  ld a,d
        or e
        jr z,fpw_d
        push de
        call fu_run
        defb LD_+0, MUL_+0, ST_+0, END_
        pop de
        jr fpw_l
fpw_d:  call fu_run
        defb LD_+1, END_
        pop af
        or a
        jr z,fpw_st
        call fu_run
        defb ST_+1, LD_+K_ONE, DIV_+1, END_
fpw_st: pop hl
        jp fp_stA
fpw_f:  push hl
        call fu_ld2
        ld hl,FB
        ld de,FT+8*5
        ld bc,7
        ldir                    ; T5 = y
        ld a,(FA+5)
        or a
        jr z,fpw_0
        call fu_ln
        call fu_run
        defb MUL_+5, END_
        call fu_exp
        jr fpw_st
fpw_0:  ld a,(FB+6)
        or a
        jp nz,err_div0
        jr fpw_st
m_fpt_e:
m_fpk_s:
        include "gen/kconst.inc"
m_fpk_e:
