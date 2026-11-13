; cls.asm - CLS at $0D6B: clear the screen to ATTR_P and home the cursor.
m_cls_s:
CLS:    ld hl,$4000
        ld de,$4001
        ld bc,6143
        ld (hl),0
        ldir
        inc hl
        inc de
        ld a,(ATTR_P)
        ld (hl),a
        ld bc,767
        ldir
        ld hl,(ATTR_P)          ; ATTR_P, MASK_P -> ATTR_T, MASK_T
        ld (ATTR_T),hl
        ld hl,0
        ld (S_POSN),hl
        xor a
        ld (PR_CTRL),a
        ld (CUR_VIS),a
        ret
m_cls_e:
