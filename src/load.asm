; load.asm - LD-BYTES at $0556.  IX = start, DE = length, A = flag,
; carry set = LOAD, clear = VERIFY.  Returns carry set on success.
; All timing goes through LD-EDGE-1/2 ($05E7/$05E3).
LB_PIL0   equ 156               ; full pilot cycle reads about +58
LB_PILMIN equ 191
LB_SYN0   equ 206               ; half pilot reads about +29, sync about +3
LB_SYNMAX equ 222
LB_BIT0   equ 180               ; bit 0 cycle about +14, bit 1 about +43
LB_BITTH  equ 208
m_ld_s:
LD_BYTES:                       ; (trap layout: see save.asm)
        di
        ex af,af'               ; A' = flag, F' carry = load / verify
        ld hl,tape_ret          ; exit handler ($053F) on the stack
        push hl
        ld a,$0F
        out ($FE),a
        in a,($FE)
        rra                     ; $0562: an instruction boundary
        and $20
        or $02
        ld c,a                  ; C bit 5 = EAR level, bits 0-2 = border
lb_wait:
        ld h,0                  ; need 256 good pilot cycles in a row
        cp a
        ret nz                  ; $056B: never taken (Z set); load traps fire here
lb_lead:
        ld b,LB_PIL0
        call LD_EDGE2
        jr nc,lb_nc
        ld a,b
        cp LB_PILMIN
        jr c,lb_wait
        inc h
        jr nz,lb_lead
lb_sync:
        ld b,LB_SYN0
        call LD_EDGE1
        jr nc,lb_nc
        ld a,b
        cp LB_SYNMAX
        jr nc,lb_sync           ; still pilot
        ld h,0                  ; parity
        call LD_EDGE1           ; second sync edge
        ret nc
        ld a,c
        xor $03                 ; blue / yellow stripes for data
        ld c,a
        call lb_byte            ; flag byte
        ret nc
        ex af,af'
        jr nc,lb_vf
        cp l
        jr nz,lb_fail
lb_ld:  ld a,d
        or e
        jr z,lb_par
        call lb_byte
        ret nc
        ld (ix+0),l
        inc ix
        dec de
        jr lb_ld
lb_vf:  cp l
        jr nz,lb_fail
lb_vl:  ld a,d
        or e
        jr z,lb_par
        call lb_byte
        ret nc
        ld a,(ix+0)
        cp l
        jr nz,lb_fail
        inc ix
        dec de
        jr lb_vl
lb_par: call lb_byte            ; parity byte: running XOR must end at 0
        ret nc
        ld a,h
        cp 1                    ; carry set only when H = 0
        ret
lb_fail:
        or a
        ret
lb_nc:  ld a,$7F                ; time-out or BREAK?
        in a,($FE)
        rra
        jr c,lb_wait            ; time-out: keep looking for a leader
        ret                     ; BREAK: carry clear, tape_ret reports it
m_ld_e:
        org $05E2
        ret                     ; $05E2: load traps resume here
