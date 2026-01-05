# Implementation Plan: Atari ST File Type Detector

## Overview
Build a Python-based file type detector for Atari ST files that analyzes content and renames files with correct extensions.

## Architecture

### Main Components

```
filetype-detector.py          # CLI entry point
detectors/
  ├── __init__.py
  ├── binary_executables.py   # PRG/TOS/TTP/ACC (0x601A), Turbo-C (0x4EFA), Devpac (FF65)
  ├── rsc_detector.py          # GEM Resource files
  ├── image_detector.py        # All image formats
  ├── text_detector.py         # Text/source files
utils/
  ├── __init__.py
  ├── binary_utils.py          # Big-endian reading helpers
  ├── decompression.py         # PackBits, STAD decompression
  ├── palette_validation.py    # Atari ST/STE palette checks
```

## Detection Order (Most Reliable First)

### Phase 1: Magic-Number Binaries with Exact Size
1. **RSC files** - Magic at offset with exact size field (`rsh_rssize`)
2. **Turbo-C objects** (0x4EFA) - Exact size = 32 + tlen + dlen + blen
3. **Devpac objects** (FF65) - Parse to end marker

### Phase 2: Magic-Number Executables
4. **GEMDOS executables** (0x601A) - Parse relocation stream to find exact size

### Phase 3: Magic-Based Images
5. **STAD PAC** - Signature `pM85`/`pM86` + decompression proof
6. **GEM IMG** - Version field + decode proof

### Phase 4: Fixed-Size Images
7. **DEGAS uncompressed** (PI1/PI2/PI3) - 32034 bytes + header validation
8. **DEGAS Elite uncompressed** (PI1/PI2/PI3) - 32066 bytes + header validation
9. **NEOchrome** (NEO) - 32128 bytes + strict header validation
10. **DEGAS Elite compressed** (PC1/PC2/PC3) - Size check + full decompression to 32000 bytes

### Phase 5: Text Files (Last Resort)
11. **Text detection** - Weighted scoring system for .C/.H/.S/.RSD/.INF/.PRJ/Makefile/.BAT

## Implementation Steps

### Step 1: Project Setup
- [ ] Create directory structure
- [ ] Set up `__init__.py` files
- [ ] Create main CLI script with argparse

### Step 2: Utility Modules

#### `utils/binary_utils.py`
- [ ] `read_be_word(data, offset)` - Read big-endian 16-bit word
- [ ] `read_be_long(data, offset)` - Read big-endian 32-bit long
- [ ] `is_valid_size(size, max_size)` - Size sanity checks

#### `utils/palette_validation.py`
- [ ] `validate_st_palette(data, offset, count=16)` - Check 12-bit palette validity
- [ ] Support both ST (3-bit/channel) and STE modes

#### `utils/decompression.py`
- [ ] `decompress_packbits(data, expected_size)` - PackBits/RLE decompression
  - Used by DEGAS Elite (scanline-by-scanline variant)
  - Return None on failure, exact bytes on success
- [ ] `decompress_stad(data, id_byte, pack_byte, special_byte)` - STAD PAC decompression
  - Return None on failure, exact bytes on success

### Step 3: Binary Executable Detectors

#### `detectors/rsc_detector.py`
- [ ] `detect_rsc(data, size)` → `(match: bool, ext: str, confidence: int, reason: str)`
- [ ] Parse 36-byte header (big-endian)
- [ ] Validate `rsh_rssize == actual file size`
- [ ] Check all offsets are valid and monotonic
- [ ] Verify table sizes fit within file
- [ ] **Confidence: 100** if all checks pass

#### `detectors/binary_executables.py`

**Turbo-C objects (0x4EFA)**
- [ ] `detect_turboc_object(data, size)` → tuple
- [ ] Check magic 0x4EFA
- [ ] Parse 32-byte header
- [ ] Verify: `size == 32 + tlen + dlen + blen`
- [ ] Extension: `.TCO`
- [ ] **Confidence: 100** if exact match

**Devpac objects (FF65)**
- [ ] `detect_devpac_object(data, size)` → tuple
- [ ] Check signature FF 65
- [ ] Extract NUL-terminated filename (max 64 bytes)
- [ ] Parse record/hunk stream to end marker
- [ ] Derive filename: `<original>-<embedded_stem>.O` (embedded_stem = embedded name without extension)
- [ ] Example: original "00123.TXT" with embedded "modf.o" → "00123-modf.O"
- [ ] **Confidence: 100** if end marker found

**GEMDOS executables and objects (0x601A)**
- [x] `detect_gemdos_executable(data, size)` → tuple
- [x] Check magic 0x601A
- [x] Parse 28-byte header
- [x] **Object vs Executable Detection** (per filetypes/601A.md):
  - [x] **Rule X1** (PRIORITY 1): Valid relocation stream → **EXECUTABLE** (ignore symbol tags)
  - [x] **Rule O4**: Invalid relocation stream (offset > TEXT+DATA) → continue to symbol check
  - [x] **Rule O2**: Detect tagged symbol values (high bit set) → likely .O
  - [x] **Combined O2 + O4**: Tagged symbols + invalid relocation → DEFINITIVE .O
- [x] **CRITICAL FIX**: Changed detection order to prioritize relocation validation
  - **Issue**: Initial implementation checked symbols before relocation
  - **Problem case**: 00505.BIN (final executable with 100% tagged symbols, but valid relocation)
  - **Root cause**: Executables CAN have tagged symbols if built from .O files with debug info
  - **Solution**: Rule X1 (valid relocation) now takes precedence over Rule O2 (tagged symbols)
- [x] Extension mapping:
  - `.O` if object module detected (confidence: 95-98%)
  - `.PRG` if executable detected (confidence: 92%)
- [x] **Successfully tested on testfiles/GEMDOS-O/ (6/6) and testfiles/GEMDOS-PRG/ (6/6) - 100% accuracy**

### Step 4: Image Detectors

#### `detectors/image_detector.py`

**STAD PAC**
- [ ] `detect_stad_pac(data, size)` → tuple
- [ ] Check signature `pM85` or `pM86`
- [ ] Extract compression parameters (IdByte, PackByte, SpecialByte)
- [ ] **Decompress and verify exactly 32000 bytes output**
- [ ] Extension: `.PAC`
- [ ] **Confidence: 100** if decompression succeeds

**DEGAS uncompressed (PI1/2/3)**
- [ ] `detect_degas_pi(data, size)` → tuple
- [ ] Check size == 32034
- [ ] Parse resolution word (must be 0, 1, or 2)
- [ ] Validate 16-word palette
- [ ] Extension mapping: 0→.PI1, 1→.PI2, 2→.PI3
- [ ] **Confidence: 100** with strict checks

**DEGAS Elite uncompressed (PI1/2/3)**
- [ ] `detect_degas_elite_uncompressed(data, size)` → tuple
- [ ] Check size == 32066
- [ ] Parse resolution word (must be 0, 1, or 2, NO high bit set)
- [ ] Validate 16-word palette
- [ ] Verify last 32 bytes exist (animation tables)
- [ ] Extension mapping: 0→.PI1, 1→.PI2, 2→.PI3
- [ ] **Confidence: 100** with strict checks

**NEOchrome (NEO)**
- [ ] `detect_neochrome(data, size)` → tuple
- [ ] Check size == 32128
- [ ] Parse 128-byte header:
  - flag == 0
  - resolution in {0,1,2}
  - xOffset == 0, yOffset == 0
  - width == 320, height == 200
  - reserved area mostly zero
- [ ] Validate palette
- [ ] Extension: `.NEO`
- [ ] **Confidence: 100** with strict invariants

**DEGAS Elite compressed (PC1/2/3)**
- [ ] `detect_degas_elite(data, size)` → tuple
- [ ] Check size < 32066 and > minimum
- [ ] Parse resolution word with high bit set (0x8000, 0x8001, 0x8002)
- [ ] Validate palette
- [ ] Reserve last 32 bytes (animation tables)
- [ ] **Decompress compressed data and verify exactly 32000 bytes output**
- [ ] Extension mapping: 0→.PC1, 1→.PC2, 2→.PC3
- [ ] **Confidence: 100** if decompression proof succeeds

**GEM IMG**
- [ ] `detect_gem_img(data, size)` → tuple
- [ ] Parse 8-word header (big-endian)
- [ ] Require version == 1
- [ ] Validate header_len_words >= 8
- [ ] Check planes in {1..8}, width/height sane
- [ ] **Implement IMG decoder and verify complete decode** (future enhancement)
- [ ] For now: strict header validation only
- [ ] Extension: `.IMG`
- [ ] **Confidence: 90** (header only) or 100 (with decode proof)

### Step 5: Text Detectors

#### `detectors/text_detector.py`

**Core text detection**
- [x] `is_text_file(data)` - Check if file is ASCII/text (allow some binary, CR/CRLF/LF)
- [x] `detect_text_type(data, size)` → tuple

**Scoring system** (as per Textfiles.md)
- [x] Implement weighted evidence scoring
- [ ] **CRITICAL REVISION NEEDED**: `STRONG_MIN = 6` points threshold (lowered from 8)
- [x] `MARGIN = 3` points for disambiguation

**Known Issues - MUST FIX**:
- [ ] **CRITICAL**: .H detection only 4% success rate (1/23 files)
  - Root cause: STRONG_MIN=8 too high, many valid headers score 6-7
  - Root cause: Over-reliance on header guards/prototypes (many ST headers lack them)
  - Root cause: Missing #include-only header pattern
  - See ANALYSIS.md for detailed breakdown
- [ ] .C detection 67% success rate (2/3 files)
  - Missing: Function definition pattern detection
  - Missing: C files without main() function

**Specific detectors:**
- [ ] `.C` - **NEEDS REVISION**:
  - Current: #include, braces, C keywords, function patterns
  - Add: Function definition pattern detection
  - Add: Better scoring for files without main()
  - Add: #include + braces combination bonus
  - [x] **Embedded filename extraction**: Extract original filename from header comments
- [ ] `.H` - **NEEDS MAJOR REVISION**:
  - Current issues: Only detects 4% of test files!
  - Revised approach (see filetypes/Textfiles.md):
    - Graduated #define scoring: 1 define → +1, 2-4 → +3, 5-9 → +4, 10-19 → +5, 20+ → +6
    - #include-only pattern: >=2 includes + <3 defines + no braces → +4 points
    - Lower reliance on header guards/prototypes (many ST headers lack them)
    - Size-agnostic (ST headers range from 50 to 2000+ bytes)
  - [x] **Embedded filename extraction**: Extract original filename from header comments
    - Patterns supported:
      - C-style: `/* FILENAME.H ... */`
      - SCCS/RCS: `@(#)filename.h version date`
      - C++: `// FILENAME.H - description`
    - Used for tie-breaking when H/C classification is ambiguous
    - Filename format: `<original>-<embedded>.<ext>` (e.g., `00014-GEMBIND.H`)
- [ ] `.S` - 68k directives (SECTION, DC.W, XDEF), mnemonics, semicolon comments
- [ ] `.INF` - KEY=VALUE patterns, drive paths (A:\, C:\)
- [ ] `Makefile` - target: rules, TAB-indented recipes, $(CC) macros
- [ ] `.BAT` - echo, REM, batch commands
- [ ] `.PRJ` - multiple source file references (*.c, *.h, *.o)
- [ ] `.RSD` - OBJECT/TREE/DIALOG/MENU/TEDINFO tokens, numeric tables
- [ ] `.TXT` - fallback for unclassified text

**Anti-signal checks** to prevent false positives

### Step 6: Main CLI

#### `filetype-detector.py`
- [x] Argument parsing:
  ```
  python filetype-detector.py [folder] [--dry-run | --no-dry-run]
  ```
- [x] `--dry-run`: Show what would be renamed (default for safety)
- [x] `--no-dry-run`: Actually perform renames
- [x] Iterate through all files in folder
- [x] For each file:
  1. Read entire file content
  2. Run detectors in priority order
  3. Accept first high-confidence match
  4. If no match, keep original extension
  5. Output: `[ACTION] filename.old → filename.new (Type: XXX, Confidence: NN)`
- [x] Minimal output: only show renamed/skipped files
- [x] Handle errors gracefully (unreadable files, permission issues)
- [x] **Enhanced Statistics Reporting:**
  - Track all detected file types
  - Display summary with:
    - Total files processed
    - Files renamed/to be renamed
    - Files skipped
    - **Breakdown by extension** (sorted alphabetically with counts)
  - Example: `.C: 4 files, .H: 3 files, .PI1: 2 files`

### Step 7: Testing

#### Test strategy
- [x] Use testfiles/ folder with subfolder-based organization
- [x] Folder structure: Each subfolder name indicates the expected file type
  ```
  testfiles/
    ├── H/          # All files should detect as .H
    ├── C/          # All files should detect as .C
    ├── S/          # All files should detect as .S
    ├── GEMDOS-PRG/   # All Files that should be detected as .PRG (programs) or .ACC
    ├── GEMDOS-O/   # All Files that should be detected as .O (GEMDOS object files)
    ├── RSC/        # All files should detect as .RSC
    └── ...
  ```
- [ ] Create test runner:
  ```python
  python test_detector.py
  ```
- [ ] For each test file:
  - Determine expected extension from parent folder name
  - Run detector
  - Compare detected extension with expected
  - Report successes/failures
- [x] Test coverage - **GEMDOS Binaries (0x601A)**:
  - [x] **testfiles/GEMDOS-PRG/** → all 6 files correctly detect as .PRG (100%)
  - [x] **testfiles/GEMDOS-O/** → all 6 files correctly detect as .O (100%)
- [ ] Test coverage - **Text Files**:
  - Files in testfiles/C/ → should all detect .C
  - Files in testfiles/H/ → should all detect .H
  - Files in testfiles/S/ → should all detect .S
- [ ] Test coverage - **Other Binaries**:
  - Files in testfiles/RSC/ → should detect .RSC

#### Edge case testing
- [ ] Empty files
- [ ] Very small files (< 100 bytes)
- [ ] Binary files with text-like content
- [ ] Truncated files
- [ ] Files with mixed encodings

### Step 8: Documentation
- [ ] Update README with usage examples
- [ ] Document confidence levels and detection criteria
- [ ] Add troubleshooting section

## Success Criteria

1. ✅ All test files correctly detected
2. ✅ Zero false positives (prefer "unknown" over wrong type)
3. ✅ Dry-run mode works perfectly
4. ✅ Handles binary and text files robustly
5. ✅ Compressed images fully decompressed and validated
6. ✅ Clear, minimal output showing only necessary info
7. ✅ **Enhanced statistics with extension breakdown** (sorted, with counts)

## Immediate Action Items (Based on ANALYSIS.md)

### Priority 1: Fix .H Detection (CRITICAL - 4% success rate!)

1. **Lower threshold**: Change `STRONG_MIN` from 8 to 6
2. **Boost #define scoring**:
   - 20+ #defines → +6 points
   - 10-19 #defines → +5 points
   - 5-9 #defines → +4 points
   - 2-4 #defines → +3 points
   - 1 #define → +1 point
3. **Add #include-only pattern**: >=2 includes + <3 defines + no braces → +4 points
4. **Test expected improvement**: 4% → ~85-90% success rate

### Priority 2: Improve .C Detection (67% success rate)

1. **Add function definition pattern detection**: `\w+\s+\w+\s*\([^)]*\)\s*\{` → +3 points
2. **Add #include + braces combo**: Both present → +2 bonus points
3. **Reduce reliance on main()**: Better scoring for library/module files
4. **Test expected improvement**: 67% → ~90-95% success rate

### Priority 3: Validation

- Run full test suite on testfiles/H (23 files)
- Run full test suite on testfiles/C (3 files)
- Verify no regressions in .S, Makefile, or other detectors
- Document final success rates

---

## Future Enhancements (Optional)

- [ ] GEM IMG full decoder implementation
- [ ] Support for more image formats (Spectrum 512, Tiny)
- [ ] Parallel processing for large folders
- [x] Statistics summary at end (COMPLETED - shows extension breakdown)
- [ ] Export detection report to JSON/CSV
