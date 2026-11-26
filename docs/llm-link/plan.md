# OpticBASIC LLM link — proof-of-concept design (RC-11)

Design only. No ROM code in this phase. British English.

The 128K Spectrum, under OpticOS, talks to an LLM (the Grok API) through Fuse's emulated Interface 1 RS-232, a pair of host FIFOs, and a small Python helper. Later the same Z80 I/O can drive a real Interface 1 (or a compatible serial port) into a Raspberry Pi 3. This document is the plan for that proof of concept.

OpticBASIC programs have no line numbers. Examples in this note are unnumbered.

## 1. Goal and architecture

```
OpticBASIC  (ASK / stream #4)
    -> extension ROM, bit-banged RS-232 on the Interface 1 ports
    -> Fuse IF1 emulation
    -> FIFO files (--rs232-tx / --rs232-rx)
    -> host Python helper
    -> Grok API  (or a mock/echo mode)
    -> helper wraps the reply to 32 or 64 columns
    -> FIFO back to Fuse
    -> INPUT # / ASK receives the text
```

The Spectrum never speaks HTTP. It only sends and receives a short, line-based serial protocol. The helper owns the API key, the model, wrapping, and timeouts.

This is a 128K feature: it lives in the extension ROM, once SAY has been moved to tape (or, if Nathan prefers, a slimmer ASK-only first cut may fit in the 1,204 bytes already free — see §8).

## 2. What Fuse 1.6.0 actually offers

The installed emulator is **Fuse 1.6.0** (`fuse-sdl`, man page dated 27 February 2021). `--help` is brief and does **not** list the Interface 1 or RS-232 switches; they are in the man page.

| Option | What it does |
|---|---|
| `--interface1` | Attach a Sinclair Interface 1, including its RS-232. Same as *Options → Peripherals → Interface 1*. |
| `--rs232-tx FILE` | Fuse writes the Spectrum's transmit wire to this FIFO or file. |
| `--rs232-rx FILE` | Fuse reads the Spectrum's receive wire from this FIFO or file. |
| `--no-rs232-handshake` | Assume the other end is live when the channels are connected. **Use this for the PoC.** |
| `--rom-interface-1 FILE` | File Fuse loads as the Interface 1 *shadow ROM*. Default name `if1-2.rom`. |

The GUI also has *Media → Interface 1 → RS232 → Plug/Unplug RxD/TxD*, and a general *RS-232 handshake* checkbox that matches `--no-rs232-handshake` when turned off.

Handshake, when left on (the default), is not a hardware UART setting. Fuse then injects escape sequences on the FIFO: `0x00` is the escape byte, and a bare `0x00` in the data is rewritten (Fuse bug [#514](https://sourceforge.net/p/fuse-emulator/bugs/514/) reports `0x00` becoming `0x00 0x2A`). There is no `--rs232-baud` on this build — unlike an unmerged AY-serial patch, Interface 1 baud is determined only by the Z80's bit timing. There is no separate "rs232 mode" switch in 1.6.0; the old raw/interpreted setting was replaced by the handshake option.

Fuse opens the FIFOs in a way that is not supposed to block the emulator. The helper should still open both ends carefully (for example `O_RDWR` on each FIFO, or open read and write in either order without deadlocking).

Fuse **does** emulate Interface 1 with a shadow ROM. It looks for `if1-2.rom` in `~/.spectrum-roms`, `/usr/local/share/spectrum-roms` and the usual Debian paths (see the package `README.Debian`). That file is **not** supplied with this Fuse build, and we must not add, read, disassemble or ship the Sinclair Interface 1 ROM. Our code will drive the hardware ports directly. For Fuse to accept `--interface1` at all, *a* file must be given with `--rom-interface-1`. That file should be an **OpticOS-written page-in stub**, not Sinclair's ROM — see §4 and §8.

### Check performed (26 November 2026)

Command, run from Fuse's data directory so `fuse.font` is found (`/workspace/tools-prefix/usr/share/fuse`):

```
mkfifo /tmp/optic-rs232-tx /tmp/optic-rs232-rx
fuse-sdl --machine 128 \
  --rom-128-0 opticos.rom --rom-128-1 opticos128ext.rom \
  --interface1 --rom-interface-1 /tmp/if1-dummy.rom \
  --no-rs232-handshake \
  --rs232-tx /tmp/optic-rs232-tx --rs232-rx /tmp/optic-rs232-rx \
  --no-auto-load --no-traps --no-confirm-actions
```

`opticos.rom` and `opticos128ext.rom` were the v1.1 release images. `/tmp/if1-dummy.rom` was 8,192 bytes of `0xFF` — not a Sinclair ROM.

- Without `--rom-interface-1`, and with no `if1-2.rom` on Fuse's search path, Fuse printed `couldn't find ROM 'if1-2.rom'` (and still opened a window).
- With the dummy file, Fuse started cleanly, no stderr, and OpticOS v1.1 reached its `] ` prompt.
- `PRINT 1/0` then *destroyed* the display (blue vertical bars, no OpticOS error report). That is the Interface 1 shadow-ROM page-in at `$0008` (RST 8, OpticOS's error entry) running the dummy image. This is expected hardware behaviour, and it is why a real stub is required before any RS-232 work. See §4.

## 3. Interface 1 ports (public hardware documentation only)

The Interface 1 RS-232 is not a UART. The Z80 bit-bangs a single data bit and two handshake bits. Port addresses and bit roles below are taken from public hardware documentation, not from any ROM listing:

- Sinclair Research, *ZX Microdrive, Interface 1 and Interface 2 Service Manual*, I/O port table (about §1.4.6) and RS-232 section (about §1.5). Public copies are on World of Spectrum and Spectrum for Everyone.
- *comp.sys.sinclair* FAQ / World of Spectrum, [48K ZX Spectrum Technical Information — ZX Interface I](https://worldofspectrum.net/faq/reference/48kreference.htm), ports `$E7`, `$EF`, `$F7`.
- [Sinclair Wiki, ZX Interface 1](https://sinclair.wiki.zxnet.co.uk/wiki/ZX_Interface_1), port table.

We will not use, read or cite any Interface 1 ROM disassembly (including Geoff Wearmouth's listings linked from that FAQ).

| Port | Role |
|---|---|
| `$EF` (239) | Control (write) and status (read). |
| `$F7` (247) | Serial / network data bit. |
| `$E7` (231) | Microdrive data. **Do not use.** An access can halt the Z80 if no drive is running. |

Port `$EF`:

```
Bit     7    6    5     4      3      2       1          0
Read  |         |    | busy | DTR  | gap  | sync    | write prot |
Write |         | wait| CTS  | erase| R/W  | comms clk| comms data |
```

Port `$F7`:

```
Bit     7         6 5 4 3 2 1    0
Read  | Tx DATA |               | net input           |
Write |                         | net output / Rx DATA |
```

Notes that matter for us, still from those sources:

- **COMMS DATA** (write `$EF` bit 0) selects where bit 0 of `$F7` goes: set it to route the bit to RS-232, reset it for the Sinclair network.
- **Tx DATA** (read `$F7` bit 7) is the bit *received from the line*. **Rx DATA** (write `$F7` bit 0) is the bit *we transmit*. The Service Manual uses DCE names; the Interface 1 is a DCE.
- **DTR** (read `$EF` bit 4) means the remote end wishes to send. **CTS** (write `$EF` bit 3) means the Spectrum wishes to send. Under Fuse with `--no-rs232-handshake`, Fuse treats the far end as live once the FIFOs are connected, so the PoC can hold CTS asserted and not depend on DTR changing. On real hardware, wait for DTR before sending a long burst, and drop CTS if our receive buffer is full.
- The same IC pin is shared with the network; selecting RS-232 with COMMS DATA is mandatory.

Paging, also public (same FAQ): the Interface 1 *shadow ROM* is paged in when the Z80 fetches an instruction at `$0008` or `$1708`, and paged out when it executes the `RET` at `$0700`. Fuse emulates this. OpticOS uses RST 8 (`$0008`) as its error entry, so enabling Interface 1 without a correct stub breaks every BASIC error. Our code must never jump into, copy, or rely on Sinclair's shadow ROM.

## 4. The Z80 side

All serial I/O sits in the 128K extension ROM and talks to `$EF` / `$F7` only.

**Bit-banged timing.** Default **2,400 baud**, 8 data bits, no parity, one stop bit. At 3.5 MHz that is about 1,458 T-states per bit — loose enough under contended memory, and the same loops should later talk to a real Interface 1. 9,600 (about 365 T-states per bit) can be a later option, but it is tight. Interrupts are **off** for the duration of each byte (and, for a first cut, for a whole short line). BREAK is still polled between bytes so a hung receive can be abandoned. Start-bit detection on receive uses a timeout (see §6).

**Buffer.** A receive buffer in RAM, 1,024 bytes, above RAMTOP or in a spare 128K bank that SAY is not using. One prompt is at most 256 characters; a longer reply is truncated and the user sees that it was cut.

**Page-in stub (our file, not Sinclair's).** Fuse requires `--rom-interface-1` to attach the peripheral. We will later supply a tiny original 8K image (working name `opticos-if1stub.rom`) whose only job is: when Fuse pages it in at `$0008` or `$1708`, unpage immediately via the published `$0700` `RET` trigger, then continue into OpticOS at an address that does *not* re-enter `$0008` (the body of the error handler, not the RST 8 vector itself). The stub contains no Sinclair code. It is not part of this design-only commit.

**Byte estimate.** The v1.1 extension has **1,204 bytes free**. In the current map, SAY ends at `codeend` `$28A6`; the speech statements and engine occupy about **6.1–6.9K** (`n_say`…`codeend` = 6,131 bytes; `em_say`…`codeend` = 6,856). The brief's figure of about 7.6K freed by moving SAY to tape is a comfortable planning number; even the measured 6.1K plus the 1,204 already free is around 7.3K, which is ample.

| Piece | ASK-only, bytes (rough) | With streams as well |
|---|---:|---:|
| Port init, bit-bang TX/RX, delays, BREAK, timeout | 250–350 | 250–350 |
| Line assembly and 1K buffer | 80–120 | 80–120 |
| Protocol, errors, messages | 120–180 | 120–180 |
| `ASK` | 100–150 | 100–150 |
| `OPEN` / `CLOSE` / `PRINT #` / `INPUT #` | — | 400–700 |
| **Total** | **about 600–900** | **about 1.0–1.6K** |

ASK-only might already fit in the 1,204 bytes free, without waiting for SAY to move. Full streams are a tight squeeze until that move. The main ROM has only 102 bytes free and `CHAN-OPEN` (`$1601`) is a stub, so new keywords and almost all of the work belong in the extension, with at most a SAY-style hook in the main ROM.

## 5. OpticBASIC syntax

Clean-room streams. The device name is `"AI"`, not Sinclair's `"b"` or `"t"`.

```
OPEN #4,"AI"
PRINT #4;"What is a Spectrum?"
INPUT #4;a$
PRINT a$
CLOSE #4
```

Convenience form, one shot, same protocol:

```
ASK "What is a Spectrum?";a$
PRINT a$
```

`ASK` uses the current screen width (32 or 64) when it asks the helper to wrap. Stream 4 is the usual choice; 5–15 are allowed if 4 is taken. No line numbers. `INPUT #4;a$` reads up to the end-of-reply marker (§6), not a single line only, so a wrapped paragraph lands in one string (newlines kept as `CHR$ 13`).

v1.1 has no user streams today (`OPEN` / `CLOSE` / `PRINT #` / `INPUT #` are not implemented). Whether the first coded cut is `ASK` alone, or the full stream set, is an open question for Nathan (§8).

## 6. Wire protocol

Line-based, 8-bit, no parity, 1 stop. **`--no-rs232-handshake`**, and the protocol itself avoids `NUL` (`$00`) so a mistaken handshake setting cannot corrupt a frame.

- The Spectrum sends one prompt line, ASCII, ending with CR (`$0D`). Optionally prefixed with `W32` or `W64` and a space, so the helper can wrap without a command-line flag. `ASK` always writes that prefix from `OMODE`.
- The helper accepts CR, LF or CRLF as a line end. It replies with lines ended by CR only (Spectrum-friendly), already wrapped to 32 or 64 columns.
- After the last text line it sends a line containing only the three characters `END` and a CR. That is the end-of-reply marker. It is typable, visible in mock mode, and does not clash with ordinary English if we require it to be the *whole* line.
- Maximum prompt 256 bytes including the prefix; maximum reply 1,024 bytes of text (the marker is not stored in `a$`). Over-long replies are truncated, then `END` is still sent; the Spectrum may append a short notice such as `[cut]`.
- Timeouts: the helper waits 30 seconds for the API (configurable). The Z80 waits the same order of time for the first reply byte, and a much shorter per-byte timeout once a line has started. BREAK abandons the receive. If the helper is down, the Spectrum reports a timeout, not a hang.
- Busy: a second `PRINT #` / `ASK` while a reply is still arriving is an error, `Busy`.
- Helper failures come back as a single line `!ERROR ` plus a short plain-ASCII reason, then `END`. The Spectrum reports that text.
- Character set: the helper's system prompt demands **plain ASCII** — no typographic quotes, no markdown fences, no characters outside `$20`–`$7E` except CR. On the way in, anything else becomes `?`. Spectrum `$60` (often a pound sign on a Sinclair font; OpticOS's 64-column font may differ) is sent as `` ` `` or `GBP`, not as UTF-8. Code `$7F` is the OpticOS cursor block, not ©; it is not used on the wire. The banner's `(c)` convention already avoids ©.

Mock/echo mode speaks this exact protocol, so the Z80 path can be tested with no API key.

## 7. Host helper

A single Python 3 script (stdlib plus `urllib`, no SDK required for the PoC).

- API key from the environment variable `XAI_API_KEY`. Never committed, never written to a FIFO log by default.
- Base URL `https://api.x.ai/v1`. First cut can use `POST /v1/chat/completions` (OpenAI-shaped, simple). The newer Responses API is fine later if we want it.
- Model from `--model` or `XAI_MODEL`, default `grok-4.7` (current API default at the time of writing; easy to change).
- System prompt: you are answering a ZX Spectrum over a slow serial line. Keep replies short, plain ASCII, no markdown, no typographic punctuation, at most a handful of short sentences. The helper still wraps to the requested width.
- `--echo` / `--mock`: do not call the API. Reply with a short wrapped echo of the prompt, then `END`. Useful when `XAI_API_KEY` is unset.
- `--tx` / `--rx` FIFO paths, matching Fuse's `--rs232-tx` / `--rs232-rx` the other way around (the helper *reads* Fuse's tx file and *writes* Fuse's rx file).
- `--timeout`, `--width` as a fallback when the Spectrum sends no `W32`/`W64` prefix.

## 8. PoC steps and a Fuse test plan

Do this in order. No Sinclair IF1 ROM at any step.

1. **Page-in stub.** Write `opticos-if1stub.rom` from the public paging rules in §3. In Fuse, with Interface 1 enabled, `PRINT 1/0` must once again show a normal OpticOS error and return to `]`.
2. **Echo helper and FIFOs.** Launch Fuse as in §2, but with the stub instead of the dummy, and run the helper in `--echo`. A host-side write to the rx FIFO must appear as bytes when the (still test-level) Z80 receive loop runs, and vice versa.
3. **Z80 bit-bang in the extension.** Transmit and receive one line at 2,400 baud, interrupts off, with a RAM buffer and a timeout. Prove it with the echo helper: `ASK "HELLO";a$` then `PRINT a$` shows the echoed text, wrapped, with no `END` in `a$`.
4. **Grok.** The same path with `XAI_API_KEY` set and `--echo` off. A short question returns a short wrapped answer. A missing key or an HTTP error becomes `!ERROR …`.
5. **Streams**, if they were not part of step 3: `OPEN #4,"AI"` / `PRINT #4` / `INPUT #4;a$` / `CLOSE #4`.

Fuse test plan for steps 3–5:

- Boot with the v1.1 images, the stub, `--interface1`, `--no-rs232-handshake`, and the two FIFOs. Prompt is `]`.
- `PRINT 1/0` still reports an OpticOS error (stub regression test).
- Echo: `ASK "HELLO NATHAN";a$` fills `a$` and prints it; width 64 and width 32 (`SCREEN 1`) both wrap correctly.
- Timeout: helper stopped, then `ASK` reports a timeout and accepts BREAK.
- Error path: helper sends `!ERROR no key` and `END`.
- Optional: leave handshake *on* and confirm we still recommend leaving it off; our frames contain no `NUL`, but we do not rely on that as the normal setup.

## 9. Later, on real hardware

The same port I/O should run on a real Interface 1. A Raspberry Pi 3 is a good helper host, but its UART is 3.3 V TTL; the Interface 1 is proper RS-232 at about ±12 V. Use a level-shifted RS-232 adaptor (for example a USB-serial dongle, or a MAX3232), never the Pi's pins straight to the IF1 connector. Wiring is a null-modem: cross TX/RX and, if handshake is used, DTR/CTS, plus ground (the Service Manual and the Interface 1 user cabling notes).

**Retro Games' The Spectrum** is a HDMI/USB replica that emulates 48K / 128K / +2 / +2A and loads software from USB. It has no Interface 1, no Microdrive and no RS-232 port. Treat this feature as **unsupported** on that machine — emulator (Fuse) or real Interface 1 only.

## 10. Risks and open questions for Nathan

**Risks**

- Interface 1 page-in at `$0008` is real in Fuse; a dummy ROM already broke OpticOS errors. The stub is on the critical path.
- `$1708` is also a published page-in address. We must not leave OpticOS executing there with Interface 1 attached without a matching stub path.
- Fuse's RS-232 is known to buffer a little and is not identical to a real Interface 1 (noted by other people who used the FIFOs). Bit timing must still be correct, or the same binary will fail on hardware.
- Contention and interrupt-off pauses: a 1K reply at 2,400 baud is a few seconds of muted interrupts (FRAMES will lag; keyboard except BREAK is deaf). Acceptable for a PoC.
- Main-ROM keyword space and the `CHAN-OPEN` stub: full streams may need a careful hook so we do not spend the last 102 bytes.
- FIFO open order and helper crashes must not freeze Fuse or the BASIC.
- API cost and key leakage: env var only; no key in the repo, in screenshots, or in default logs.

**Open questions**

1. Is **ASK-only** acceptable for the first coded cut, with `OPEN #` / `PRINT #` / `INPUT #` in a second cut?
2. Should we **move SAY to tape first**, or try to land ASK in the 1,204 bytes already free?
3. Default baud **2,400** (safer on a real IF1) or **9,600** (fine if Fuse is forgiving)?
4. Is the helper **stateless** (each `ASK` is a new chat) or do we keep a short multi-turn history in the helper process?
5. Please confirm the clean-room path: **our own page-in stub**, never the Sinclair Interface 1 ROM, is the way to make Fuse attach the ports.
6. Default model `grok-4.7` and env var `XAI_API_KEY` — any preference?
7. Reply cap of **1,024 bytes**, and wrap width taken automatically from the current `SCREEN` mode: agreed?
8. Any wish to expose this on **48K** later, via a different serial add-on? Out of scope for the PoC.

