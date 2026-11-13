; edit.asm - phase 4 line editor: the current-line marker, LIST around it,
; cursor up/down and EDIT (see docs/phase4/README.md)
m_edt_s:
; ---------------------------------------------------- line editor
; The current line CURL carries the LIST marker.  Cursor up/down move it
; and list the lines around it; EDIT copies it into the input line.
; lst: list the program from line HL (earlier lines only set the indent),
; at most B lines (0 = all), ">" before the current line
lst:    ld (TMP),hl
        ld a,b
        ld (BCN),a
        xor a
        ld (LSTLV),a
        ld hl,OPROG
lt_l:   ld a,(hl)
        or a
        jr z,lt_x
        push hl
        ld de,(TMP)
        call cphd
        ld de,nul_ch
        jr c,lt_o
        ld a,(BCN)
        or a
        jr z,lt_1
        dec a
        jr z,lt_xp
        ld (BCN),a
lt_1:   ld de,(CURL)
        call cphd
        ld de,CHANTAB+5
        ld (CURCHL),de
        ld a,'>'
        call z,pr_ch
        ld de,CHANTAB+5
lt_o:   ld (CURCHL),de
        pop hl
        push hl
        call list_line
        pop hl
        call nxl
        jr lt_l
lt_xp:  pop hl
lt_x:   ld hl,CHANTAB+5
        ld (CURCHL),hl
        ret
nul_ch: defw $+2                ; a channel that drops its output
        ret
cap_ch: defw cap_out            ; a channel that fills the input line
cap_out: cp 13
        ret z
        ld c,a
        ld hl,CON_LEN
        ld a,(hl)
        cp EMAX
        ret nc
        inc (hl)
        ld e,a
        ld d,0
        ld hl,EBUF
        add hl,de
        ld (hl),c
        ret
; elist: clear the screen and list about ten lines either side of the marker
elist:  call CLS
        ld hl,(CURL)
        ld a,h
        or l
        jr nz,el_1
        ld hl,OPROG
el_1:   ld b,10
el_b:   push hl
        push bc
        call prv
        pop bc
        pop de
        jr z,el_t
        djnz el_b
        ex de,hl
el_t:   ex de,hl
        ld b,21
        jp lst
; prv: HL = line -> the line before it (Z and HL = 0 if HL is the first)
prv:    ld de,OPROG
        or a
        sbc hl,de
        ret z
        add hl,de
        dec hl
        ld e,(hl)
        inc hl
        ld d,0
        sbc hl,de
        ret
; cursor keys: move the marker and relist
c_up:   ld hl,(CURL)
        ld a,h
        or l
        jr z,c_list
        call prv
        jr c_set
c_down: ld hl,(CURL)
        ld a,h
        or l
        ld hl,OPROG
        jr z,cd_1
        ld hl,(CURL)
        call nxl
cd_1:   ld a,(hl)
        or a
        jr z,c_list
c_set:  ld (CURL),hl
c_list: call elist
        jp con_new
; con_edit: EDIT copies the current line into the input line; a second
; EDIT empties it (ENTER on an empty edit then deletes the line)
con_edit:
        ld hl,EMODE
        bit 1,(hl)
        jp nz,con_new
        ld hl,(CURL)
        ld a,h
        or l
        jp z,con_key
        ld a,(EMODE)
        or 2
        ld (EMODE),a
        xor a
        ld (CON_LEN),a
        ld (LSTLV),a
        ld de,cap_ch
        ld (CURCHL),de
        call list_line
        ld hl,CHANTAB+5
        ld (CURCHL),hl
        ld a,(CON_LEN)
        ld (EIDX),a
        ld hl,(ESTART)          ; reprint the prompt in place
        dec hl
        dec hl
        call lin_pos
        jp con_pr

m_edt_e:
