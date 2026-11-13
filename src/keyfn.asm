; keyfn.asm - phase 5c: KEY(k$) and FREE
m_key_s:
; KEY(k$): TRUE while the key for the first character of k$ is held (letters,
; digits and space; read straight from the matrix, so several keys can be down)
f_key:  call str_una
        inc hl
        inc hl
        ld a,(hl)
        or a
        ld de,0
        jr z,fk_w
        inc hl
        ld a,(hl)
        inc hl
        ld h,(hl)
        ld l,a
        ld a,(hl)
        or $20
        ld hl,ktab_base
        ld bc,40
        cpir
        jr nz,fk_w
        ld a,39
        sub c                   ; key index = row * 5 + bit
        ld b,$FE
fk_r:   sub 5
        jr c,fk_b
        rlc b
        jr fk_r
fk_b:   add a,6
        ld e,a
        ld c,$FE
        in a,(c)
fk_s:   rra
        dec e
        jr nz,fk_s
        jr c,fk_w               ; E is 0 here, so DE = 0
        dec de
fk_w:   call ev_pop
        jp push_int
; FREE: bytes between the variables and the string heap
f_free: ld hl,(HP)
        ld de,(VEND)
        or a
        sbc hl,de
        ex de,hl
        jp push_u
m_key_e:
