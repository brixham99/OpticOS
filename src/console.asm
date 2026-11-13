; console.asm - phase 1 minimal console: a one-line editor with a blinking
; 4x8 cursor block after the "] " prompt.  Lines go to con_line (basic.asm):
; "> text" adds a program line, anything else runs at once.
CON_LEN equ $5B4F
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
        ld a,(S_POSN)
        or a
        ld a,13
        call nz,pr_out
        ld a,']'                ; the OpticOS direct-mode prompt
        call pr_out
        ld a,' '
        call pr_out
        xor a
        ld (CON_LEN),a
con_key:
        call con_getkey
        cp 13
        jr z,con_enter
        cp 12
        jr z,con_del
        cp 32
        jr c,con_key
        cp 128
        jr nc,con_key
        ld c,a
        ld a,(CON_LEN)
        cp 61                   ; prompt + 61 characters + cursor = 64
        jr nc,con_key
        ld e,a
        ld d,0
        ld hl,LINEBUF
        add hl,de
        ld (hl),c
        inc a
        ld (CON_LEN),a
        ld a,c
        call pr_out
        jr con_key
con_del:
        ld a,(CON_LEN)
        or a
        jr z,con_key
        dec a
        ld (CON_LEN),a
        ld a,8
        call pr_out
        ld a,' '
        call pr_out
        ld a,8
        call pr_out
        jr con_key
con_enter:
        ld a,(CON_LEN)
        ld e,a
        ld d,0
        ld hl,LINEBUF
        add hl,de
        ld (hl),0
        ld a,13
        call pr_out
        call con_line
        jp con_new

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
