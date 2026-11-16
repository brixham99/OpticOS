# Print edition (A5)

Made by `python3 docs/manual/build_print.py` (or `make manual-print`) from the same `manual.md` and `template.html` as the on-screen PDF, which is left as it is.

| File | What it is |
|---|---|
| `OpticOS_Manual_A5_cover.pdf` | The front cover: one page, 154 × 216 mm (A5 plus 3 mm bleed on every edge), Nathan's artwork at about 348 dpi |
| `OpticOS_Manual_A5_interior.pdf` | The inside pages: exactly A5 (148 × 210 mm), no bleed, everything but the front cover, padded with blank pages to a multiple of 4 |
| `cover_artwork.png` | Nathan's cover artwork (1920 × 2773), the source for the cover |

The cover artwork is placed 140 mm wide, so its text and logo are at least 5 mm inside the trim (at least 8 mm from the file edge); the border out to the bleed is the artwork's own edge, mirrored from a copy with the text removed. The interior is laid out afresh for A5 (not shrunk); a listing too wide for the page is set in a smaller size of JetBrains Mono so that no line wraps. The page numbers in the interior count from its first page, the title page, and the contents page matches them.

Needs Python with `pypdf`, `img2pdf`, `numpy`, `Pillow` and `markdown`, plus Google Chrome and poppler-utils.
