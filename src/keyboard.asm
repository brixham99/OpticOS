; keyboard.asm - matrix scan with debounce and auto-repeat (called by the
; ISR), key tables, and key_in (channel K input).
m_kbd_s:
kscan:  ld bc,$FEFE
        ld de,$FF00             ; D = key index found, E = shift bits
        ld l,0                  ; L = key index (row * 5 + bit)
ks_row: in a,(c)
        cpl
        ld h,5
ks_bit: rra
        jr nc,ks_nxt
        push af
        ld a,l
        or a                    ; index 0 = CAPS SHIFT
        jr nz,ks_ns
        set 0,e
        jr ks_rel
ks_ns:  cp 36                   ; index 36 = SYMBOL SHIFT
        jr nz,ks_key
        set 1,e
        jr ks_rel
ks_key: ld d,l
ks_rel: pop af
ks_nxt: inc l
        dec h
        jr nz,ks_bit
        rlc b
        jr c,ks_row
        ld a,d
        inc a
        ld a,d
        jr nz,ks_have
        ld a,e
        cp 3                    ; CAPS + SYMBOL alone: E mode (pseudo key 40)
        ld a,40
        jr z,ks_have
        ld a,$FF
        ld (KS_LAST),a
        ret
ks_have:
        ld hl,KS_LAST
        cp (hl)
        jr nz,ks_new
        inc hl
        dec (hl)
        ret nz
        cp 40
        ret z                   ; E mode never repeats
        ld a,(REPPER)
        ld (hl),a
        ld a,d
        jr ks_emit
ks_new: ld (hl),a
        inc hl
        ld b,a
        ld a,(REPDEL)
        ld (hl),a
        ld a,b
        cp 40
        jr nz,ks_emit
        ld hl,KS_MODE
        ld a,(hl)
        xor 2
        ld (hl),a
        ret
ks_emit:                        ; A = key index 0-39, E = shift bits
        ld c,a
        ld b,0
        ld hl,KS_MODE
        bit 1,(hl)
        jr z,ks_noe
        res 1,(hl)
        ld hl,ktab_e
ks_el:  ld a,(hl)
        inc hl
        inc a
        jr z,ks_noe
        dec a
        cp c
        ld a,(hl)
        inc hl
        jr nz,ks_el
        jr ks_store
ks_noe: bit 1,e
        jr z,ks_nosym
        ld hl,ktab_sym
        add hl,bc
        ld a,(hl)
        jr ks_store
ks_nosym:
        ld hl,ktab_base
        add hl,bc
        ld a,(hl)
        bit 0,e
        jr nz,ks_caps
        ld hl,KS_MODE
        bit 0,(hl)
        jr z,ks_store
        cp 'a'
        jr c,ks_store
        sub 32
        jr ks_store
ks_caps:
        cp 'a'
        jr c,ks_cnl
        sub 32
        jr ks_store
ks_cnl: sub '0'
        jr c,ks_coth
        ld c,a
        ld hl,ktab_capd
        add hl,bc
        ld a,(hl)
        cp 6                    ; CAPS+2: caps lock
        jr nz,ks_store
        ld hl,KS_MODE
        ld a,(hl)
        xor 1
        ld (hl),a
        ret
ks_coth:
        add a,'0'
        cp 13                   ; CAPS+ENTER is ENTER; CAPS+SPACE is BREAK,
        ret nz                  ; which is polled directly, not queued
ks_store:
        or a
        ret z
        ld (LAST_K),a
        ld hl,FLAGS
        set 5,(hl)
        ret

; key_in: wait for a key (interrupts on), return it in A with carry set
key_in: ei
ki_w:   halt
        ld hl,FLAGS
        bit 5,(hl)
        jr z,ki_w
        res 5,(hl)
        ld a,(LAST_K)
        scf
        ret

ktab_base:
        defb 0,'z','x','c','v'
        defb 'a','s','d','f','g'
        defb 'q','w','e','r','t'
        defb '1','2','3','4','5'
        defb '0','9','8','7','6'
        defb 'p','o','i','u','y'
        defb 13,'l','k','j','h'
        defb ' ',0,'m','n','b'
ktab_sym:
        defb 0,':','`','?','/'
        defb 0,0,0,0,0
        defb 0,0,0,'<','>'
        defb '!','@','#','$','%'
        defb '_',')','(',$27,'&'
        defb '"',';',0,0,0
        defb 13,'=','+','-','^'
        defb ' ',0,'.',',','*'
ktab_capd:                      ; CAPS + 0..9
        defb 12,7,6,4,5,8,10,11,9,15
ktab_e:                         ; E mode: key index, character
        defb 29,'[',28,']',8,'{',9,'}',7,$5C,6,'|',5,'~',$FF
m_kbd_e:
