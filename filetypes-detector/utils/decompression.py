"""
Decompression algorithms for Atari ST compressed image formats.
"""


def decompress_packbits_scanline(data, offset, expected_size):
    """
    Decompress a single scanline using PackBits/RLE compression.
    Used by DEGAS Elite Compressed format.

    Args:
        data: compressed data bytes
        offset: starting position in data
        expected_size: expected decompressed size in bytes

    Returns:
        tuple: (decompressed_bytes, bytes_consumed) or (None, 0) on failure
    """
    output = bytearray()
    pos = offset

    try:
        while len(output) < expected_size and pos < len(data):
            if pos >= len(data):
                return None, 0

            control = data[pos]
            pos += 1

            if control < 128:
                # Copy next (control + 1) literal bytes
                count = control + 1
                if pos + count > len(data) or len(output) + count > expected_size:
                    return None, 0
                output.extend(data[pos:pos + count])
                pos += count
            else:
                # Repeat next byte (257 - control) times
                count = 257 - control
                if pos >= len(data) or len(output) + count > expected_size:
                    return None, 0
                byte_val = data[pos]
                pos += 1
                output.extend([byte_val] * count)

        if len(output) != expected_size:
            return None, 0

        return bytes(output), pos - offset

    except (IndexError, ValueError):
        return None, 0


def decompress_degas_elite(data, compressed_offset, palette_offset):
    """
    Decompress DEGAS Elite compressed image data.
    Format: 4 bitplanes × 200 scanlines, each scanline compressed separately.

    Args:
        data: full file data
        compressed_offset: offset to compressed data (after palette)
        palette_offset: offset to palette (to calculate data start)

    Returns:
        bytes: decompressed 32000 bytes or None on failure
    """
    output = bytearray()
    pos = compressed_offset

    # DEGAS Elite compresses each scanline separately
    # Resolution determines scanline size:
    # - Low res (320x200x4): 160 bytes/scanline × 200 = 32000 bytes total
    # - Med res (640x200x2): 160 bytes/scanline × 200 = 32000 bytes total
    # - High res (640x400x1): 80 bytes/scanline × 200 = 16000 bytes total (rarely compressed)

    # For low/med res: 200 scanlines of 160 bytes each
    scanlines = 200
    scanline_size = 160

    try:
        for _ in range(scanlines):
            if pos >= len(data):
                return None

            decompressed, consumed = decompress_packbits_scanline(data, pos, scanline_size)
            if decompressed is None:
                return None

            output.extend(decompressed)
            pos += consumed

        if len(output) != 32000:
            return None

        return bytes(output)

    except Exception:
        return None


def decompress_stad(data, offset, id_byte, pack_byte, special_byte, expected_size=32000):
    """
    Decompress STAD PAC format.

    Format:
        - Header: "pM85" or "pM86" + 3 control bytes (IdByte, PackByte, SpecialByte)
        - Compressed data using RLE-like encoding

    Args:
        data: full file data
        offset: offset to compressed data (after header)
        id_byte: ID byte from header
        pack_byte: pack control byte
        special_byte: special control byte
        expected_size: expected output size (default 32000 for full screen)

    Returns:
        bytes: decompressed data or None on failure
    """
    output = bytearray()
    pos = offset

    try:
        while len(output) < expected_size and pos < len(data):
            if pos >= len(data):
                return None

            byte_val = data[pos]
            pos += 1

            if byte_val == id_byte:
                # Control sequence
                if pos >= len(data):
                    return None

                next_byte = data[pos]
                pos += 1

                if next_byte == 0:
                    # End marker
                    break
                elif next_byte == id_byte:
                    # Escaped ID byte - output literal ID byte
                    output.append(id_byte)
                elif next_byte == pack_byte:
                    # RLE sequence: repeat next byte N times
                    if pos + 1 >= len(data):
                        return None
                    count = data[pos]
                    pos += 1
                    repeat_byte = data[pos]
                    pos += 1

                    if len(output) + count > expected_size:
                        return None
                    output.extend([repeat_byte] * count)
                else:
                    # Unknown control - might be format variation
                    return None
            else:
                # Literal byte
                output.append(byte_val)

        # Verify we got exactly the expected size
        if len(output) != expected_size:
            return None

        return bytes(output)

    except (IndexError, ValueError):
        return None
