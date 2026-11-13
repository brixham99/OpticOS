; tokenise.asm - OpticBASIC tokeniser and LIST detokeniser (phase 3).
; Token stream: keywords $80+, $01 identifier (type, hash, length, name),
; $02 integer, $03 hex, $04 binary (lo hi), $05 float (5 bytes), $06 string
; (length, chars), $07 link slot (lo hi), $08-$0C <= >= <> << >>, $0D end.
TKF     equ $5BF9               ; 1 = at the start of a statement
WBUF    equ $5B50               ; word buffer (tape header / maths scratch)
T_CMT   equ $0E                 ; ' comment (rest of the line is raw text)
m_tok_s:
; tokenise: HL = text (0-terminated), DE = destination -> DE past the $0D
tokenise:
        ld a,1
tz_f:   ld (TKF),a
tz_lp:  ld a,(hl)
        or a
        jp z,tz_end
        inc hl
        cp ' '
        jr z,tz_lp
        ld c,a
        ld a,(TKF)
        ld b,a
        xor a
        ld (TKF),a
        ld a,c
        cp ':'
        jr nz,tz_1
        ld (de),a
        inc de
        ld a,1
        jr tz_f
tz_1:   cp $27                  ; ' at a statement start: a comment
        jr nz,tz_2
        djnz tz_em
        ld a,T_CMT
tz_raw: ld (de),a
        inc de
tz_rw2: ld a,(hl)
        or a
        jr z,tz_end
        inc hl
        jr tz_raw
tz_2:   cp '"'
        jr z,tz_str
        cp '?'
        jr nz,tz_3
        ld a,T_PRINT
        jr tz_em
tz_3:   cp '<'
        jr nz,tz_4
        ld bc,T_LE*256+'='
        call tz_two
        ld bc,T_NE*256+'>'
        call tz_two
        ld bc,T_SHL*256+'<'
        call tz_two
        ld a,'<'
        jr tz_em
tz_4:   cp '>'
        jr nz,tz_5
        ld bc,T_GE*256+'='
        call tz_two
        ld bc,T_SHR*256+'>'
        call tz_two
        ld a,'>'
        jr tz_em
tz_5:   cp '&'
        jr z,tz_hex
        cp '$'
        jr z,tz_hex
        cp '%'
        jr z,tz_bin
        cp '.'
        jr z,tz_num
        call is_dig
        jr nc,tz_num
        call is_alph
        jp nc,tz_word
tz_em:  ld (de),a
        inc de
        jp tz_lp
tz_end: ld a,13
        ld (de),a
        inc de
        ret
; tz_two: if the next character is C, emit B and continue the main loop
tz_two: ld a,(hl)
        cp c
        ret nz
        inc hl
        pop af
        ld a,b
        jr tz_em
tz_str: ld a,6
        ld (de),a
        inc de
        push de
        inc de
        ld b,0
ts_lp:  ld a,(hl)
        or a
        jp z,err_syn
        inc hl
        cp '"'
        jr nz,ts_ch
        cp (hl)
        jr nz,ts_e
        inc hl
ts_ch:  ld (de),a
        inc de
        inc b
        jr ts_lp
ts_e:   ex (sp),hl
        ld (hl),b
        pop hl
        jp tz_lp
tz_num: dec hl
        push de
        ld de,DIMB
        call fp_val
        jp c,err_syn
        pop de
        push hl
        ld hl,DIMB
        ld a,(hl)
        inc hl
        or (hl)
        jr nz,tn_f
        inc hl
        ld a,2
        ld bc,2
        jr tn_c
tn_f:   dec hl
        ld a,5
        ld bc,5
tn_c:   ld (de),a
        inc de
        ldir
        pop hl
        jp tz_lp
tz_bin: ld c,4
        jr tz_hb
tz_hex: ld c,3
tz_hb:  push de
        ld de,0
        ld b,d
th_lp:  ld a,(hl)
        call is_dig
        jr nc,th_d
        and $DF
        cp 'A'
        jr c,th_e
        cp 'G'
        jr nc,th_e
        sub 7
th_d:   sub '0'
        ex de,hl
        bit 0,c
        jr z,th_2
        add hl,hl
        add hl,hl
        add hl,hl
        jr th_1
th_2:   cp 2
        jr c,th_1
        ex de,hl
        jr th_e
th_1:   add hl,hl
        or l
        ld l,a
        ex de,hl
        inc hl
        inc b
        jr th_lp
th_e:   ld a,b
        or a
        jp z,err_syn
        ld a,c
        ld b,d
        ld c,e
        pop de
        ld (de),a
        inc de
        ld a,c
        ld (de),a
        inc de
        ld a,b
        jp tz_em
; tz_word: a keyword or an identifier
tz_word: dec hl
        push de
        ld de,WBUF
        ld b,0
tw_lp:  ld a,(hl)
        call is_alnum
        jr c,tw_e
        cp 'a'
        jr c,tw_u
        sub 32
tw_u:   ld (de),a
        inc de
        inc hl
        inc b
        bit 5,b
        jp nz,err_syn           ; words of up to 31 characters
        jr tw_lp
tw_e:   cp '$'
        jr nz,tw_e2
        ld (de),a
        inc hl
        inc b
tw_e2:  ld a,b
        ld (WLEN),a
        pop de
        call kw_find
        jr nz,tz_id
        ld (de),a
        inc de
        cp T_REM
        jp z,tz_rw2
        dec de
        ld a,(de)
        inc de
        push hl
        ld hl,lk_tab
tk_lk:  ld c,(hl)
        inc hl
        inc c
        dec c
        jr z,tk_nl
        cp c
        jr nz,tk_lk
        ld a,7
        ld (de),a
        inc de
        xor a
        ld (de),a
        inc de
        ld (de),a
        inc de
tk_nl:  pop hl
        jp tz_lp
tz_id:  ld a,1
        ld (de),a
        inc de
        ld c,0                  ; type
        push hl
        ld hl,WBUF-1
        ld a,(WLEN)
        ld b,a
        add a,l
        ld l,a
        jr nc,ti_1
        inc h
ti_1:   ld a,(hl)
        pop hl
        cp '$'
        jr nz,ti_2
        ld c,2
        dec b
        jr ti_3
ti_2:   ld a,(hl)
        cp '%'
        jr nz,ti_3
        inc hl
        inc c
ti_3:   ld a,(hl)
        cp '('
        jr nz,ti_4
        set 2,c
ti_4:   ld a,c
        ld (de),a
        inc de
        push de                 ; hash slot
        inc de
        ld a,b
        ld (de),a
        inc de
        push hl
        ld hl,WBUF
ti_lp:  ld a,(hl)
        cp 'A'
        jr c,ti_c
        cp 'Z'+1
        jr nc,ti_c
        add a,32
ti_c:   ld (de),a
        inc de
        inc hl
        add a,c
        ld c,a
        djnz ti_lp
        pop hl
        ex (sp),hl
        ld a,c
        and 31
        ld (hl),a
        pop hl
        jp tz_lp
; kw_find: WBUF/WLEN -> Z and A = token if it is a keyword
kw_find: push hl
        push de
        ld hl,kw_tab
        ld c,$80
kf_e:   ld a,(hl)
        or a
        jr z,kf_no
        push hl
        ld de,WBUF
        ld a,(WLEN)
        ld b,a
kf_c:   ld a,(hl)
        and $7F
        ex de,hl
        cp (hl)
        ex de,hl
        jr nz,kf_x
        dec b
        jr z,kf_l
        bit 7,(hl)
        jr nz,kf_x
        inc hl
        inc de
        jr kf_c
kf_l:   bit 7,(hl)
        jr z,kf_x
        pop hl
        ld a,c
        cp a
        jr kf_r
kf_x:   pop hl
kf_s:   bit 7,(hl)
        inc hl
        jr z,kf_s
        inc c
        jr kf_e
kf_no:  inc a
kf_r:   pop de
        pop hl
        ret
; character classes: CF clear if A is one
is_dig: cp '0'
        ret c
        cp '9'+1
        ccf
        ret
is_alnum: call is_dig
        ret nc
        cp '_'
        ret z
is_alph: cp 'A'
        ret c
        cp 'Z'+1
        ccf
        ret nc
        cp 'a'
        ret c
        cp 'z'+1
        ccf
        ret

m_tok_e:
