# Atari ST Image File Detection

Below is a detection strategy that’s biased toward **very low false positives** for common Atari ST image formats by combining:

1.  **file size gates** (many ST formats are fixed-size)
2.  **strict header parsing with range checks** (big-endian “Motorola” words)
3.  **palette validity checks** (Atari ST/STE hardware palette patterns)
4.  **full (or partial) decompression as a proof step** for compressed formats (accept only if it decodes cleanly to the exact expected size)

I’ll focus on the formats you explicitly mentioned + the ones that show up all the time in ST collections: **DEGAS (PI1/2/3), DEGAS Elite Compressed (PC1/2/3), NEOchrome (NEO), Tiny (TNY/TN1/2/3), Spectrum 512 (SPU), STAD PAC, GEM Raster IMG**.

* * *

Core principle: “prove it” instead of “guess it”
------------------------------------------------

For each candidate format, implement a `try_parse_X()` that returns:

*   `match: bool`
*   `suggested_extension: str`
*   `confidence: 0..100`
*   `reason: str` (optional, for your logs)

A file is accepted only if it passes a **high-confidence proof**:

*   Fixed-size formats: strict header + strict invariants (+ optional extra checks)
*   Compressed formats: strict header + **decompress successfully to the exact expected output length** (typically 32000 bytes for ST full-screen bitplane data)

* * *

Byte order and palette checks (re-used everywhere)
--------------------------------------------------

### Big-endian words

Most ST image headers store 16-bit words in **big-endian**. (GEM IMG explicitly specifies Motorola hi-lo word order.) [Atari Wiki](https://www.atari-wiki.com/?title=IMG_file)

### Palette validity check (minimize false positives)

Atari ST classic palette is 3 bits per channel (0–7). STE extends that, but many file formats still store the hardware-style 12-bit palette word.

A very conservative check that still works well:

*   Accept palette word if `(w & 0xF000) == 0` and `w <= 0x0FFF`
*   Optionally (stricter, classic ST): require each nibble <= 0x7 (i.e. `w & 0x0888 == 0`)  
    Use the stricter version only if you know your corpus is not STE-enhanced.

This palette test is _great_ at reducing “random binary happens to look like a header” false hits.

* * *

High-confidence detectors (with tight rules)
--------------------------------------------

### 1) DEGAS / DEGAS Elite uncompressed: `.PI1 .PI2 .PI3`

starts with 2-byte res_word, values in {0,1,2}

This is widely documented and extremely reliable. [Atari Wiki+2AtariAge Forums+2](https://www.atari-wiki.com/index.php?title=DEGAS_file_format)

**Detection rules (very low FP):**


#### If file size == 32034

→ DEGAS uncompressed (classic)
→ .PI1/.PI2/.PI3

Conditions:
- res_word ∈ {0,1,2}
- palette words plausible (≤ 0x0FFF)

#### If file size == 32066

→ DEGAS Elite uncompressed
→ .PI1/.PI2/.PI3

Conditions:
- res_word ∈ {0,1,2}
- palette plausible
- last 32 bytes exist (by size)

#### If file size < 32066

→ candidate for DEGAS Elite compressed, see below

Conditions:
- (res_word & 0x8000) != 0
- (res_word & 0x0003) ∈ {0,1,2}
- palette plausible
- If decompression yields exactly 32000 bytes → then .PC1/.PC2/.PC3

This cleanly separates all three cases with zero ambiguity.

#### summary (authoritative)

- 32034 bytes → DEGAS uncompressed (classic)
- 32066 bytes → DEGAS Elite uncompressed
- < 32066 bytes + high bit set + decompresses to 32000 → DEGAS Elite compressed


* * *

### 2) NEOchrome: `.NEO`

NEO is also essentially fixed-layout:

*   **total size 32128 bytes**
*   header 128 bytes + 32000 bytes image data [JustSolve+2Atari Magazines+2](https://justsolve.archiveteam.org/wiki/NEOchrome?utm_source=chatgpt.com)

The header contains lots of fields with “always 0” / “always 320/200” defaults (flag, offsets, width/height, reserved), making it highly provable. [FileFormat](https://www.fileformat.info/format/atari/egff.htm)

**Detection rules (very low FP):**

*   `size == 32128`
*   parse header as:
    *   `flag == 0`
    *   `resolution in {0,1,2}`
    *   `xOffset == 0 && yOffset == 0`
    *   `width == 320 && height == 200`
    *   reserved area mostly/entirely 0 (be strict here; it’s a strong discriminator) [FileFormat](https://www.fileformat.info/format/atari/egff.htm)
*   palette passes validity check (16 words)

**Extension:** `.NEO`

* * *

* * *

Compressed formats: accept only if decompression proves it
----------------------------------------------------------

### 3) DEGAS Elite Compressed: `.PC1 .PC2 .PC3`

Documented structure:

*   word0: resolution, but high bit set (e.g. 0x8000, 0x8001, 0x8002)
*   16 words palette
*   compressed data (<32000 bytes)
*   then several animation tables at the end; total file size < 32066 bytes [Atari Wiki+2Atari Wiki+2](https://www.atari-wiki.com/index.php?title=DEGAS_Elite_Compressed_file_format)

Compression is PackBits-like; scanlines compressed separately. [Atari Wiki](https://www.atari-wiki.com/index.php?title=DEGAS_Elite_Compressed_file_format)

**Detection rules (very low FP):**

*   `size < 32066` and `size >= (2+32+32)+1` (must at least hold header + tables + 1 byte data)
*   `res_word & 0x8000 != 0`
*   `(res_word & 0x0003) in {0,1,2}` (and ignore other future bits as per spec) [Atari Wiki](https://www.atari-wiki.com/index.php?title=DEGAS_Elite_Compressed_file_format)
*   palette validity check
*   treat **last 32 bytes** as the 4×4-word animation tables (don’t need to interpret fully; just reserve them)
*   decompress the compressed block and **require exactly 32000 bytes output**
    *   if decompression fails, overflows, or ends early: reject

**Extension mapping:**

*   0 → `.PC1`
*   1 → `.PC2`
*   2 → `.PC3`

* * *

### 4) STAD packed: `.PAC`

STAD `.PAC` has an actual ASCII signature in the first 4 bytes:

*   `pM85` or `pM86` (packing direction)
*   then 3 single-byte parameters (IdByte, PackByte, SpecialByte)
*   then RLE-ish data [FileFormat](https://www.fileformat.info/format/atari/egff.htm)

**Detection rules (very low FP):**

*   first 4 bytes are exactly `b"pM85"` or `b"pM86"` [FileFormat](https://www.fileformat.info/format/atari/egff.htm)
*   `IdByte != SpecialByte` (reasonable sanity)
*   run the decoder and require it produces the expected output length
    *   If you’re targeting full-screen ST images: require 32000 bytes output.
    *   Otherwise, you may need external knowledge; but for “folder full of ST graphics”, 32000 is usually the right proof target.

**Extension:** `.PAC`

* * *

GEM Raster / GEM IMG: `.IMG` (and variants)
-------------------------------------------

GEM IMG has a strong header:

*   8-word minimum header, **version must be 1**
*   header length is a word count
*   planes, width, height, microns, etc. [Atari Wiki+2Accusoft Hilfe+2](https://www.atari-wiki.com/?title=IMG_file)

**Detection rules (to avoid false positives):**

1.  Parse first 8 words big-endian.
2.  Require:
    *   `version == 1` [Atari Wiki](https://www.atari-wiki.com/?title=IMG_file)
    *   `header_len_words >= 8`
    *   `planes in {1..8}` (or a small sane max you choose)
    *   width/height non-zero and within sane bounds (e.g., <= 4096 unless you expect bigger)
3.  Compute `data_offset = header_len_words * 2`, require `data_offset < file_size`
4.  **Proof step:** implement an IMG decoder (token-based compression variants exist) and only accept if decoding completes exactly to the expected bitmap size.

If you don’t want to implement full IMG decoding yet, you can still be conservative:

*   Only classify `.IMG` when the header is perfect _and_ width/height/planes imply a data size that is plausible given remaining bytes.
*   But the real “min false positives” answer is: **decode to prove**.

* * *

Recommended detection order (important!)
----------------------------------------

Run detectors from “most unique signature” to “most ambiguous”:

1.  Containers with magic:
    *   IFF/ILBM: starts with `FORM` (common in Deluxe Paint)
*   STAD: `pM85` / `pM86` [FileFormat](https://www.fileformat.info/format/atari/egff.htm)
*   XIMG/STTT signatures (IMG dialects) if you decide to support them (mentioned in IMG discussions) [Atari Wiki](https://www.atari-wiki.com/?title=IMG_file)
2.  Fixed-size “screen dump” formats:
    *   DEGAS `.PI?` (32034) [Atari Wiki](https://www.atari-wiki.com/index.php?title=DEGAS_file_format)
*   NEO `.NEO` (32128) [JustSolve+1](https://justsolve.archiveteam.org/wiki/NEOchrome?utm_source=chatgpt.com)
3.  Compressed formats with proof-by-decompression:
    *   DEGAS Elite compressed `.PC?` [Atari Wiki](https://www.atari-wiki.com/index.php?title=DEGAS_Elite_Compressed_file_format)
*   GEM IMG `.IMG` (proof-by-decode)

This ordering reduces the chance that a loose heuristic steals a file from a stricter match.

* * *

Practical “min false positives” scoring policy
----------------------------------------------

Use a **hard accept** model:

*   If a format has **magic bytes** and a **proof step** (decode/decompress), accept with confidence 100.
*   If a format has **fixed size + strict invariants**, accept with confidence ~95–100.
*   If a format has only “header looks plausible” but no proof step, keep it as **unknown** (or “weak guess”), because that’s where false positives happen.

