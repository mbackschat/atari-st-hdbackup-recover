"""
Binary utilities for reading Atari ST big-endian data.
All multi-byte values in Atari ST files are big-endian (Motorola 68000).
"""

import struct


def read_be_word(data, offset):
    """
    Read a big-endian 16-bit word from data at offset.

    Args:
        data: bytes object
        offset: position to read from

    Returns:
        int (0-65535) or None if out of bounds
    """
    if offset < 0 or offset + 2 > len(data):
        return None
    return struct.unpack('>H', data[offset:offset+2])[0]


def read_be_long(data, offset):
    """
    Read a big-endian 32-bit long from data at offset.

    Args:
        data: bytes object
        offset: position to read from

    Returns:
        int (0-4294967295) or None if out of bounds
    """
    if offset < 0 or offset + 4 > len(data):
        return None
    return struct.unpack('>I', data[offset:offset+4])[0]


def read_be_word_signed(data, offset):
    """
    Read a big-endian signed 16-bit word from data at offset.

    Args:
        data: bytes object
        offset: position to read from

    Returns:
        int (-32768 to 32767) or None if out of bounds
    """
    if offset < 0 or offset + 2 > len(data):
        return None
    return struct.unpack('>h', data[offset:offset+2])[0]


def is_valid_size(size, min_size=0, max_size=10*1024*1024):
    """
    Check if a size value is within reasonable bounds.

    Args:
        size: size to check
        min_size: minimum valid size
        max_size: maximum valid size (default 10MB)

    Returns:
        bool
    """
    return min_size <= size <= max_size


def safe_slice(data, offset, length):
    """
    Safely extract a slice of data, returning None if out of bounds.

    Args:
        data: bytes object
        offset: start position
        length: number of bytes to extract

    Returns:
        bytes or None if out of bounds
    """
    if offset < 0 or offset + length > len(data):
        return None
    return data[offset:offset+length]
