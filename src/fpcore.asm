; fpcore.asm - OpticOS float core (phase 2).
; Numbers are 5 bytes, Sinclair layout (spec 4.2, 7.7):
;   float      e m4|s m3 m2 m1   value = 0.1m4m3m2m1 (binary) x 2^(e-128)
;   small int  00 s lo hi 00     s = $00 or $FF, lo/hi two's complement,
;                                integers -65535..65535 are always stored so.
; Internally a number is unpacked into 8 bytes (FA, FB, T0-T6):
;   +0 guard  +1 m1 (low) .. +4 m4 (top bit set)  +5 exponent (0 = zero)
;   +6 sign ($00 or $80)
; All routines may change AF BC DE HL; IX and IY are preserved.
; Errors: RST 8 with ERR_DIV0, ERR_OVFL or ERR_ARG.  See docs/maths.md.
m_fpc_s:
err_ovf: rst 8
        defb ERR_OVFL
err_div0: rst 8
        defb ERR_DIV0
err_arg: rst 8
        defb ERR_ARG

; ---------------------------------------------------- packed-level API
; fp_add / fp_sub / fp_mul / fp_div / fp_pow: HL = left operand, which
; receives the result; DE = right operand (unchanged).
fp_sub: ld a,1
        jr fps_g
fp_add: xor a
fps_g:  ld (FSG),a
        ld (FRP),de
        ld a,(de)
        or (hl)
        jr nz,fpa_f
        push hl
        call si_val             ; left in C:D:E
        ld b,c
        ex de,hl
        ex (sp),hl              ; stack: left value, HL = destination
        push hl
        ld hl,(FRP)
        push bc
        call si_val             ; right in C:D:E
        ld a,(FSG)
        or a
        call nz,si_neg
        ld b,c                  ; B = right sign byte
        pop af
        ld c,a                  ; C = left sign byte
        pop hl                  ; destination
        ex (sp),hl              ; HL = left value
        add hl,de
        ld a,c
        adc a,b
        ex de,hl
        pop hl                  ; destination
        ld c,a
        call si_put
        ret nc
        ld de,(FRP)
fpa_f:  ld bc,fu_add
        ld a,(FSG)
        or a
        jr z,fp_gen
        ld bc,fu_sub
        jr fp_gen

fp_div: ld bc,fu_div
fp_gen: push hl                 ; destination
        push bc
        call fu_ld2
        pop hl
        call jphl
        pop hl
fp_stA: ex de,hl                ; pack FA into (HL)
        ld hl,FA
        jp fu_pack
jphl:   jp (hl)

fp_mul: ld a,(de)
        or (hl)
        jr nz,fpm_f
        push hl
        push de
        call si_val
        call si_mag
        ld a,c
        ld (FSG),a
        ld b,d
        ld c,e                  ; BC = |left|
        pop hl
        push hl
        push bc
        call si_val
        call si_mag             ; DE = |right|
        ld a,(FSG)
        xor c
        ld (FSG),a
        pop bc
        call mul16              ; HL = product, CF = too big
        pop de                  ; right operand
        ex (sp),hl              ; HL = destination
        jr c,fpm_o
        pop de                  ; product
        ld a,(FSG)
        or a
        ld c,0
        jr z,fpm_p
        ld a,d
        or e
        jr z,fpm_p
        call si_ngd
        ld c,$FF
fpm_p:  jp si_put
fpm_o:  pop af
fpm_f:  ld bc,fu_mul
        jr fp_gen

; mul16: HL = BC * DE; CF set if the product needs more than 16 bits
mul16:  ld hl,0
        ld a,16
m16_l:  add hl,hl
        jr c,m16_x
        sla e
        rl d
        jr nc,m16_n
        add hl,bc
        jr c,m16_x
m16_n:  dec a
        jr nz,m16_l
        ret
m16_x:  scf
        ret

; fp_cmp: HL = left, DE = right -> A = $FF (left < right), 0 (equal) or
; 1 (left > right), with S and Z set to match.  Nothing is written.
fp_cmp: ld a,(de)
        or (hl)
        jr nz,fpc_f
        inc hl
        inc de
        ld a,(hl)
        xor $80
        ld b,a
        ld a,(de)
        xor $80
        cp b
        jr nz,fc_r
        inc hl
        inc hl
        inc de
        inc de
        ld a,(de)
        cp (hl)
        jr nz,fc_r
        dec hl
        dec de
        ld a,(de)
        cp (hl)
        jr nz,fc_r
        xor a
        ret
fc_r:   sbc a,a                 ; CF = right < left
        cpl
        or 1
        ret
fpc_f:  call fu_ld2
; fu_cmp: compare FA with FB, result as fp_cmp
fu_cmp: ld a,(FA+5)
        or a
        jr nz,fuc_1
        ld (FA+6),a             ; a zero has no sign
fuc_1:  ld a,(FB+5)
        or a
        jr nz,fuc_2
        ld (FB+6),a
fuc_2:  ld a,(FA+6)
        ld hl,FB+6
        cp (hl)
        jr z,fuc_s
        rla                     ; signs differ: the negative one is smaller
        sbc a,a
        or 1
        ret
fuc_s:  ld hl,FA+5
        ld de,FB+5
        ld a,(de)
        cp (hl)
        jr nz,fuc_d
        or a
        ret z                   ; both zero
        ld b,5
fuc_l:  dec hl
        dec de
        ld a,(de)
        cp (hl)
        jr nz,fuc_d
        djnz fuc_l
        xor a
        ret
fuc_d:  sbc a,a                 ; |FA| > |FB| -> 1, else -1
        cpl
        or 1
        ld b,a
        ld a,(FA+6)
        or a
        ld a,b
        jr z,fuc_x
        neg
fuc_x:  or a
        ret

; fp_neg, fp_abs, fp_sgn: HL = number, changed in place
fp_neg: ld a,(hl)
        or a
        jr z,fpn_i
        inc hl
        ld a,(hl)
        xor $80
        ld (hl),a
        dec hl
        ret
fpn_i:  call si_val
        call si_neg
        jp si_put
fp_abs: ld a,(hl)
        or a
        jr z,fpb_i
        inc hl
        res 7,(hl)
        dec hl
        ret
fpb_i:  inc hl
        bit 7,(hl)
        dec hl
        ret z
        jr fpn_i
fp_sgn: call fp_tst
        ld e,a
        rla
        sbc a,a
        ld d,a
        ld c,a
        jp si_put
; fp_tst: HL = number -> A = $FF, 0 or 1 (sign), flags set
fp_tst: ld a,(hl)
        or a
        inc hl
        ld a,(hl)
        jr z,ft_i
        dec hl
ft_s:   rla
        sbc a,a
        or 1
        ret
ft_i:   inc hl
        or (hl)
        inc hl
        or (hl)
        dec hl
        dec hl
        dec hl
        ret z
        inc hl
        ld a,(hl)
        dec hl
        jr ft_s

; fp_int: HL = number -> INT (largest integer not above it), in place
fp_int: ld a,(hl)
        or a
        ret z
        push hl
        ld de,FA
        call fu_unpack
        call fu_int
        pop hl
        jp fp_stA
fu_int: ld a,(FA+5)
        cp 160
        ret nc                  ; no fraction bits
        sub 129
        jr c,fi_sm              ; |x| < 1
        sub 31
        neg                     ; fraction bits 1..31
        ld b,a
        ld hl,FA+1
        ld c,0
fi_l:   ld a,b
        cp 8
        jr c,fi_p
        ld a,(hl)
        or c
        ld c,a
        ld (hl),0
        inc hl
        ld a,b
        sub 8
        ld b,a
        jr fi_l
fi_p:   ld a,$FF
        inc b
fi_m:   dec b
        jr z,fi_m2
        add a,a
        jr fi_m
fi_m2:  ld d,a
        cpl
        and (hl)
        or c
        ld c,a
        ld a,(hl)
        and d
        ld (hl),a
        ld a,c
        or a
        ret z
        ld a,(FA+6)
        or a
        ret z
        call fu_run
        defb SUB_+K_ONE, END_
        ret
fi_sm:  ld a,(FA+6)
        or a
        jp z,fu_zero
        ld de,1
        ld c,$80
        ld hl,FA
        jp fu_from16

; fp_set_int: HL = destination, DE = signed 16-bit value
fp_set_int:
        ld a,d
        rla
        sbc a,a
        ld c,a
        jp si_put
; fp_get_int: HL = number -> DE = nearest integer (two's complement),
; A = $00 or $FF (sign, giving -65535..65535); CF set if out of range.
fp_get_int:
        ld a,(hl)
        or a
        jr nz,fgi_f
        push hl
        inc hl
        ld a,(hl)
        inc hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        pop hl
        or a
        ret
fgi_f:  push hl
        ld de,FA
        call fu_unpack
        call fu_fix
        pop hl
        ret c
        xor a
        bit 7,c
        ret z
        ld a,d
        or e
        ret z
        call si_ngd
        ld a,$FF
        or a
        ret

; ---------------------------------------------------- small integers
; si_val: HL = small int -> C:D:E (24-bit two's complement), HL kept
si_val: push hl
        inc hl
        ld c,(hl)
        inc hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        pop hl
        ret
; si_put: store C:D:E at HL as a small int; CF set (nothing stored) if
; it is outside -65535..65535
si_put: ld a,c
        or a
        jr z,sp_ok
        inc a
        scf
        ret nz
        ld a,d
        or e
        scf
        ret z
sp_ok:  push hl
        xor a
        ld (hl),a
        inc hl
        ld (hl),c
        inc hl
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ld (hl),a
        pop hl
        ret                     ; CF clear from xor
si_neg: xor a
        sub e
        ld e,a
        ld a,0
        sbc a,d
        ld d,a
        ld a,0
        sbc a,c
        ld c,a
        ret
si_mag: bit 7,c
        ret z
si_ngd: xor a
        sub e
        ld e,a
        sbc a,a
        sub d
        ld d,a
        ret

; ---------------------------------------------------- unpack / pack
; fu_ld2: unpack (HL) into FA and (DE) into FB
fu_ld2: push de
        ld de,FA
        call fu_unpack
        pop hl
        ld de,FB
; fu_unpack: HL = packed number, DE = 8-byte unpacked destination
fu_unpack:
        ld a,(hl)
        or a
        jr z,fuu_i
        ex de,hl
        ld (hl),0
        inc hl
        inc de
        inc de
        inc de
        inc de
        ld b,3
fuu_l:  ld a,(de)
        ld (hl),a
        inc hl
        dec de
        djnz fuu_l
        ld a,(de)
        ld c,a
        or $80
        ld (hl),a
        inc hl
        dec de
        ld a,(de)
        ld (hl),a
        inc hl
        ld a,c
        and $80
        ld (hl),a
        ret
fuu_i:  inc hl
        ld a,(hl)
        inc hl
        ld c,(hl)
        inc hl
        ld b,(hl)
        ex de,hl
        ld e,c
        ld d,b
        and $80
        ld c,a
        jr z,fu_from16
        call si_ngd
        ld a,d
        or e
        jr nz,fu_from16
        ld d,$80                ; -65536
        ld b,145
        jr ff_e
; fu_from16: HL = unpacked destination, DE = magnitude, C = sign
fu_from16:
        ld b,144
ff_e:   xor a
        ld (hl),a
        inc hl
        ld (hl),a
        inc hl
        ld (hl),a
        inc hl
        ld a,d
        or e
        jr nz,ff_n
        ld b,a
        ld c,a
        jr ff_st
ff_n:   bit 7,d
        jr nz,ff_st
        ex de,hl
        add hl,hl
        ex de,hl
        dec b
        jr ff_n
ff_st:  ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ld (hl),b
        inc hl
        ld (hl),c
        ret

; fu_pack: HL = unpacked source, DE = packed destination.  Rounds to
; nearest, stores integers -65535..65535 in small-int form.
fu_pack:
        push de
        ld a,(hl)
        inc hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        ld c,(hl)
        inc hl
        ld b,(hl)
        inc hl
        add a,a                 ; CF = rounding bit
        ld a,(hl)
        inc hl
        ld l,(hl)               ; L = sign
        jr nc,fk_1
        inc e
        jr nz,fk_1
        inc d
        jr nz,fk_1
        inc c
        jr nz,fk_1
        inc b
        jr nz,fk_1
        ld b,$80
        inc a
        jp z,err_ovf
fk_1:   ld h,a                  ; H = exponent
        or a
        jr z,fk_z
        sub 129
        cp 16
        jr nc,fk_f              ; not 1 <= |x| < 65536
        ld a,d
        or e
        jr nz,fk_f
        push hl
        push bc
        ld a,144
        sub h
        jr z,fk_i2
fk_i1:  srl b
        rr c
        jr c,fk_ni
        dec a
        jr nz,fk_i1
fk_i2:  pop af
        pop hl
        ld a,l
        or a
        jr z,fk_i3
        xor a
        sub c
        ld c,a
        sbc a,a
        sub b
        ld b,a
        ld a,$FF
fk_i3:  pop hl
        ld (hl),0
        inc hl
        ld (hl),a
        inc hl
        ld (hl),c
        inc hl
        ld (hl),b
        inc hl
        ld (hl),0
        ret
fk_ni:  pop bc
        pop hl
fk_f:   ld a,b
        and $7F
        or l
        ld b,a
        ld a,h
        pop hl
        ld (hl),a
        inc hl
        ld (hl),b
        inc hl
        ld (hl),c
        inc hl
        ld (hl),d
        inc hl
        ld (hl),e
        ret
fk_z:   pop hl
        ld b,5
fk_z1:  ld (hl),0
        inc hl
        djnz fk_z1
        ret

; ---------------------------------------------------- unpacked arithmetic
; fu_add / fu_sub: FA = FA + FB / FA - FB  (FB is changed)
fu_sub: ld hl,FB+6
        ld a,(hl)
        xor $80
        ld (hl),a
fu_add: ld a,(FB+5)
        or a
        ret z
        ld b,a
        ld a,(FA+5)
        or a
        jp z,fad_c
        sub b
        jr nc,fad_1
        push af
        call fu_swap
        pop af
        neg
fad_1:  cp 41
        ret nc
        ld hl,FB
        call fu_shr
        ld a,(FA+6)
        ld hl,FB+6
        xor (hl)
        ld hl,FA
        ld de,FB
        ld b,5
        jr nz,fad_s
fad_a:  ld a,(de)
        adc a,(hl)
        ld (hl),a
        inc hl
        inc de
        djnz fad_a
        ret nc
        ld hl,FA+4
        ld b,5
fad_r:  rr (hl)
        dec hl
        djnz fad_r
        ld hl,FA+5
        inc (hl)
        ret nz
        jp err_ovf
fad_s:  ld a,(de)
        ld c,a
        ld a,(hl)
        sbc a,c
        ld (hl),a
        inc hl
        inc de
        djnz fad_s
        jr nc,fu_norm
        ld hl,FA
        ld b,5
        or a
fad_n:  ld a,0
        sbc a,(hl)
        ld (hl),a
        inc hl
        djnz fad_n
        ld a,(FA+6)
        xor $80
        ld (FA+6),a
; fu_norm: normalise FA (mantissa top bit set), zero if all clear
fu_norm:
        ld hl,FA
        ld b,5
        xor a
fn_z:   or (hl)
        inc hl
        djnz fn_z
        jr z,fu_zero
fn_l:   ld a,(FA+4)
        or a
        ret m
        ld hl,FA
        ld b,5
fn_s:   rl (hl)
        inc hl
        djnz fn_s
        ld hl,FA+5
        dec (hl)
        jr nz,fn_l
fu_zero: xor a
        ld (FA+5),a
        ld (FA+6),a
        ret
fad_c:  ld hl,FB
        ld de,FA
        ld bc,7
        ldir
        ret
fu_swap: ld hl,FA
        ld de,FB
        ld b,7
fw_l:   ld a,(de)
        ld c,(hl)
        ld (hl),a
        ld a,c
        ld (de),a
        inc hl
        inc de
        djnz fw_l
        ret
; fu_shr: shift the 40-bit mantissa at HL (guard first) right A bits
fu_shr: cp 8
        jr c,fs_b
        push af
        push hl
        ld d,h
        ld e,l
        inc hl
        ld bc,4
        ldir
        xor a
        ld (de),a
        pop hl
        pop af
        sub 8
        jr fu_shr
fs_b:   or a
        ret z
        ld c,a
fs_b1:  push hl
        inc hl
        inc hl
        inc hl
        inc hl
        ld b,5
        or a
fs_b2:  rr (hl)
        dec hl
        djnz fs_b2
        pop hl
        dec c
        jr nz,fs_b1
        ret

; fu_mul: FA = FA * FB
fu_mul: ld a,(FB+5)
        ld c,a
        ld a,(FA+5)
        or a
        ret z
        inc c
        dec c
        jp z,fu_zero
        ld l,a
        ld h,0
        ld b,h
        add hl,bc
        ld bc,-128
        add hl,bc
        push hl                 ; exponent
        ld a,(FB+6)
        ld hl,FA+6
        xor (hl)
        ld (hl),a
        push ix
        ld ix,FA
        ld hl,0
        ld d,h
        ld e,l
        ld c,l
        ld a,(FB)
        call fm_b
        ld a,(FB+1)
        call fm_b
        ld a,(FB+2)
        call fm_b
        ld a,(FB+3)
        call fm_b
        ld a,(FB+4)
        call fm_b
        pop ix
        ld a,c
        ld (FA),a
        ld (FA+1),de
        ld (FA+3),hl
        pop bc
fm_nrm: ld a,(FA+4)
        or a
        jp m,fu_sete
        push bc
        ld hl,FA
        ld b,5
fm_s1:  rl (hl)                 ; CF clear from or
        inc hl
        djnz fm_s1
        pop bc
        dec bc
        jr fm_nrm
; fm_b: one multiplier byte (A) into the product H L D E C
fm_b:   or a
        jr z,fm_z
        scf
        rra
        ld b,a
fm_l:   jr nc,fm_s
        ld a,e
        add a,(ix+1)
        ld e,a
        ld a,d
        adc a,(ix+2)
        ld d,a
        ld a,l
        adc a,(ix+3)
        ld l,a
        ld a,h
        adc a,(ix+4)
        ld h,a
fm_s:   rr h
        rr l
        rr d
        rr e
        rr c
        srl b
        jr nz,fm_l
        ret
fm_z:   ld c,e
        ld e,d
        ld d,l
        ld l,h
        ld h,a
        ret
; fu_sete: BC = signed exponent for FA: zero if <= 0, error if > 255
fu_sete:
        ld a,b
        or a
        jr nz,fe_1
        or c
        jp z,fu_zero
        ld (FA+5),a
        ret
fe_1:   rla
        jp c,fu_zero
        jp err_ovf

; fu_div: FA = FA / FB
fu_div: ld a,(FB+5)
        or a
        jp z,err_div0
        ld c,a
        ld a,(FA+5)
        or a
        ret z
        ld l,a
        ld h,0
        ld b,h
        or a
        sbc hl,bc
        ld bc,129
        add hl,bc
        push hl                 ; exponent (if the quotient is >= 1)
        ld a,(FB+6)
        ld hl,FA+6
        xor (hl)
        ld (hl),a
        push ix
        ld ix,FB
        ld de,(FA+1)
        ld hl,(FA+3)
        or a
        call fd_byte
        push bc
        call fd_byte
        push bc
        call fd_byte
        push bc
        call fd_byte
        push bc
        call fd_byte
        ld a,c
        ld (FA),a
        ld hl,FA+1
        pop bc
        ld (hl),c
        inc hl
        pop bc
        ld (hl),c
        inc hl
        pop bc
        ld (hl),c
        inc hl
        pop bc
        ld (hl),c
        pop ix
        pop bc
        jp fm_nrm
; fd_byte: 8 quotient bits into C.  R = H L D E, divisor at IX+1..4,
; CF in = the bit shifted out of R last time.
fd_byte: ld b,8
fd_l:   jr c,fd_f
        call fd_sub
        jr nc,fd_q
        call fd_add
        jr fd_q
fd_f:   call fd_sub
        or a
fd_q:   ccf
        rl c
        sla e
        rl d
        rl l
        rl h
        djnz fd_l
        ret
fd_sub: ld a,e
        sub (ix+1)
        ld e,a
        ld a,d
        sbc a,(ix+2)
        ld d,a
        ld a,l
        sbc a,(ix+3)
        ld l,a
        ld a,h
        sbc a,(ix+4)
        ld h,a
        ret
fd_add: ld a,e
        add a,(ix+1)
        ld e,a
        ld a,d
        adc a,(ix+2)
        ld d,a
        ld a,l
        adc a,(ix+3)
        ld l,a
        ld a,h
        adc a,(ix+4)
        ld h,a
        ret

; fu_fix: FA -> DE = |nearest integer|, C = sign; CF set if >= 65535.5
fu_fix: ld a,(FA+6)
        ld c,a
        ld de,0
        ld a,(FA+5)
        sub 128
        jr c,fx_z
        cp 17
        ccf
        ret c
        ld b,a
        ld a,24
        sub b
        ld b,a
        ld hl,(FA+3)
        ld a,(FA+2)
fx_s:   srl h
        rr l
        rra
        djnz fx_s
        ld e,a
        ld d,l
        ret nc
        inc de
        ld a,d
        or e
        ret nz
        scf
        ret
fx_z:   or a
        ret
m_fpc_e:
