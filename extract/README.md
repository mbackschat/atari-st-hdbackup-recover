# Atari ST File Extractor

A Python utility to extract files from Atari ST hard disk backup images. This tool processes binary HD backup files and recovers individual files stored within the fragmented byte stream.

## Overview

This extractor reverse-engineers the Atari ST file fragment format used in hard disk backups. It parses fragment headers, handles RLE compression, and reassembles multi-fragment files into individual output files.

## Features

- **Fragment-based extraction**: Processes files stored as one or more fragments
- **RLE decompression**: Automatically decompresses RLE-compressed fragments
- **Multi-fragment file assembly**: Combines fragments to reconstruct complete files
- **Automatic alignment handling**: Manages 2-byte boundary padding
- **Safe output management**: Backs up existing files before extraction

## Installation

Requires Python 3.x (no external dependencies).

```bash
git clone <repository-url>
cd extract
```

## Usage

### Basic Usage

```bash
python atari_extractor.py <input_file> [output_dir]
```

### Arguments

- `input_file` - Binary HD backup file to extract from (required)
- `output_dir` - Output directory for extracted files (optional, default: "extracted")

### Examples

Extract to default "extracted" directory:
```bash
python atari_extractor.py backup.st
```

Extract to custom directory:
```bash
python atari_extractor.py backup.hd my_files
```

## Output Format

Extracted files are numbered sequentially with Atari ST compatible filenames:
- `00001.TXT`
- `00002.TXT`
- `00003.TXT`
- etc.

All files use the `.TXT` extension regardless of actual content type.

If the output directory already exists, existing files are automatically moved to a randomly named backup subfolder before extraction begins.

## Technical Details

### Fragment Structure

Each file fragment in the binary stream consists of:

1. **Header (8 bytes)**
   - Length: 4-byte unsigned long (big-endian)
   - Compression flag: 2-byte word (0 = uncompressed, 1 = RLE compressed)
   - Last fragment flag: 2-byte word (0 = more fragments follow, 1 = last fragment)

2. **Content** (variable length, as specified in header)

3. **Alignment padding** (0 or 1 byte to reach 2-byte boundary)

### RLE Compression

The Run-Length Encoding uses a 3-byte sequence:
- `0xC7` - Marker byte
- Count byte - Number of repetitions
- Value byte - Byte to repeat

**Example**: `0xC7 0x13 0xFE` → outputs `0xFE` repeated 19 times

### Fragment Processing

Files may consist of multiple fragments:
- Fragments are processed sequentially
- Compressed fragments are decompressed before assembly
- Fragments are appended until the last-fragment flag is encountered
- A new file begins with the next fragment after a last-fragment flag

### Example Fragment Sequence

```
Fragment #1: length=35656, compressed=true, last=false
Fragment #2: length=30764, compressed=false, last=false
Fragment #3: length=6844, compressed=true, last=true
  → File 1 (combines fragments #1, #2, #3)

Fragment #4: length=21215, compressed=true, last=true
  → File 2 (single fragment)

Fragment #5: length=17344, compressed=true, last=true
  → File 3 (single fragment)
```

## Project Files

- `atari_extractor.py` - Main extraction utility
- `CLAUDE.md` - Detailed specification and requirements
- `PLAN.md` - Implementation plan and architecture
- `README.md` - This file

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
