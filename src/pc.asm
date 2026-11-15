; pc.asm - PicoCalc machine routines (PICOCALC builds only): the display
; device interface, the boot colour bar, the console's 40-column line
; arithmetic, and CAT.  The display device is described in sysvars.inc (DV_*).
m_pc_s:
; dev: A -> PicoCalc display register B.  Only C is changed.
dev:    ld c,DEV
        out (c),a
        ret
; dev_pos: L = column, H = row -> COL, ROW.  A, B, C changed.
dev_pos:
        ld a,l
        ld b,DV_COL
        call dev
        ld a,h
        inc b
        jr dev
; dev_attr: ATTR_T, MASK_T, P_FLAG -> ATTR, MASK, FLAG.  A, B, C, HL changed.
dev_attr:
        ld hl,(ATTR_T)          ; L = ATTR_T, H = MASK_T
        ld a,l
        ld b,DV_ATTR
        call dev
        ld a,h
        inc b
        call dev
        ld a,(P_FLAG)
        inc b
        jr dev
; dev_bar: the boot screen's row 0, a colour bar of the eight BRIGHT colours,
; five cells each (paper = ink, no pixels)
dev_bar:
        ld hl,0
        ld d,l                  ; D = colour
db_sw:  ld a,d
        add a,a
        add a,a
        add a,a
        or d
        or $40                  ; BRIGHT
        ld e,5
db_c:   push af
        call dev_pos            ; L = column, H = row 0
        pop af
        ld b,DV_CELL
        call dev
        inc l
        dec e
        jr nz,db_c
        inc d
        bit 3,d
        jr z,db_sw
        ret
; lin_pos: HL = row*COLS + column -> S_POSN.  A, B, DE changed.
lin_pos: ld de,-COLS
        ld b,-1
lp_d:   inc b                   ; B = row
        add hl,de
        jr c,lp_d
        ld a,l
        add a,COLS              ; A = column
        ld l,a
        ld h,b
        ld (S_POSN),hl
        ret
; pos_lin: S_POSN -> HL = row*COLS + column (COLS = 40).  A, DE changed.
pos_lin: ld hl,(S_POSN)
        ld a,l
        ld l,h
        ld h,0
        add hl,hl
        add hl,hl
        add hl,hl
        ld d,h
        ld e,l                  ; row*8
        add hl,hl
        add hl,hl               ; row*32
        add hl,de               ; row*40
        ld e,a
        ld d,0
        add hl,de
        ret
; st_xtra: A = token-$80 of a statement after the shared ones: CAT
st_xtra: cp T_CAT-$80
        jp nz,err_syn
        rst $20
; CAT: the files on the SD card, one name a line (the storage device lists them)
st_cat: ld bc,ST_DIR*256+STOR
        out (c),a
sc_l:   ld bc,ST_DIR*256+STOR
        in a,(c)
        or a
        ret z
        rst 16
        jr sc_l
m_pc_e:
