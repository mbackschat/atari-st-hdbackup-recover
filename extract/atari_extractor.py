#!/usr/bin/env python3
"""
Atari ST File Extractor
Extracts files from binary HD backup containing fragmented Atari ST files.
"""

import argparse
import os
import struct
import sys
from datetime import datetime
import shutil


def prepare_output_dir(output_dir):
    """
    Prepare output directory. If it exists, move contents to backup subfolder.

    Args:
        output_dir: Path to output directory
    """
    if os.path.exists(output_dir):
        # Create backup subfolder with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(output_dir, f"backup_{timestamp}")

        # Get all files/folders in output_dir (except the backup we're about to create)
        existing_items = [item for item in os.listdir(output_dir)
                         if not item.startswith('backup_')]

        if existing_items:
            os.makedirs(backup_dir, exist_ok=True)
            print(f"Moving existing files to: {backup_dir}")

            for item in existing_items:
                src = os.path.join(output_dir, item)
                dst = os.path.join(backup_dir, item)
                shutil.move(src, dst)
    else:
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")


def read_fragment_header(file):
    """
    Read and parse fragment header (8 bytes, big-endian).

    Header structure:
    - Length: 4-byte unsigned long
    - Compression flag: 2-byte word (0=no, 1=yes)
    - Last fragment flag: 2-byte word (0=no, 1=yes)

    Args:
        file: Binary file object

    Returns:
        dict with 'length', 'compressed', 'last_fragment' or None if EOF
    """
    header_bytes = file.read(8)

    if len(header_bytes) < 8:
        return None  # EOF or incomplete header

    # Parse big-endian values
    length = struct.unpack('>I', header_bytes[0:4])[0]
    compressed = struct.unpack('>H', header_bytes[4:6])[0]
    last_fragment = struct.unpack('>H', header_bytes[6:8])[0]

    return {
        'length': length,
        'compressed': bool(compressed),
        'last_fragment': bool(last_fragment)
    }


def decompress_rle(data):
    """
    Decompress RLE (Run-Length Encoding) compressed data.

    RLE format:
    - 0xC7 is ALWAYS a marker
    - Followed by: count (1 byte) + value (1 byte)
    - Output: 'value' repeated 'count' times
    - To encode literal 0xC7: use 0xC7 0x01 0xC7

    Args:
        data: Compressed bytes

    Returns:
        Decompressed bytes
    """
    result = bytearray()
    i = 0

    while i < len(data):
        if data[i] == 0xC7:
            if i + 2 < len(data):
                count = data[i + 1]
                value = data[i + 2]
                result.extend([value] * count)
                i += 3
            else:
                # Incomplete RLE sequence at end
                raise ValueError(f"Incomplete RLE sequence at position {i}")
        else:
            result.append(data[i])
            i += 1

    return bytes(result)


def write_file(output_dir, counter, data):
    """
    Write extracted file with Atari ST compatible filename.

    Args:
        output_dir: Output directory path
        counter: File counter (1-based)
        data: File content bytes

    Returns:
        Filename written
    """
    filename = f"{counter:05d}.TXT"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'wb') as f:
        f.write(data)

    return filename


def extract_files(input_file, output_dir):
    """
    Extract all files from binary stream.

    Args:
        input_file: Path to input binary file
        output_dir: Path to output directory
    """
    file_counter = 1
    current_file_data = bytearray()
    fragment_counter = 0

    print(f"Extracting from: {input_file}")
    print(f"Output directory: {output_dir}")
    print("-" * 60)

    with open(input_file, 'rb') as f:
        while True:
            # Read fragment header
            header = read_fragment_header(f)

            if header is None:
                # End of file
                if len(current_file_data) > 0:
                    print(f"Warning: Incomplete file at end (no last-fragment flag)")
                break

            fragment_counter += 1

            # Read fragment content
            content = f.read(header['length'])

            if len(content) < header['length']:
                print(f"Warning: Fragment {fragment_counter} truncated "
                      f"(expected {header['length']}, got {len(content)} bytes)")

            # Decompress if needed
            original_size = len(content)
            if header['compressed']:
                try:
                    content = decompress_rle(content)
                except ValueError as e:
                    print(f"Error decompressing fragment {fragment_counter}: {e}")
                    # Skip this fragment
                    continue

            # Append to current file buffer
            current_file_data.extend(content)

            # Handle 2-byte alignment padding
            if header['length'] % 2 == 1:
                padding = f.read(1)  # Skip padding byte

            # Write file if this is the last fragment
            if header['last_fragment']:
                filename = write_file(output_dir, file_counter, current_file_data)

                comp_info = " (compressed)" if header['compressed'] else ""
                print(f"File {file_counter:5d}: {filename} - {len(current_file_data):,} bytes{comp_info}")

                file_counter += 1
                current_file_data = bytearray()

    print("-" * 60)
    print(f"Extraction complete: {file_counter - 1} files extracted")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Extract files from Atari ST binary backup',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python atari_extractor.py test.st
  python atari_extractor.py backup.hd extracted
        '''
    )

    parser.add_argument('input_file',
                       help='Binary file to extract from')
    parser.add_argument('output_dir',
                       nargs='?',
                       default='extracted',
                       help='Output directory (default: extracted)')

    args = parser.parse_args()

    # Validate input file
    if not os.path.exists(args.input_file):
        print(f"Error: Input file not found: {args.input_file}", file=sys.stderr)
        sys.exit(1)

    # Prepare output directory
    prepare_output_dir(args.output_dir)

    # Extract files
    try:
        extract_files(args.input_file, args.output_dir)
    except Exception as e:
        print(f"Error during extraction: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
