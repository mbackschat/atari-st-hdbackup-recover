# Atari ST HD Backup Restoration

This is a toolset to extract files from Atari ST backup images written
with an old version of the program "Harddisk Utility" from Application Systems Heidelberg (ASH).

## Motivation

The HD backup image is a binary stream that was originally written
on disks using the program "Harddisk Utility" from Application System Heidelberg in 1988/89.

My problem was that I have lost the last disk of this backup, which unfortunately
has important information about the filenames and folder structure (the "catalogue", basically a FAT).

Another problem is that the backup was made with an old version of Harddisk Utility,
which I cannot find anymore. I have tried V2.0 and V2.2b (available on the Internet), but
they use a different format.

Therefore, I decided to restore the files on my own.
I figured out the backup structure by doing a little bit of reverse engineering, using
the great hex editor "Hex Fiend" and spent a lot of LLM tokens during analysis and recovering experiments.

The result is a chain of simple tools using Claude Code.
I think it is easier to use a divide & conquer approach with the modern LLMs, and keeping
each tool focused and the code rather small.


## Overview

This project provides a four-step toolchain to recover files from Atari ST hard disk backups stored on floppy disk images.
The toolchain processes disk images created with the Greaseweazle tool and extracts individual files with proper type detection and format conversion.

### The Recovery Toolchain

The restoration process consists of four stages, automated through `toolchain.sh`:

#### Stage 1: Binary File Carving
**Tool:** `carver/carver.py`

Splits the original disk image files (.st) at known offset boundaries to isolate the backup data from disk formatting overhead. The tool removes boot sectors and disk metadata by cutting at precise byte offsets (10240 and 819200), then concatenates the carved segments into a continuous binary stream.

#### Stage 2: File Fragment Extraction
**Tool:** `extract/atari_extractor.py`

Parses the binary stream and reconstructs individual files from fragmented backup data. The Harddisk Utility stored files as fragments with 8-byte headers containing length, compression flags, and continuation markers. This tool:
- Reads fragment headers (big-endian format for Motorola 68000)
- Decompresses RLE-encoded fragments
- Assembles multi-fragment files into complete files
- Handles 2-byte alignment padding
- Outputs sequentially numbered files (00001.TXT, 00002.TXT, etc.)

#### Stage 3: File Type Detection
**Tool:** `filetypes-detector/filetype-detector.py`

Analyzes the extracted files to determine their actual type and assigns proper Atari ST-compatible 3-letter extensions. The detector recognizes:

**Binary formats:**
- GEMDOS executables (PRG/TOS/TTP/ACC/APP) with 0x601A magic
- Object files (GEMDOS .O, Turbo-C .TCO, Devpac .O)
- GEM Resource files (.RSC)
- Image formats: DEGAS (PI1/PI2/PI3), DEGAS Elite compressed (PC1/PC2/PC3), NEOchrome (.NEO), STAD packed (.PAC), GEM Raster (.IMG)

**Text formats:**
- C source and headers (.C, .H) with embedded filename extraction
- Assembly source (.S) for Motorola 68000
- GEM Resource Definition files (.RSD)
- Configuration files (.INF)
- Build scripts (Makefiles, .BAT)
- Project files (.PRJ)
- Generic text (.TXT as fallback)

Detection uses magic bytes, file size validation, header parsing, content analysis, and keyword scoring to minimize false positives.

#### Stage 4: Image Format Conversion
**Tool:** `degas_to_png/degas_to_png.py`

Converts vintage Atari ST image files to modern PNG format for easy viewing. Processes DEGAS images in all three resolutions:
- PI1: Low resolution (320x200, 16 colors)
- PI2: Medium resolution (640x200, 4 colors)
- PI3: High resolution (640x400, 2 colors)

Handles both classic DEGAS format (32,034 bytes) and DEGAS Elite uncompressed format (32,066 bytes), converting the ST's bitplane format and hardware palette into standard RGB PNG images.

## Setup

### Prerequisites
- Python 3.x (Python 3.6 or later recommended)
- pip (Python package installer)

### Installation

Most tools in this project use only Python's standard library and work out of the box. However, the image conversion tool requires the Pillow library.

**Install all dependencies:**

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install Pillow
```

**Note:** If you're only using the carver, extractor, or file type detector, no additional installation is required.

### Dependency Overview

| Tool | External Dependencies |
|------|---------------------|
| `carver/carver.py` | None |
| `extract/atari_extractor.py` | None |
| `filetypes-detector/filetype-detector.py` | None |
| `degas_to_png/degas_to_png.py` | Pillow |

## Usage

### Running the Toolchain

```bash
./toolchain.sh [DATAFOLDER] [EXTRACTED]
```

**Parameters:**
- `DATAFOLDER` (optional): Directory containing .st disk images (default: `example/disks`)
- `EXTRACTED` (optional): Output directory for recovered files (default: `extracted` folder next to DATAFOLDER)

**Example:**
```bash
./toolchain.sh example/disks
```

The provided `example` folder contains:
- folder `disks` with the first 3 .st files of my backup (the rest are left out, but it's enough to test the tools…)
- `extracted.zip` contains the files that were produced in my test run
- `log.txt` has the output of the test run


### Input Files

Before running the toolchain:
1. Place your .st disk image files in the DATAFOLDER
2. The images should be disk images created with tools like Greaseweazle
3. Files must have ".st" extension and they should be sorted by filename, example: "E1.st", "E2.st" etc, or similar

### Output

After successful execution:
- Extracted files will be in the EXTRACTED folder
- Files will have proper extensions based on detected type
- DEGAS images will have corresponding PNG versions for viewing
- Original numbered files (e.g., 00014.TXT) may be renamed with detected types (e.g., 00014-GEMBIND.H)


## License

MIT License

Copyright (c) 2026 Martin Backschat

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
