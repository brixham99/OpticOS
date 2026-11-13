; fpconv.asm - OpticOS number <-> text (phase 2).
m_fpv_s:
; fp_str: HL = number -> HL = NBUF, B = length.  Up to 9 significant
; digits; fixed notation for 1E-5 <= |x| < 1E9, otherwise E notation
; (1.5E+12, 2E-7).  Integers print exactly.
fp_str: push hl
        ld hl,NBUF
        ld (NBP),hl
        pop hl
        ld a,(hl)
        or a
        jr nz,fs_fl
        ; small int: magnitude into FA+1..4, 5 digits
        call si_val
        ld a,c
        or a
        jr z,fs_ip
        call si_ngd
        ld a,'-'
        call nb_put
fs_ip:  ld a,d
        or e
        jr nz,fs_i2
        ld a,'0'
        call nb_put
        jp fs_end
fs_i2:  ld (FA+1),de
        ld hl,0
        ld (FA+3),hl
        ld a,4
        ld b,5
        jr fs_dg
fs_fl:  ld de,FA
        call fu_unpack
        ld hl,FA+6
        ld a,(hl)
        ld (hl),0
        or a
        ld a,'-'
        call nz,nb_put
        ld a,(FA+5)             ; estimate d = floor((exp-129)*77/256)
        dec a
        ld e,a
        ld d,0
        ld bc,77
        call mul16
        ld bc,-128*77
        add hl,bc
        ld a,h
        ld (NDE),a
        neg
        add a,8
        call fu_scl             ; FA = x * 10^(8-d)
fs_a1:  ld a,K_E9
        call fu_cmpk
        jp m,fs_a2
        call fu_run
        defb DIV_+K_TEN, END_
        ld hl,NDE
        inc (hl)
        jr fs_a1
fs_a2:  ld a,K_E8
        call fu_cmpk
        jp p,fs_a3
        call fu_run
        defb MUL_+K_TEN, END_
        ld hl,NDE
        dec (hl)
        jr fs_a2
fs_a3:  ld a,(FA+5)             ; to a 32-bit integer, rounded
        sub 160
        neg
        ld hl,FA
        call fu_shr
        ld a,(FA)
        add a,a
        jr nc,fs_a4
        ld hl,FA+1
        ld b,4
fs_inc: inc (hl)
        jr nz,fs_a4
        inc hl
        djnz fs_inc
fs_a4:  ld a,(NDE)
        ld b,9
; fs_dg: B digits of the integer in FA+1..4 into NDIG; A = power of ten
; of the first digit
fs_dg:  ld (NDE),a
        ld a,b
        ld (NCNT),a
        ld hl,NDIG-1
        ld e,b
        ld d,0
        add hl,de
fs_d1:  push bc
        push hl
        call div10
        pop hl
        add a,'0'
        ld (hl),a
        dec hl
        pop bc
        djnz fs_d1
        ld a,(FA+1)             ; 10^9 after rounding up: digits are 1000...
        or a
        jr z,fs_lz
        ld a,'1'
        ld (NDIG),a
        ld hl,NDE
        inc (hl)
fs_lz:  ld a,(NDIG)             ; drop leading zeros (integers)
        cp '0'
        jr nz,fs_tz
        ld hl,NDIG+1
        ld de,NDIG
        ld bc,8
        ldir
        ld hl,NDE
        dec (hl)
        ld hl,NCNT
        dec (hl)
        jr fs_lz
fs_tz:  ld a,(NCNT)             ; drop trailing zeros
        ld b,a
        ld e,a
        ld d,0
        ld hl,NDIG-1
        add hl,de
fs_t1:  ld a,(hl)
        cp '0'
        jr nz,fs_t2
        dec hl
        djnz fs_t1
fs_t2:  ld hl,NDIG              ; B = significant digits
        ld a,(NDE)
        add a,5
        cp 14
        jr nc,fs_e              ; E notation
        sub 5
        jp m,fs_neg
        inc a                   ; digits before the point
        ld c,a
fs_f1:  ld a,(hl)
        call nb_put
        inc hl
        dec b
        dec c
        jr nz,fs_f1
        ld a,b
        or a
        jr z,fs_end
        jp m,fs_end
fs_fr:  ld a,'.'
        call nb_put
fs_rest: ld a,(hl)
        call nb_put
        inc hl
        djnz fs_rest
fs_end: ld hl,(NBP)
        ld de,NBUF
        or a
        sbc hl,de
        ld b,l
        ex de,hl
        ret
fs_neg: ld c,a                  ; 0.000ddd
        ld a,'0'
        call nb_put
        ld a,'.'
        call nb_put
fs_n1:  inc c
        jr z,fs_rest
        ld a,'0'
        call nb_put
        jr fs_n1
fs_e:   ld a,(hl)               ; d.dddE+nn
        call nb_put
        inc hl
        dec b
        jr z,fs_e1
        ld a,'.'
        call nb_put
fs_e0:  ld a,(hl)
        call nb_put
        inc hl
        djnz fs_e0
fs_e1:  ld a,'E'
        call nb_put
        ld a,(NDE)
        ld c,'+'
        or a
        jp p,fs_e2
        neg
        ld c,'-'
fs_e2:  ld b,a
        ld a,c
        call nb_put
        ld a,b
        ld c,'0'-1
fs_e3:  inc c
        sub 10
        jr nc,fs_e3
        add a,'0'+10
        ld b,a
        ld a,c
        cp '0'
        call nz,nb_put
        ld a,b
        call nb_put
        jr fs_end
nb_put: push hl
        ld hl,(NBP)
        ld (hl),a
        inc hl
        ld (NBP),hl
        pop hl
        ret
; div10: 32-bit integer at FA+1..4 /= 10, A = remainder
div10:  ld hl,FA+1
        ld b,32
        xor a
d10_l:  sla (hl)
        inc hl
        rl (hl)
        inc hl
        rl (hl)
        inc hl
        rl (hl)
        dec hl
        dec hl
        dec hl
        rla
        cp 10
        jr c,d10_n
        sub 10
        inc (hl)
d10_n:  djnz d10_l
        ret

; fu_scl: FA = FA * 10^A (A signed).  10^k is built by squaring in T4/T5
; (|k| > 31 is done in steps of 10^32 so it cannot overflow); uses T3-T5.
fu_scl: or a
        ret z
        jp p,fsc_p
        cp -31
        jr nc,fsc_go
        add a,32
        ld c,-32
        jr fsc_ch
fsc_p:  cp 32
        jr c,fsc_go
        sub 32
        ld c,32
fsc_ch: push af                 ; scale by 10^(+-32) first, then the rest
        ld a,c
        call fsc_go
        pop af
        jr fu_scl
fsc_go: or a                    ; S = direction
        push af
        call fu_run
        defb ST_+3, LD_+K_TEN, ST_+4, LD_+K_ONE, ST_+5, END_
        pop af
        push af
        jp p,fsc_1
        neg
fsc_1:  ld b,a
fsc_l:  srl b
        jr nc,fsc_2
        push bc
        call fu_run
        defb LD_+5, MUL_+4, ST_+5, END_
        pop bc
fsc_2:  ld a,b
        or a
        jr z,fsc_d
        push bc
        call fu_run
        defb LD_+4, MUL_+4, ST_+4, END_
        pop bc
        jr fsc_l
fsc_d:  call fu_run
        defb LD_+3, END_
        pop af
        jp m,fsc_v
        call fu_run
        defb MUL_+5, END_
        ret
fsc_v:  call fu_run
        defb DIV_+5, END_
        ret

; fp_val: HL = text, DE = destination -> number stored, HL just past it;
; CF set (nothing stored) if the text does not start with a number.
; Accepts 12, 1.5, .5, 3E8, 2.5e-3 (no sign; minus is an operator).
fp_val: push de
        xor a
        ld (VDX),a
        ld (FA+5),a
        ld (FA+6),a
        ld c,a                  ; bit 0 digit seen, bit 1 after point
vl_lp:  ld a,(hl)
        cp '.'
        jr nz,vl_d
        bit 1,c
        jr nz,vl_ne
        set 1,c
        inc hl
        jr vl_lp
vl_d:   sub '0'
        cp 10
        jr nc,vl_ne
        set 0,c
        push hl
        push bc
        ld b,a
        ld a,(FA+5)
        cp 164
        jr nc,vl_skp            ; 11 digits kept, the rest only counted
        push bc
        call fu_run
        defb MUL_+K_TEN, END_
        pop bc
        ld e,b
        ld d,0
        ld c,d
        ld hl,FB
        call fu_from16
        call fu_add
        pop bc
        push bc
        bit 1,c
        jr z,vl_nx
        ld hl,VDX
        dec (hl)
        jr vl_nx
vl_skp: pop bc
        push bc
        bit 1,c
        jr nz,vl_nx
        ld hl,VDX
        inc (hl)
vl_nx:  pop bc
        pop hl
        inc hl
        jr vl_lp
vl_ne:  bit 0,c
        jr z,vl_no
        ld a,(hl)
        or $20
        cp 'e'
        jr nz,vl_sc
        push hl                 ; exponent part
        inc hl
        ld a,(hl)
        ld b,0                  ; sign
        cp '+'
        jr z,vl_es
        cp '-'
        jr nz,vl_e1
        dec b
vl_es:  inc hl
vl_e1:  ld a,(hl)
        sub '0'
        cp 10
        jr nc,vl_eb             ; no digit: the E is not ours
        pop de
        ld e,0
vl_e2:  ld a,(hl)
        sub '0'
        cp 10
        jr nc,vl_e3
        ld d,a
        ld a,e
        cp 13
        jr nc,vl_e4             ; clamp: overflow or underflow anyway
        add a,a
        add a,a
        add a,e
        add a,a
        add a,d
        ld e,a
vl_e4:  inc hl
        jr vl_e2
vl_e3:  ld a,e
        inc b
        jr nz,vl_e5
        neg
vl_e5:  ld e,a
        ld a,(VDX)
        add a,e
        ld (VDX),a
        jr vl_sc
vl_eb:  pop hl
vl_sc:  push hl
        ld a,(VDX)
        call fu_scl
        pop hl
        pop de
        push hl
        ld hl,FA
        call fu_pack
        pop hl
        or a
        ret
vl_no:  pop de
        scf
        ret
m_fpv_e:
