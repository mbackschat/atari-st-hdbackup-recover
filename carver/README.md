# Binary File Carver

A simple command-line tool for splitting binary files at specified offsets.

## Overview

Binary File Carver takes a binary file and splits it into multiple pieces at user-defined offset points. This is useful for extracting segments from disk images, firmware files, or any binary data where you need to separate content at known boundaries.

## Features

- Split binary files at one or more offset positions
- Support for both decimal and hexadecimal offset notation
- Automatic sequential file naming
- Simple command-line interface

## Usage

```bash
python carver.py <binary_file> <offset1> [offset2] [offset3] ...
```

### Parameters

- `binary_file` - Path to the binary file you want to split
- `offset` - One or more offset positions where the file should be split
  - Decimal format: `96304`
  - Hexadecimal format: `$17830` or `0x17830`

### Output Files

The tool creates sequentially numbered output files:
- Original filename with `-1` appended for the first piece
- Original filename with `-2` appended for the second piece
- Original filename with `-N` appended for the Nth piece

**Number of output files:** With N offsets provided, the tool creates N+1 files.

## Examples

### Single Cut Point

Split a file at offset 96304:

```bash
python carver.py example/test.bin 96304
```

Output:
- `data-1.bin` - Contains bytes from start to offset 96304
- `data-2.bin` - Contains bytes from offset 96304 to end

### Multiple Cut Points

Split a file at offsets 5 and 96304:

```bash
python carver.py example/test.bin 5 96304
```

Output:
- `data-1.bin` - Contains bytes 0-4 (5 bytes)
- `data-2.bin` - Contains bytes 5-96303
- `data-3.bin` - Contains bytes 96304 to end

### Using Hexadecimal Offsets

```bash
python carver.py firmware.bin $1000 0x5000
```

This splits the file at hexadecimal offsets 0x1000 and 0x5000.

## Use Cases

- Extracting boot sectors from disk images
- Separating concatenated firmware components
- Recovering specific segments from binary dumps
- Splitting Atari ST disk images or hard disk backups
- General binary file analysis and forensics

## License

This tool is provided as-is for binary file manipulation tasks.
