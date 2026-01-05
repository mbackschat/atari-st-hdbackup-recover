# Atari ST File Type Detector

Automatically detect and classify Atari ST files by analyzing their content and structure. This tool is designed for reverse engineering and recovering files from Atari ST hard disk backups where the original file extensions are unknown or lost.

## Project Goal

Analyze a folder of unknown files and detect valid file types that were common on the Atari ST platform, especially those related to software development. The tool examines file content and/or size to determine the file type, then renames files with appropriate 3-letter Atari ST-compatible extensions.

## Supported File Types

### Binary Formats

**Executables & Objects:**
- **PRG/TOS/TTP/ACC/APP** - GEMDOS executable files (0x601A magic)
- **O** - GEMDOS object files (linkable modules)
- **TCO** - Turbo-C/Pure-C object files (0x4EFA magic)
- **O** - Devpac assembler object files (FF65 magic, with embedded filename extraction)

**Resources:**
- **RSC** - GEM Resource Files (exact size validation)

**Image Formats:**
- **PI1/PI2/PI3** - DEGAS uncompressed images (fixed 32034 bytes)
- **PC1/PC2/PC3** - DEGAS Elite compressed images (with full decompression validation)
- **NEO** - NEOchrome images (fixed 32128 bytes)
- **PAC** - STAD compressed images (pM85/pM86 signature)
- **IMG** - GEM Raster images

### Text Formats

Detected using intelligent keyword analysis and weighted scoring:

- **C** - C source files
- **H** - C header files (with embedded filename extraction)
- **S** - Motorola 68000 assembly source
- **RSD** - GEM Resource Definition files (text-based resource descriptions)
- **INF** - Configuration files
- **Makefiles** - Build scripts
- **BAT** - Batch files
- **PRJ** - Project files
- **TXT** - Generic text (fallback for unidentifiable text files)

## Usage

### Command Line Interface

```bash
python filetype-detector.py [folder] [--dry-run | --no-dry-run]
```

**Arguments:**
- `folder` - Directory containing files to analyze (required)
- `--dry-run` - Show what would be renamed without actually renaming (default, safe mode)
- `--no-dry-run` - Actually rename files (use with caution)

### Examples

```bash
# Preview what would happen (safe, default mode)
python filetype-detector.py extracted

# Same as above (explicit dry-run)
python filetype-detector.py extracted --dry-run

# Actually rename files (CAUTION!)
python filetype-detector.py extracted --no-dry-run
```

## Detection Strategy

The tool uses a priority-based detection approach, checking for the most reliable signatures first:

1. **Magic-based formats with exact size** - RSC, Turbo-C objects (highest confidence)
2. **Fixed-size image formats** - DEGAS, NEOchrome (file size + header validation)
3. **Magic-based executables** - GEMDOS PRG/TOS/TTP (0x601A magic + structure)
4. **Compressed formats with proof** - DEGAS Elite, STAD (full decompression validation)
5. **Text-based formats** - C, H, S, etc. (weighted keyword scoring)

**Key principle:** If uncertain, the file is skipped or classified as generic text to minimize false positives.

## Output and Reporting

The tool provides detailed output showing:

- Each file being processed with action indicator:
  - **RENAME** - File will be/was renamed
  - **SKIP** - File type undetectable or already correct
  - **OK** - File already has correct extension
- Detected file type and confidence level
- Summary statistics at the end

**Example output:**

```
============================================================
Summary:
  Total files processed: 15
  Files to be renamed: 12
  Files skipped: 3

  Files by detected extension:
    .C      :   4 files
    .H      :   3 files
    .PI1    :   2 files
    .PRG    :   2 files
    .S      :   1 file
============================================================
```

## Testing

The `testfiles/` folder contains test files organized by expected extension. Each subfolder is named after the extension that files inside should be detected as:

```
testfiles/
  ├── H/          # Files that should be detected as .H (header files)
  ├── C/          # Files that should be detected as .C (C source)
  ├── S/          # Files that should be detected as .S (assembly)
  ├── GEMDOS-PRG/ # Files that should be detected as .PRG (programs) or .ACC
  ├── GEMDOS-O/   # Files that should be detected as .O (GEMDOS object files)
  ├── RSC/        # Files that should be detected as .RSC
  ├── PI1/        # Files that should be detected as .PI1
  └── ...         # Other extensions
```

Run tests on a copy of the folder to verify detection accuracy!

## Special Features

### Embedded Filename Extraction

For certain file types, the tool can extract the original filename embedded in the file content:

- **Devpac .O files** - Module name embedded after FF65 magic
- **C Header files** - Filename often present in comment headers

When detected, the output filename preserves both the original and embedded names:
```
00014.TXT → 00014-GEMBIND.H
```

### Validation Methods

**Binary files:**
- Magic number verification
- Exact file size calculation and validation
- Header structure integrity checks

**Compressed images:**
- Full decompression to expected size (32000 bytes for full-screen ST images)
- Zero tolerance for malformed data

**Text files:**
- Weighted evidence scoring system
- Minimum confidence thresholds
- Anti-patterns to prevent false positives

## Notes

- **Safe by default** - Dry-run mode prevents accidental file modifications
- **Conservative classification** - Files are only renamed when confident in the detection
- **Big-endian support** - All binary formats use Motorola 68000 byte order
- **No dependencies** - Uses Python standard library only
- **Atari ST compatible** - All extensions use 3-letter format

## Requirements

- Python 3.6 or higher
- No external dependencies
