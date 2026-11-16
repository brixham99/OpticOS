# Print edition (A5, ring bound, double-sided)

Made by `python3 docs/manual/build_print.py` (or `make manual-print`) from the same `manual.md` and `template.html` as the on-screen PDF, which is left as it is.

| File | What it is |
|---|---|
| `OpticOS_Manual_A5_cover.pdf` | The front cover: one page, 154 × 216 mm (A5 plus 3 mm bleed on every edge; TrimBox set to the A5 trim) |
| `OpticOS_Manual_A5_interior.pdf` | The inside pages: exactly A5 (148 × 210 mm), no bleed, everything but the front cover, padded with blank pages to a multiple of 4. Page 1, the title page, is a recto |
| `cover_source_ringbound.pdf` | Nathan's ring-bound cover design, the source for the cover |

**Cover.** Nathan's layout, re-set at 154 × 216 mm. His page maps onto the trim; his background picture (1152 × 1728, about 190 ppi at this size) is scaled to cover the bleed; his logo image (about 259 ppi) and his text (vector, the embedded Aptos subset) keep their relative places. The copyright line is moved up to 5 mm inside the trim. The left-hand text is 13.7 mm inside the trim, clear of a 12 mm ring-hole zone.

**Interior.** Laid out afresh for A5 (not shrunk), with a binding gutter: the inner margin is 20 mm (left on odd pages, right on even pages) and the outer 12 mm; headers, page numbers and pictures follow. Listings never wrap. A code box too wide is set smaller, but never below 6 pt; a line still too long at 6 pt is broken, and the rest goes on the next line after a "→" (in the assembler listing as a "; →" comment), with a note under the box. A broken line and its continuation stay on the same page. The page numbers count from the title page, and the contents page matches them.

Needs Python with `pypdf` and `markdown`, plus Google Chrome and poppler-utils.
