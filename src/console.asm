; console.asm - phase 1 minimal console: a one-line editor with a blinking
; 4x8 cursor block.  The input line (up to 126 characters, two rows) is
; edited with left/right, DELETE and insert; ENTER hands it to con_line.
m_con_s:
console:
        ld sp,(RAMTOP)
        ld hl,con_err
        push hl
        ld (ERR_SP),sp
        ld iy,ERR_NR
        ld hl,CHANTAB+5         ; channel S
        ld (CURCHL),hl
        ei
con_new:
        ld hl,(ATTR_P)          ; temporary colours end with the statement
        ld (ATTR_T),hl
        ld a,(S_POSN)
        or a
        ld a,13
        call nz,pr_out
        xor a
        ld (CON_LEN),a
        ld (EIDX),a
con_pr: ld a,(EMODE)            ; prompt: ] direct, + AUTO, * EDIT
        and 3
        ld e,a
        ld d,0
        ld hl,prm_t
        add hl,de
        ld a,(hl)
        rst 16
        ld a,' '
        rst 16
con_in: call pos_lin
        ld (ESTART),hl
k_rd:   call redraw
con_key:
        call con_getkey
        cp 13
        jp z,con_enter
        ld hl,EMODE
        bit 2,(hl)              ; INPUT: no editor keys
        jr nz,ck_n
        cp 7
        jp z,con_edit
        cp 11
        jp z,c_up
        cp 10
        jp z,c_down
ck_n:   ld hl,EIDX
        cp 8
        jr z,c_left
        cp 9
        jr z,c_right
        cp 12
        jr z,c_del
        cp 32
        jr c,con_key
        cp 128
        jr nc,con_key
        push af                 ; insert at the cursor
        ld a,(CON_LEN)
        cp EMAX
        jr nc,ci_x
        sub (hl)
        ld c,a
        ld b,0
        ld a,(CON_LEN)
        ld e,a
        ld d,b
        ld hl,EBUF
        add hl,de
        ld d,h
        ld e,l
        dec hl
        ld a,c
        or a
        jr z,ci_1
        lddr
ci_1:   pop af
        ld (de),a
        ld hl,CON_LEN
        inc (hl)
        ld hl,EIDX
c_right: ld a,(CON_LEN)
        cp (hl)
        jr z,con_key
        inc (hl)
        jr k_rd
ci_x:   pop af
        jr con_key
c_left: ld a,(hl)
        or a
        jr z,con_key
        dec (hl)
        jr k_rd
c_del:  ld a,(hl)               ; DELETE: the character left of the cursor
        or a
        jr z,con_key
        dec (hl)
        ld hl,CON_LEN
        dec (hl)
        ld a,(hl)
        ld hl,EIDX
        sub (hl)
        ld c,a
        ld b,0
        ld e,(hl)
        ld d,b
        ld hl,EBUF
        add hl,de
        ld d,h
        ld e,l
        inc hl
        or a
        jp z,k_rd
        ldir
        jp k_rd
prm_t:  defb "]+**"
con_enter:
        ld a,(CON_LEN)
        ld e,a
        ld d,0
        ld hl,EBUF
        add hl,de
        ld (hl),d
        ld hl,(ESTART)
        add hl,de
        call lin_pos
        ld a,13
        rst 16
        ld hl,EMODE
        bit 2,(hl)
        res 2,(hl)
        ret nz                  ; back to INPUT
        ld hl,EBUF              ; J"" alone (an emulator auto-loading types
        ld a,(hl)               ; J, which is LOAD on a Sinclair ROM, then
        or $20                  ; "" and ENTER) runs as LOAD ""
        cp 'j'
        jr nz,ce_go
        ld de,ce_ld+5
        ld b,3
ce_q:   inc hl
        ld a,(de)
        cp (hl)
        jr nz,ce_go
        inc de
        djnz ce_q
        ld hl,ce_ld
        ld de,EBUF
        ld c,8
        ldir
        ld a,7
        ld (CON_LEN),a
ce_go:  call con_line
        jp con_new
ce_ld:  defm "LOAD \"\""
        defb 0
; con_inp: read one line into EBUF (CON_LEN) at the print position
con_inp: xor a
        ld (CON_LEN),a
        ld (EIDX),a
        ld hl,EMODE
        set 2,(hl)
        jp con_in
; redraw: print the input line from ESTART, then put the cursor at EIDX
redraw: ld hl,(ESTART)
        call lin_pos
        ld a,(CON_LEN)
        ld b,a
        inc b
        ld hl,EBUF
        jr rd_n
rd_l:   ld a,(hl)
        rst 16
        inc hl
rd_n:   djnz rd_l
        ld a,' '
        rst 16
        call pos_lin            ; the text may have scrolled up
        ld a,(CON_LEN)
        ld e,a
        ld d,0
        inc de
        or a
        sbc hl,de
        ld (ESTART),hl
        ld a,(EIDX)
        ld e,a
        add hl,de
; lin_pos: HL = row*64 + column -> S_POSN
lin_pos: ld a,l
        and 63
        add hl,hl
        add hl,hl
        ld l,a
        ld (S_POSN),hl
        ret
; pos_lin: S_POSN -> HL = row*64 + column
pos_lin: ld hl,(S_POSN)
        ld a,l
        ld l,h
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        add hl,hl
        or l
        ld l,a
        ret

con_ok: ld a,ERR_OK
        ld (ERR_NR),a
        call err_show
        jp console

; con_getkey: wait for a key with the cursor blinking every 16 frames
con_getkey:
        ei
cg_lp:  ld a,(FRAMES)
        and 16
        xor 16                  ; 16 = cursor should be showing
        ld hl,CUR_VIS
        cp (hl)
        call nz,cur_set
        ld hl,FLAGS
        bit 5,(hl)
        jr nz,cg_got
        halt
        jr cg_lp
cg_got: res 5,(hl)
        ld a,(CUR_VIS)
        or a
        ld a,0
        call nz,cur_set
        ld a,(LAST_K)
        ret
cur_set:                        ; A = new state; XOR the block at S_POSN
        ld (CUR_VIS),a
        ld hl,(S_POSN)
        ld a,l
        cp 64
        ret nc
        ld c,$F0
        rra
        jr nc,cs_1
        ld c,$0F
cs_1:   call pos_addr
        ld b,8
cs_2:   ld a,(hl)
        xor c
        ld (hl),a
        inc h
        djnz cs_2
        ret

m_con_e:
