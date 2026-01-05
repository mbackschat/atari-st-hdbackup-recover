# Atari ST Degas Image Converter

A Python utility for converting classic Atari ST Degas image files to modern PNG format.

## Overview

This tool converts Atari ST Degas image files (PI1, PI2, PI3 formats) to PNG images, preserving the original retro graphics from the 16-bit computing era. The converter processes entire folders of Degas images, making it easy to batch-convert your vintage Atari ST graphics collections.

## Supported Formats

The converter supports all three Degas image format variants:

- **PI1** - Low resolution (320×200, 16 colors)
- **PI2** - Medium resolution (640×200, 4 colors)
- **PI3** - High resolution (640×400, 2 colors)

Both classic Degas (32,034 bytes) and Degas Elite uncompressed (32,066 bytes) formats are supported.

## Usage

```bash
python degas_converter.py <folder_path>
```

The script will:
1. Scan the specified folder for Degas image files (.PI1, .PI2, .PI3)
2. Convert each image to PNG format
3. Save the PNG files in the same folder with the same filename (but .PNG extension)

### Example

```bash
python degas_converter.py ./my_atari_graphics
```

This will convert all Degas images in `./my_atari_graphics/` to PNG format in the same directory.

## Requirements

- Python 3.x
- PIL/Pillow library for PNG generation

## Background

The Atari ST was a popular 16-bit home computer from the mid-1980s. Degas was one of the most widely-used graphics programs on the platform, and its file format became a de facto standard for ST graphics. These files contain:

- A 2-byte resolution indicator (0=low, 1=medium, 2=high)
- A 16-color palette (stored as ST hardware palette words)
- Raw bitplane image data (32,000 bytes)

This converter faithfully reconstructs the original images by parsing the Degas file structure and converting the ST's unique bitplane format and hardware palette into standard PNG images viewable on modern systems.

## Technical Details

The Degas format stores images in the Atari ST's native bitplane format, where each color plane is stored separately in memory. The palette uses the ST's 12-bit color values (3 bits per RGB channel, or 4 bits for STE-enhanced systems). The converter handles:

- Big-endian (Motorola) byte order used by the 68000 processor
- Bitplane-to-chunky pixel conversion
- ST hardware palette to RGB color mapping
- Multiple resolution modes with different color depths

## License

This project is provided as-is for preserving and accessing vintage Atari ST graphics.
