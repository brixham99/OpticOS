; vars.asm - OpticBASIC run-time data (phase 3): the value stack, variables
; and arrays, the string heap with its sliding compactor, and the control
; stack.  See docs/phase3/README.md for the layouts.
F_FOR   equ 1                   ; control stack frame types
F_PROC  equ 2
F_FN    equ 3
F_TRY   equ 4
F_LOC   equ 5
m_var_s:
err_syn:  rst 8
        defb ERR_SYN
err_type: rst 8
        defb ERR_TYPE
err_nomem: rst 8
        defb ERR_NOMEM
err_novar: rst 8
        defb ERR_NOVAR
err_subs: rst 8
        defb ERR_SUBS
err_endp: rst 8
        defb ERR_ENDP
err_next: rst 8
        defb ERR_NEXT

; ---------------------------------------------------- workspace
; Below RAMTOP: machine stack 512, control stack 768, value stack 320,
; tokenised direct line 256, then the string heap grows down.
ws_init: ld hl,(RAMTOP)
        ld de,-512
        add hl,de
        ld (CSB),hl
        ld de,-768
        add hl,de
        ld (CSLIM),hl
        ld (VSLIM),hl
        ld de,-320
        add hl,de
        ld (VSB),hl
        ld de,-256
        add hl,de
        ld (TKB),hl
        ld (HTOP),hl
        ld hl,STATIC
        ld b,52
wi_z:   ld (hl),0
        inc hl
        djnz wi_z
p_new:  ld hl,OPROG
        ld (PEND),hl
        ld (hl),0
        inc hl
        ld (VARSB),hl
        ld a,1
        ld (PPF),a
; clr_vars: forget every variable and string (A%-Z% are kept)
clr_vars:
        ld hl,(VARSB)
        ld (VEND),hl
        ld hl,HEADS
        ld b,64
cv_z:   ld (hl),0
        inc hl
        djnz cv_z
        ld hl,(HTOP)
        ld (HP),hl
        ret
; stk_reset: empty the control and value stacks
stk_reset:
        ld hl,(CSB)
        ld (CSP),hl
        ld hl,(VSB)
        ld (VSP),hl
        ret

; ---------------------------------------------------- text pointer helpers
tk:     ld hl,(CH_ADD)          ; A = current token
        ld a,(hl)
        ret
skip1:  ld hl,(CH_ADD)          ; step over a one-byte token
        inc hl
        ld (CH_ADD),hl
        ret
expect: ld hl,(CH_ADD)          ; A must be the current (one-byte) token
        cp (hl)
        jp nz,err_syn
        inc hl
        ld (CH_ADD),hl
        ret
rd_link: ld hl,(CH_ADD)         ; DE = link slot at CH_ADD, step over it
        inc hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        ld (CH_ADD),hl
        ret
is_end: cp ':'                  ; Z if A ends a statement
        ret z
        cp 13
        ret z
        cp T_ELSE
        ret
nxl:    ld e,(hl)               ; HL = line -> HL = next line
        ld d,0
        add hl,de
        ret
; tk_len: HL = token -> HL just past it (A changed)
tk_len: ld a,(hl)
        inc hl
        dec a
        jr z,tl_id              ; 1 identifier
        cp 4
        jr c,tl_2               ; 2, 3, 4 integer / hex / binary
        jr z,tl_f               ; 5 float
        cp 5
        jr z,tl_st              ; 6 string
        cp 6
        ret nz                  ; everything else is one byte
tl_2:   inc hl                  ; 7 link slot
        inc hl
        ret
tl_f:   ld a,5
        jr tl_ad
tl_id:  inc hl
        inc hl
tl_st:  ld a,(hl)
        inc hl
tl_ad:  add a,l
        ld l,a
        ret nc
        inc h
        ret

; ---------------------------------------------------- value stack
ev_push: push de                 ; HL = new 5-byte slot (BC, DE kept)
        ld hl,(VSP)
        push hl
        ld de,5
        add hl,de
        ex de,hl
        ld hl,(VSLIM)
        or a
        sbc hl,de
        jp c,err_nomem
        ld (VSP),de
        pop hl
        pop de
        ret
ev_top: push de                 ; HL = top entry (DE kept)
        ld hl,(VSP)
        ld de,-5
        add hl,de
        pop de
        ret
ev_pop: call ev_top             ; drop the top; HL = it (data still there)
        ld (VSP),hl
        ret
ev_2:   call ev_top             ; HL = second, DE = top
        push hl
        ld de,-5
        add hl,de
        pop de
        ret
is_str: ld a,(hl)               ; Z if the entry at HL is a string
        or a
        ret nz
        inc hl
        ld a,(hl)
        dec hl
        cp 1
        ret
num_chk: call is_str
        jp z,err_type
        ret
str_chk: call is_str
        jp nz,err_type
        ret
pop_num: call ev_pop
        jr num_chk
; pop_int: pop a number -> DE (two's complement), A = sign
pop_int: call pop_num
        call fp_get_int
        jp c,err_arg
        ret
; ty2: HL, DE = entries -> A = 0 both numbers, 1 both strings
ty2:    ex de,hl
        call is_str
        ex de,hl
        jr z,t2_s
        call is_str
        jp z,err_type
        xor a
        ret
t2_s:   call is_str
        jp nz,err_type
        ld a,1
        ret
; tsz: A = type (0 float, 1 int, 2 string) -> BC = value size, A kept
tsz:    ld bc,5
        cp 1
        jr nz,tsz_1
        ld c,2
tsz_1:   cp 2
        ret nz
        ld c,3
        ret
; cphd: CF set if HL < DE (unsigned), HL kept
cphd:   or a
        sbc hl,de
        add hl,de
        ret

; ---------------------------------------------------- values
; val_push: HL = value address, A = type -> pushed as a 5-byte entry
val_push: push hl
        push af
        call ev_push
        pop af
        pop de
        dec a
        jr z,vp_int
        dec a
        jr z,vp_str
        ex de,hl
        ld bc,5
        ldir
        ret
vp_int: ex de,hl
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        ex de,hl
        jp fp_set_int
vp_str: ld (hl),0
        inc hl
        ld (hl),1
        inc hl
        ex de,hl
        ld bc,3
        ldir
        ret
; val_store: HL = variable, A = type <- the top entry, which is popped
val_store: push hl
        push af
        call ev_top
        ex de,hl
        pop af
        pop hl
        call val_put
        jp ev_pop
; val_put: HL = variable, A = type, DE = entry (left in place)
val_put: dec a
        jr z,vs_int
        dec a
        jr z,vs_str
        ex de,hl
        call num_chk
        ld bc,5
        ldir
        ret
vs_int: push hl
        ex de,hl
        call num_chk
        call fp_get_int
        jp c,err_ovf
        xor d                   ; the sign must match bit 7: -32768..32767
        rla
        jp c,err_ovf
        pop hl
        ld (hl),e
        inc hl
        ld (hl),d
        ret
vs_str: ex de,hl
        call str_chk
        ex de,hl
; s_assign: HL = descriptor <- copy of the string entry at DE (on the value
; stack, so a compaction during the allocation keeps it up to date)
s_assign:
        push de
        inc de
        inc de
        ld a,(de)
        pop de
        or a
        jr z,sa_0
        push hl
        push de
        ld d,h
        ld e,l
        call s_alloc            ; DE = new chars, back-pointer = descriptor
        pop hl
        inc hl
        inc hl
        ld c,(hl)
        ld b,0
        inc hl
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        push de
        push bc
        ldir
        pop bc
        pop de
        pop hl
        ld (hl),c
        inc hl
        ld (hl),e
        inc hl
        ld (hl),d
        ret
sa_0:   ld (hl),a
        inc hl
        ld (hl),a
        inc hl
        ld (hl),a
        ret

; ---------------------------------------------------- variables
; var_find: CH_ADD at an identifier token -> CH_ADD past it and
; HL = value address, A = type, CF clear; or CF set if there is none.
; A%-Z% are fixed 2-byte cells and always exist.
var_find:
        ld hl,(CH_ADD)
        ld (VID),hl
        inc hl
        ld a,(hl)
        ld (VTY),a
        inc hl
        ld e,(hl)               ; hash
        inc hl
        ld c,(hl)               ; name length
        ld b,0
        inc hl
        push hl
        add hl,bc
        ld (CH_ADD),hl
        pop hl
        cp 1
        jr nz,vf_h
        dec c
        jr nz,vf_h1
        ld a,(hl)
        sub 'a'
        add a,a
        ld l,a
        ld h,0
        ld bc,STATIC
        add hl,bc
        ld a,1
        or a
        ret
vf_h1:  inc c
vf_h:   push hl
        ld a,e
        add a,a
        ld l,a
        ld h,0
        ld de,HEADS
        add hl,de
        ld (VHD),hl
        pop de                  ; DE = name
vf_lp:  ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        or h
        scf
        ret z
        push hl
        inc hl
        inc hl
        ld a,(VTY)
        cp (hl)
        jr nz,vf_nx
        inc hl
        ld a,c
        cp (hl)
        jr nz,vf_nx
        inc hl
        push de
        ld b,c
vf_c:   ld a,(de)
        cp (hl)
        jr nz,vf_ne
        inc hl
        inc de
        djnz vf_c
        pop de
        pop af
        ld a,(VTY)
        or a
        ret
vf_ne:  pop de
vf_nx:  pop hl
        jr vf_lp
; var_new: make the variable VID/VTY/VHD with BC zeroed value bytes
; -> HL = value address.  Record: next (2), type, length, name, value.
var_new: ld hl,(VID)
        inc hl
        inc hl
        inc hl
        ld a,(hl)
        push bc
        ld l,a
        ld h,0
        add hl,bc
        ld bc,4
        add hl,bc
        push hl
        call room
        pop bc
        ld hl,(VEND)
        push hl
        ld d,h
        ld e,l
        add hl,bc
        ld (VEND),hl
        ld h,d
        ld l,e
        ld (hl),0
        dec bc
        inc de
        ldir
        pop hl                  ; record
        ld de,(VHD)
        ld a,(de)
        ld (hl),a
        inc de
        ld a,(de)
        inc hl
        ld (hl),a
        dec hl
        ex de,hl
        ld (hl),d
        dec hl
        ld (hl),e               ; head = record
        ex de,hl
        inc hl
        inc hl
        ld a,(VTY)
        ld (hl),a
        inc hl
        ex de,hl
        ld hl,(VID)
        inc hl
        inc hl
        inc hl
        ld c,(hl)
        ld b,0
        inc bc
        ldir                    ; length and name
        ex de,hl
        pop bc
        ret
; var_ref: a variable or array element to write (made if new)
; -> HL = value address, A = type (0-2)
var_ref: call var_find
        jr nc,vr_f
        ld a,(VTY)
        bit 2,a
        jp nz,err_novar         ; arrays need DIM
        call tsz
        call var_new
        ld a,(VTY)
        ret
vr_f:   bit 2,a
        ret z
; arr_elem: HL = array value (header), A = type; CH_ADD at "(".
; Header: dimensions, then each size (2 bytes), then the elements.
arr_elem:
        and 3
        push af
        push hl                 ; header
        inc hl
        push hl                 ; cursor at the first size
        ld hl,0
        push hl                 ; offset
        ld a,'('
        call expect
ae_lp:  call ev_expr
        call pop_int
        or a
        jp nz,err_subs
        pop bc                  ; offset
        pop hl                  ; cursor
        push de                 ; index
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        ex (sp),hl              ; HL = index, stack = cursor
        call cphd
        jp nc,err_subs
        push hl
        call mul16              ; HL = offset * size
        jp c,err_subs
        pop de
        add hl,de
        push hl
        call tk
        cp ','
        jr nz,ae_e
        call skip1
        jr ae_lp
ae_e:   ld a,')'
        call expect
        pop bc                  ; offset
        pop de                  ; cursor
        pop hl                  ; header
        ld a,(hl)
        add a,a
        inc a
        add a,l
        ld l,a
        jr nc,ae_1
        inc h
ae_1:   or a                    ; all dimensions given?
        sbc hl,de
        jp nz,err_subs
        pop af
        ld h,b
        ld l,c
        cp 1
        jr z,ae_2
        add hl,hl
        cp 2
        jr z,ae_3
        add hl,hl               ; x4
ae_3:   add hl,bc               ; x3 or x5
        jr ae_4
ae_2:   add hl,hl               ; x2
ae_4:   add hl,de
        ret

; ---------------------------------------------------- string heap
; Blocks grow down from HTOP: chars, length, back-pointer (2) to the
; descriptor (length, address) that owns it.  0 = temporary.
; s_alloc: A = length (1-255), DE = back-pointer -> DE = chars
s_alloc: push de
        ld c,a
        ld b,0
        push bc
        ld hl,3
        add hl,bc
        call room
        pop bc
        pop de
        ld hl,(HP)
        dec hl
        ld (hl),d
        dec hl
        ld (hl),e
        dec hl
        ld (hl),c
        or a
        sbc hl,bc
        ld (HP),hl
        ex de,hl
        ret
; room: make sure HL bytes (+64 spare) are free between VEND and HP,
; compacting the heap if needed
room:   ld de,64
        add hl,de
        push hl
        call free_gap
        pop de
        call cphd
        ret nc
        push de
        call gc
        call free_gap
        pop de
        call cphd
        ret nc
        jp err_nomem
free_gap: ld hl,(HP)
        ld de,(VEND)
        or a
        sbc hl,de
        ret
; gc: slide every live block up towards HTOP.  A block lives if its
; back-pointer names a descriptor that still points at it, or a string on
; the value stack points at it; those are fixed up as it moves.
gc:     ld hl,(HTOP)
        ld (GD),hl
gc_lp:  ld de,(HP)
        or a
        sbc hl,de
        jr z,gc_end
        add hl,de
        dec hl
        ld d,(hl)
        dec hl
        ld e,(hl)
        ld (GB),de
        dec hl
        ld c,(hl)
        ld b,0
        ld a,c
        ld (GL),a
        or a
        sbc hl,bc
        ld (GS),hl
        ld a,d
        or e
        jr z,gc_v
        ex de,hl                ; HL = descriptor, DE = start
        ld a,(hl)
        cp c
        jr nz,gc_v
        inc hl
        ld a,(hl)
        cp e
        jr nz,gc_v
        inc hl
        ld a,(hl)
        cp d
        jr z,gc_k
gc_v:   xor a
        call gc_sc
        jr nz,gc_dr
        ld h,a
        ld l,a
        ld (GB),hl
gc_k:   ld a,(GL)
        ld c,a
        ld b,0
        inc bc
        inc bc
        inc bc
        ld hl,(GD)
        or a
        sbc hl,bc
        ld (GN),hl
        ld de,(GS)
        or a
        sbc hl,de
        jr z,gc_nm
        ld hl,(GS)
        add hl,bc
        dec hl
        ld de,(GD)
        dec de
        lddr
        ld hl,(GB)
        ld a,h
        or l
        jr z,gc_fv
        inc hl
        ld de,(GN)
        ld (hl),e
        inc hl
        ld (hl),d
gc_fv:  ld a,1
        call gc_sc
gc_nm:  ld hl,(GN)
        ld (GD),hl
gc_dr:  ld hl,(GS)
        jp gc_lp
gc_end: ld hl,(GD)
        ld (HP),hl
        ret
; gc_sc: look for value-stack strings pointing into the block at (GS),
; length (GL).  A = 0: Z if there is one; A = 1: move them all by
; (GN) - (GS).
gc_sc:  ld (GF),a
        ld hl,(VSB)
gs_l:   ld de,(VSP)
        call cphd
        jr nc,gs_no
        push hl
        ld a,(hl)
        inc hl
        or a
        jr nz,gs_n
        ld a,(hl)
        inc hl
        dec a
        jr nz,gs_n
        ld a,(hl)
        inc hl
        or a
        jr z,gs_n
        ld e,(hl)
        inc hl
        ld d,(hl)
        push hl
        ex de,hl
        ld de,(GS)
        or a
        sbc hl,de               ; offset into the block
        jr c,gs_p
        ld a,h
        or a
        jr nz,gs_p
        ld a,(GL)
        cp l
        jr c,gs_p
        jr z,gs_p
        ld a,(GF)
        or a
        jr z,gs_y
        ld de,(GN)
        add hl,de
        ex de,hl
        pop hl
        ld (hl),d
        dec hl
        ld (hl),e
        jr gs_n
gs_p:   pop hl
gs_n:   pop hl
        ld de,5
        add hl,de
        jr gs_l
gs_y:   pop hl
        pop hl
        xor a
        ret
gs_no:  or 1
        ret
; bp_set: DE = descriptor; if its string is in the heap, make the block's
; back-pointer DE
bp_set: ld h,d
        ld l,e
        ld a,(hl)
        or a
        ret z
        ld c,a
        inc hl
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        push de
        ld de,(HP)
        call cphd
        pop de
        ret c
        push de
        ld de,(HTOP)
        call cphd
        pop de
        ret nc
        ld b,0
        add hl,bc
        inc hl
        ld (hl),e
        inc hl
        ld (hl),d
        ret

; ---------------------------------------------------- control stack
; Frames (type byte first, growing down from CSB):
;   FOR  18: var (2), type, limit (5), step (5), loop CH_ADD, loop line
;   PROC  5: return CH_ADD, return line
;   FN    7: return CH_ADD, return line, machine SP
;   TRY   7: CATCH line, machine SP, value stack pointer
;   LOCAL 9: var (2), type, old value (5)
fsz:    defb 18,5,7,7,9
; cs_push: A = type, C = size -> HL = new frame
cs_push: push af
        ld hl,(CSP)
        ld b,0
        or a
        sbc hl,bc
        ld de,(CSLIM)
        call cphd
        jp c,err_nomem
        ld (CSP),hl
        pop af
        ld (hl),a
        ret
; cs_pop: drop the top frame (a LOCAL is restored) -> HL = frame, A = type;
; CF set if the stack is empty
cs_pop: ld hl,(CSP)
        ld de,(CSB)
        or a
        sbc hl,de
        scf
        ret z
        add hl,de
        ld a,(hl)
        push hl
        ld e,a
        ld d,0
        ld hl,fsz-1
        add hl,de
        ld e,(hl)
        pop hl
        push hl
        add hl,de
        ld (CSP),hl
        pop hl
        cp F_LOC
        call z,loc_rest
        or a
        ret
loc_rest: push hl
        push af
        inc hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        ld a,(hl)
        inc hl
        push de
        call tsz
        ldir
        pop de
        cp 2
        call z,bp_set
        pop af
        pop hl
        ret
; loc_save: HL = variable, A = type -> old value saved in a LOCAL frame,
; the variable set to 0 or ""
loc_save: push hl
        push af
        ld a,F_LOC
        ld c,9
        call cs_push
        pop af
        pop de
        inc hl
        ld (hl),e
        inc hl
        ld (hl),d
        inc hl
        ld (hl),a
        inc hl
        push af
        push hl                 ; saved-value slot
        ex de,hl
        call tsz
        push hl
        push bc
        ldir
        pop bc
        pop hl
ls_z:   ld (hl),0
        inc hl
        dec bc
        ld a,b
        or c
        jr nz,ls_z
        pop de
        pop af
        cp 2
        ret nz
        jp bp_set
; fr_ret: HL = PROC/FN frame -> CH_ADD and CURLN restored, HL = frame+5
fr_ret: inc hl
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        ld (CH_ADD),de
        ld e,(hl)
        inc hl
        ld d,(hl)
        inc hl
        ld (CURLN),de
        ret
m_var_e:
