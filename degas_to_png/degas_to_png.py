#!/usr/bin/env python3
"""
Atari ST Degas PI1/PI2/PI3 to PNG Converter

Converts Degas format images (PI1/PI2/PI3) to PNG format.
Supports both classic DEGAS (32034 bytes) and DEGAS Elite (32066 bytes) uncompressed formats.
"""

import struct
import sys
from pathlib import Path
from PIL import Image


class DegasImage:
    """Parser and converter for Atari ST Degas image format."""

    # Resolution modes
    RESOLUTIONS = {
        0: {'width': 320, 'height': 200, 'planes': 4, 'colors': 16},  # Low res
        1: {'width': 640, 'height': 200, 'planes': 2, 'colors': 4},   # Medium res
        2: {'width': 640, 'height': 400, 'planes': 1, 'colors': 2},   # High res (mono)
    }

    def __init__(self, filepath):
        """Load and parse a Degas image file."""
        self.filepath = Path(filepath)
        with open(filepath, 'rb') as f:
            self.data = f.read()

        self.validate_format()
        self.parse_header()
        self.parse_palette()
        self.parse_image_data()

    def validate_format(self):
        """Validate that this is a Degas format file."""
        size = len(self.data)
        if size == 32034:
            self.format = "DEGAS Classic"
        elif size == 32066:
            self.format = "DEGAS Elite"
        else:
            raise ValueError(f"Invalid file size {size}. Expected 32034 or 32066 bytes.")

    def parse_header(self):
        """Parse the 2-byte resolution header (big-endian)."""
        res_word = struct.unpack('>H', self.data[0:2])[0]

        # For DEGAS Elite compressed, high bit is set, but we only handle uncompressed here
        if res_word & 0x8000:
            raise ValueError("This appears to be a compressed DEGAS Elite file, which is not supported.")

        self.resolution = res_word & 0x0003
        if self.resolution not in self.RESOLUTIONS:
            raise ValueError(f"Invalid resolution mode: {self.resolution}")

        self.res_info = self.RESOLUTIONS[self.resolution]
        self.width = self.res_info['width']
        self.height = self.res_info['height']
        self.planes = self.res_info['planes']
        self.num_colors = self.res_info['colors']

    def parse_palette(self):
        """Parse the 16-word (32-byte) palette in Atari ST format."""
        self.palette = []

        for i in range(16):
            offset = 2 + (i * 2)
            pal_word = struct.unpack('>H', self.data[offset:offset+2])[0]

            # Atari ST palette format: 0x0RGB (3 bits per channel, 0-7)
            # Extract RGB components
            r = (pal_word >> 8) & 0x07
            g = (pal_word >> 4) & 0x07
            b = pal_word & 0x07

            # Scale from 0-7 to 0-255
            r = (r * 255) // 7
            g = (g * 255) // 7
            b = (b * 255) // 7

            self.palette.append((r, g, b))

    def parse_image_data(self):
        """Parse the bitplane image data (32000 bytes starting at offset 34)."""
        self.image_data = self.data[34:34+32000]

    def decode_bitplanes(self):
        """Convert bitplane format to indexed pixel data."""
        pixels = []

        if self.resolution == 0:  # Low res: 320x200, 4 bitplanes
            # Bitplanes are interleaved by words within each scanline
            # Format: word0_plane0, word0_plane1, word0_plane2, word0_plane3, word1_plane0, ...
            words_per_line = self.width // 16  # 20 words per scanline

            for y in range(self.height):
                line_offset = y * words_per_line * 4 * 2  # 20 words × 4 planes × 2 bytes
                scanline = []

                for x in range(words_per_line):
                    # Each group of 4 words contains 16 pixels (one word per plane)
                    word_offset = line_offset + (x * 4 * 2)  # 4 words × 2 bytes

                    plane0 = struct.unpack('>H', self.image_data[word_offset:word_offset+2])[0]
                    plane1 = struct.unpack('>H', self.image_data[word_offset+2:word_offset+4])[0]
                    plane2 = struct.unpack('>H', self.image_data[word_offset+4:word_offset+6])[0]
                    plane3 = struct.unpack('>H', self.image_data[word_offset+6:word_offset+8])[0]

                    # Extract 16 pixels from MSB to LSB
                    for bit in range(15, -1, -1):
                        pixel_value = ((plane0 >> bit) & 1) | \
                                    (((plane1 >> bit) & 1) << 1) | \
                                    (((plane2 >> bit) & 1) << 2) | \
                                    (((plane3 >> bit) & 1) << 3)
                        scanline.append(pixel_value)

                pixels.extend(scanline)

        elif self.resolution == 1:  # Medium res: 640x200, 2 bitplanes
            # Bitplanes are interleaved by words within each scanline
            # Format: word0_plane0, word0_plane1, word1_plane0, word1_plane1, ...
            words_per_line = self.width // 16  # 40 words per scanline

            for y in range(self.height):
                line_offset = y * words_per_line * 2 * 2  # 40 words × 2 planes × 2 bytes
                scanline = []

                for x in range(words_per_line):
                    # Each group of 2 words contains 16 pixels (one word per plane)
                    word_offset = line_offset + (x * 2 * 2)  # 2 words × 2 bytes

                    plane0 = struct.unpack('>H', self.image_data[word_offset:word_offset+2])[0]
                    plane1 = struct.unpack('>H', self.image_data[word_offset+2:word_offset+4])[0]

                    # Extract 16 pixels from MSB to LSB
                    for bit in range(15, -1, -1):
                        pixel_value = ((plane0 >> bit) & 1) | \
                                    (((plane1 >> bit) & 1) << 1)
                        scanline.append(pixel_value)

                pixels.extend(scanline)

        elif self.resolution == 2:  # High res: 640x400, 1 bitplane (monochrome)
            # Each scanline: 80 bytes = 640 pixels
            bytes_per_line = 80

            for y in range(self.height):
                line_offset = y * bytes_per_line
                scanline = []

                for x in range(self.width // 16):  # Process 16 pixels at a time
                    word_offset = line_offset + (x * 2)
                    plane0 = struct.unpack('>H', self.image_data[word_offset:word_offset+2])[0]

                    for bit in range(15, -1, -1):
                        pixel_value = (plane0 >> bit) & 1
                        scanline.append(pixel_value)

                pixels.extend(scanline)

        return pixels

    def to_png(self, output_path):
        """Convert the Degas image to PNG and save it."""
        # Decode bitplanes to indexed pixels
        pixels = self.decode_bitplanes()

        # Create PIL Image
        if self.num_colors == 2:  # Monochrome
            # For monochrome, create RGB image directly
            img = Image.new('RGB', (self.width, self.height))
            rgb_pixels = [self.palette[p] for p in pixels]
            img.putdata(rgb_pixels)
        else:
            # Create palette mode image
            img = Image.new('P', (self.width, self.height))

            # Set palette (PIL expects flat list of RGB values)
            flat_palette = []
            for r, g, b in self.palette:
                flat_palette.extend([r, g, b])
            # Pad palette to 256 colors
            while len(flat_palette) < 768:
                flat_palette.append(0)

            img.putpalette(flat_palette)
            img.putdata(pixels)

        # Save as PNG
        img.save(output_path, 'PNG')
        print(f"Converted: {self.filepath.name} -> {output_path.name}")


def convert_folder(folder_path):
    """Convert all Degas files in a folder to PNG."""
    folder = Path(folder_path)

    if not folder.exists():
        print(f"Error: Folder '{folder_path}' does not exist.")
        sys.exit(1)

    if not folder.is_dir():
        print(f"Error: '{folder_path}' is not a directory.")
        sys.exit(1)

    # Find all PI1, PI2, PI3 files (case-insensitive)
    patterns = ['*.PI1', '*.PI2', '*.PI3', '*.pi1', '*.pi2', '*.pi3']
    files = []
    for pattern in patterns:
        files.extend(folder.glob(pattern))

    if not files:
        print(f"No Degas image files (PI1/PI2/PI3) found in '{folder_path}'")
        sys.exit(0)

    print(f"Found {len(files)} Degas image file(s)")

    success_count = 0
    error_count = 0

    for file_path in sorted(files):
        try:
            # Create output filename with .PNG extension
            output_path = file_path.with_suffix('.PNG')

            # Load and convert
            degas = DegasImage(file_path)
            degas.to_png(output_path)
            success_count += 1

        except Exception as e:
            print(f"Error converting {file_path.name}: {e}")
            error_count += 1

    print(f"\nConversion complete: {success_count} successful, {error_count} errors")


def main():
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python degas_to_png.py <folder_path>")
        print("\nConverts all Atari ST Degas PI1/PI2/PI3 images in the specified folder to PNG format.")
        sys.exit(1)

    folder_path = sys.argv[1]
    convert_folder(folder_path)


if __name__ == '__main__':
    main()
