#!/usr/bin/env python3
"""
Binary File Carver - Splits a binary file into multiple pieces at specified offsets.
"""

import sys
import os


def parse_offset(offset_str):
    """
    Parse offset string supporting decimal, hex with $ prefix, or hex with 0x prefix.

    Args:
        offset_str: String representation of offset

    Returns:
        Integer offset value
    """
    offset_str = offset_str.strip()

    if offset_str.startswith('$'):
        # Hex with $ prefix
        return int(offset_str[1:], 16)
    elif offset_str.startswith('0x') or offset_str.startswith('0X'):
        # Hex with 0x prefix
        return int(offset_str, 16)
    else:
        # Decimal
        return int(offset_str)


def split_binary_file(input_file, offsets):
    """
    Split a binary file into multiple pieces at the specified offsets.

    Args:
        input_file: Path to the input binary file
        offsets: List of byte offsets where to split the file
    """
    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found.")
        sys.exit(1)

    # Get file size
    file_size = os.path.getsize(input_file)

    # Sort offsets
    offsets = sorted(set(offsets))

    # Validate offsets
    for offset in offsets:
        if offset < 0 or offset > file_size:
            print(f"Error: Offset {offset} is out of range (file size: {file_size} bytes).")
            sys.exit(1)

    # Read the entire file
    with open(input_file, 'rb') as f:
        data = f.read()

    # Generate output filenames and parts
    base_name, ext = os.path.splitext(input_file)

    # Create list of split points: [0, offset1, offset2, ..., file_size]
    split_points = [0] + offsets + [file_size]

    # Split and write each part
    print(f"File split successfully into {len(split_points) - 1} parts:")
    total_bytes = 0

    for i in range(len(split_points) - 1):
        start = split_points[i]
        end = split_points[i + 1]
        part_data = data[start:end]

        output_file = f"{base_name}-{i + 1}{ext}"

        with open(output_file, 'wb') as f:
            f.write(part_data)

        print(f"  Part {i + 1}: {output_file} ({len(part_data)} bytes)")
        total_bytes += len(part_data)

    print(f"  Total: {total_bytes} bytes")


def main():
    if len(sys.argv) < 3:
        print("Usage: carver.py <binary_file> <offset1> [offset2] [offset3] ...")
        print("  offsets can be decimal, hex with $ prefix, or hex with 0x prefix")
        print("  Examples:")
        print("    carver.py test.bin 96304")
        print("    carver.py test.bin 5 96304")
        print("    carver.py test.bin $5 $17810")
        print("    carver.py test.bin 0x5 0x17810")
        sys.exit(1)

    input_file = sys.argv[1]
    offset_strs = sys.argv[2:]

    try:
        offsets = [parse_offset(offset_str) for offset_str in offset_strs]
    except ValueError as e:
        print(f"Error: Invalid offset. Must be decimal or hex (with $ or 0x prefix).")
        sys.exit(1)

    split_binary_file(input_file, offsets)


if __name__ == "__main__":
    main()
