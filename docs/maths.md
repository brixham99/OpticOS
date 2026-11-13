# OpticOS maths package (phase 2)

Clean-room floating point for OpticBASIC: `src/fpcore.asm` (core),
`src/fpconv.asm` (number <-> text), `src/fptrans.asm` (byte-code runner,
transcendentals, RND, `^`) and the generated constant/coefficient tables in
`src/gen/` (written by `tools/fpcoef.py`). The phase 3 seed expression evaluator and
`PRINT` are in `src/expr.asm`. Nothing here comes from the Sinclair ROM.
The coefficients are OpticOS's own Chebyshev fits made with mpmath. The
12-byte similarity check passes.

## 1. Number formats

**Packed (5 bytes, in variables and on the value stack).** The layout is Sinclair-compatible
(spec 4.2), so legacy `CODE` data and tape headers read the same way.

| Form | Bytes | Value |
|---|---|---|
| float | `e  m4\|s  m3  m2  m1` | 0.1m4m3m2m1 (binary) × 2^(e−128); the top mantissa bit is implicit and its place holds the sign |
| small int | `00  s  lo  hi  00` | s = `$00` or `$FF`; lo/hi = two's complement low 16 bits; range −65535…65535 |
| zero | `00 00 00 00 00` | |

Canonical rule: every result that is an integer in −65535…65535 is stored
as a small int (pack, VAL, INT, the arithmetic fast paths). So "is it a small int?"
is just `byte0 == 0`, and phase 3 can use that for FOR loops, array subscripts and
PEEK/POKE arguments without conversion. The rig checks this on every result.

**Unpacked (8 bytes, working registers FA, FB, T0–T6).**

| +0 | +1 … +4 | +5 | +6 |
|---|---|---|---|
| guard byte (rounding) | m1 (low) … m4 (top bit always set) | exponent (bias 128; 0 means the value is zero) | sign `$00`/`$80` |

## 2. Workspace (RAM, see `src/sysvars.inc`)

| Name | Address | Size | Use |
|---|---|---|---|
| FA, FB | `$5B80`, `$5B88` | 8 + 8 | accumulator and operand |
| FT = T0…T5, T6 | `$5B90`…`$5BC0` | 7 × 8 | byte-code temporaries (T6 is used by POLY and RND, internal only) |
| VSP (value stack moved below RAMTOP in phase 3, see docs/phase3) | `$5BFE` | 2 | expression value stack pointer; the stack itself is VSB…VSLIM |
| NBUF, NDIG, NDE, NCNT, NBP | `$5B62`… | 16 + 9 + 4 | fp_str output buffer and digit work area |
| VDX, FSG, FRP | `$5B7D`, `$5B61`, `$5BFC` | | VAL decimal exponent, add/sub selector, right-operand pointer |
| RNDS | `$5C93` | 4 | 32-bit xorshift state (SEED, `$5C76`, keeps the last RANDOMIZE value) |

## 3. Calling conventions

All routines may change AF, BC, DE and HL. IX and IY are preserved, and the alternate set is not used.
Errors never return. They go out through `RST 8` with an OpticOS code and unwind to
`ERR_SP` (spec §7.8), so callers need no error checks.

### Packed level (what phase 3 calls)

| Routine | In | Out |
|---|---|---|
| `fp_add` `fp_sub` `fp_mul` `fp_div` `fp_pow` | HL = left operand, DE = right | (HL) = left op right; (DE) unchanged |
| `fp_cmp` | HL = left, DE = right | A = `$FF` / `0` / `1` for < / = / >, S and Z flags to match; nothing written |
| `fp_neg` `fp_abs` `fp_sgn` `fp_int` | HL = number | changed in place (INT = floor) |
| `fp_sqr` `fp_sin` `fp_cos` `fp_tan` `fp_atn` `fp_asn` `fp_acs` `fp_exp` `fp_ln` `fp_log` | HL = number | changed in place |
| `fp_tst` | HL = number | A = `$FF` / `0` / `1` (sign), flags set |
| `fp_rnd` | HL = destination | 0 ≤ RND < 1 |
| `fp_randomize` | DE = seed (0 = use FRAMES) | |
| `fp_set_int` | HL = destination, DE = signed 16-bit | small int stored |
| `fp_get_int` | HL = number | DE = nearest integer (two's complement), A = sign `$00`/`$FF` (so −65535…65535); CF set if out of range |
| `fp_str` | HL = number | HL = NBUF, B = length (text, not terminated) |
| `fp_val` | HL = text, DE = destination | number stored, HL just past it; CF set (nothing stored) if the text does not start with a number |
| `fp_pi` | DE = destination | π |

Small-int fast paths: add and sub (16-bit with sign extension, and they fall back to float
when the result leaves −65535…65535), mul (16×16 into 16, and they fall back on overflow),
cmp, neg, abs, sgn, int, get/set_int. A result outside the range is computed again in float
from the original operands, so the fast path never changes a result.

### Unpacked level (for phase 3 routines that chain several operations)

`fu_ld2` (HL→FA, DE→FB), `fu_unpack` (HL packed → DE unpacked), `fp_stA` (pack FA into (HL)),
`fu_pack` (HL unpacked → DE packed), `fu_add` `fu_sub` `fu_mul` `fu_div` (FA = FA op FB, FB changed),
`fu_cmp` (FA ? FB), `fu_from16` (HL = destination, DE = magnitude, C = sign `$00`/`$80`),
`fu_fix` (FA → DE = |nearest|, C = sign, CF if ≥ 65535.5), `fu_scl` (FA ×= 10^A),
and `fu_sin`, `fu_cos`, `fu_tan`, `fu_atn`, `fu_asn`, `fu_acs`, `fu_sqr`, `fu_exp`, `fu_ln`, `fu_log` and `fu_rnd` on FA.

### Byte-code (`call fu_run`, the bytes, then `END_`; Z80 code carries on after END_)

| Code | Op | Meaning |
|---|---|---|
| `$00+s` | `LD_ s` | FA = s |
| `$20+t` | `ST_ t` | Tt = FA |
| `$40+s` `$60+s` `$80+s` `$A0+s` | `ADD_` `SUB_` `MUL_` `DIV_` | FA = FA op s |
| `$C0+n`, then n × 5 bytes | `POLY_ n` | FA = Horner polynomial in FA, coefficients highest power first |
| `$E0` | `END_` | back to Z80 |
| `$E1` | `NEG_` | FA = −FA |

The source s is 0–5 for T0–T5, or 6+ for constant `K_*` (`src/gen/kequ.inc`: ONE, HALF, 2/π,
π/2 high/low, π/2, π/6, √3, log2 e, ln 2 high/low, 1/ln 10, the SQR seed, TEN, 1E8, 1E9, tan 15°, π).

### Expression evaluator and PRINT (phase 3 seed, `src/expr.asm`)

`ev_expr` evaluates the text at `CH_ADD` and leaves one 5-byte value on the value stack (`ev_top` → HL).
Precedence, from loosest: `+ -`, then `* /`, then unary `-`, then `^` (left-associative), then functions
and primaries. Primaries are a number, `(expr)`, `PI` and `RND`. The functions are `SQR SIN COS TAN ATN ASN ACS EXP LN LOG INT ABS SGN`,
which take a primary, so `SIN(PI/6)` and `SQR 2` both work. `cmd_print` handles `"text"` (with `""` for a quote mark),
numbers, `;` (no gap), `,` (next 16-column zone at 64 columns) and a trailing `;` (no newline).
Console commands go through one table (`cmd_tab` in `console.asm`: `PRINT`, `?`, `CLS`, `LOAD ""`).
A handler starts with CH_ADD just past the keyword.

## 4. Algorithms

| Function | Method |
|---|---|
| + − | align exponents through the guard byte, add or subtract the 40-bit mantissas, normalise, round to nearest (ties away) |
| × | 32×40-bit shift-and-add into a 40-bit result, one byte of the multiplier at a time |
| ÷ | restoring division, 40 quotient bits |
| SIN COS | q = round(x·2/π); r = x − q·(π/2)hi − q·(π/2)lo; sin r = r·S(r²) (5 terms), cos r = C(r²) (6); quadrant from q |
| TAN | sin r / cos r on the reduced argument (−cos/sin in odd quadrants) |
| ATN | \|x\| > 1 → π/2 − ATN(1/x); t > tan 15° → π/6 + ATN((t√3 − 1)/(t + √3)); then t·A(t²) (6 terms) |
| ASN | 2·ATN(x / (1 + √((1−x)(1+x)))) |
| ACS | x ≥ 0: 2·ATN √((1−x)/(1+x)); x < 0: π/2 − ASN x |
| SQR | halve the exponent; linear seed; three Newton steps |
| EXP | n = round(x·log2 e); f = x − n·(ln 2)hi − n·(ln 2)lo; e^f by a 9-term polynomial; exponent += n |
| LN | m ∈ [0.707, 1.414); s = (m−1)/(m+1); s·P(s²) (5 terms) + e·ln 2 in two parts |
| LOG | LN x × (1/ln 10) |
| x^y | integer y: repeated squaring (y < 0 → 1/x^\|y\|, 0^0 = 1); otherwise EXP(y·LN x) |
| RND | 32-bit xorshift (13, 17, 5); value = state / 2^32 |
| STR$/PRINT | estimate the decimal exponent from the binary one; scale to [1E8, 1E9) with 10^k built by squaring (in steps of 10^32 when \|k\| > 31); round to an integer; 9 digits; strip zeros; fixed for 1E-5 ≤ \|x\| < 1E9, otherwise `d.dddE±n` |
| VAL | digits accumulate as 10·a + d (11 kept, the rest only counted); decimal point and `E±n` adjust one exponent; one fu_scl at the end |

## 5. Errors

| Code | Message | Raised by |
|---|---|---|
| `$05` ERR_DIV0 | Division by zero | ÷ by 0; 0^negative |
| `$06` ERR_OVFL | Overflow | any result ≥ 2^127 (×, ÷, +, EXP, ^, VAL, PRINT never) |
| `$0B` ERR_ARG | Bad argument | SQR x<0, LN/LOG x≤0, ASN/ACS \|x\|>1, SIN/COS/TAN \|x\| > ~102900 |
| `$0D` ERR_SYN | Syntax error | evaluator, PRINT, unknown command |

Underflow is silent: the result becomes 0.

## 6. Accuracy and speed

Measured by `tools/rig/test_maths.py` (Z80 core plus mpmath at 200 bits). The table is in
[phase2/README.md](phase2/README.md) and `build/maths_results.md`.

## 7. Known limits

- SIN, COS and TAN need |x| < about 102900 (q must fit 16 bits). Beyond that the result would be noise anyway.
- `x^y` for non-integer y loses about log2(|y·ln x|) bits (up to about 55 ulp at the extremes), because ln x is only computed to 32 bits.
- Integer `x^-n` overflows if x^n overflows, even when the true result is representable.
- TAN gets near its poles by dividing two 32-bit results: up to about 3 ulp.
- PRINT shows 9 digits. That is not quite enough to give back every 32-bit value: VAL(STR$ x) is within 4 ulp. Decimals of 8 digits or fewer print as they were typed.
- `&`hex and `%`binary literals (spec item 13) are not done yet. They are phase 3, together with the tokeniser.
