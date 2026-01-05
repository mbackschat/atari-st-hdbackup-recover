"""
Atari ST binary executable and object file detectors.

Formats:
- GEMDOS executables (0x601A): PRG/TOS/TTP/ACC
- Turbo-C objects (0x4EFA): .TCO
- Devpac objects (FF65): .O with embedded filename
"""

from utils.binary_utils import read_be_word, read_be_long, read_be_word_signed


def detect_turboc_object(data, size):
    """
    Detect Turbo-C / Pure-C object files (0x4EFA magic).

    Format has exact size formula: 32 + tlen + dlen + blen

    Args:
        data: file content bytes
        size: file size

    Returns:
        tuple: (match: bool, ext: str, confidence: int, reason: str)
    """
    # Header is 32 bytes
    if size < 32:
        return False, '', 0, ''

    # Check magic: 0x4EFA (JMP (d16,PC))
    magic = read_be_word(data, 0x00)
    if magic != 0x4EFA:
        return False, '', 0, ''

    # Read displacement (should typically be 0x001C to jump to offset 0x20)
    displacement = read_be_word_signed(data, 0x02)

    # Read segment sizes
    tlen = read_be_long(data, 0x04)
    dlen = read_be_long(data, 0x08)
    blen = read_be_long(data, 0x0C)  # This is stored metadata size, not BSS!
    slen = read_be_long(data, 0x10)  # Should be 0

    if any(x is None for x in [tlen, dlen, blen, slen]):
        return False, '', 0, ''

    # slen should be 0 in Turbo-C format
    if slen != 0:
        return False, '', 0, 'slen not zero'

    # Compute expected file size
    expected_size = 32 + tlen + dlen + blen

    # EXACT SIZE CHECK
    if expected_size != size:
        return False, '', 0, f'Size mismatch: expected {expected_size}, got {size}'

    # Entry point should typically be 0x20
    entry = 4 + displacement
    if entry < 0 or entry > size:
        return False, '', 0, 'Invalid entry point'

    # Sanity checks on segment sizes
    MAX_SEGMENT = 10 * 1024 * 1024  # 10MB max
    if tlen > MAX_SEGMENT or dlen > MAX_SEGMENT or blen > MAX_SEGMENT:
        return False, '', 0, 'Segment size too large'

    # All checks passed
    return True, 'TCO', 100, 'Valid Turbo-C object with exact size match'


def detect_devpac_object(data, size):
    """
    Detect HiSoft Devpac object files (FF 65 magic + embedded filename).

    Format: FF 65 <filename\\0> <record stream> <end marker>

    Args:
        data: file content bytes
        size: file size

    Returns:
        tuple: (match: bool, ext: str, confidence: int, reason: str, embedded_name: str)
    """
    # Minimum size: magic (2) + filename (at least 1 char + null) + some data
    if size < 10:
        return False, '', 0, '', ''

    # Check signature: FF 65
    if data[0] != 0xFF or data[1] != 0x65:
        return False, '', 0, '', ''

    # Extract embedded filename (NUL-terminated, max 64 bytes)
    filename_start = 2
    filename_end = None
    max_filename_len = min(64, size - 3)

    for i in range(filename_start, filename_start + max_filename_len):
        if data[i] == 0:
            filename_end = i
            break

    if filename_end is None:
        return False, '', 0, '', 'No filename terminator found'

    # Extract filename
    try:
        embedded_name = data[filename_start:filename_end].decode('ascii', errors='ignore')
    except:
        return False, '', 0, '', 'Invalid filename encoding'

    # Strip extension from embedded name (e.g., "modf.o" -> "modf")
    # This allows renaming as: <original>-<embedded_stem>.O
    if '.' in embedded_name:
        embedded_name = embedded_name.rsplit('.', 1)[0]

    # Filename should be mostly printable ASCII
    if not all(c.isprintable() or c == ' ' for c in embedded_name):
        return False, '', 0, '', 'Non-printable filename'

    # Record stream starts after filename terminator
    record_start = filename_end + 1

    # Parse record stream to find end marker
    # This is a simplified check - full parsing would be more complex
    # For now, we verify basic structure and look for reasonable patterns

    # Devpac object files typically have specific record types
    # Without full spec, we do basic validation:
    # - File should have reasonable size (< 5MB for object file)
    # - Embedded filename should look like a module name

    if size > 5 * 1024 * 1024:
        return False, '', 0, '', 'File too large for Devpac object'

    # Check if embedded name looks like a valid module name
    if len(embedded_name) == 0 or len(embedded_name) > 32:
        return False, '', 0, '', 'Invalid filename length'

    # High confidence match
    return True, 'O', 95, f'Devpac object with embedded name: {embedded_name}', embedded_name


def detect_gemdos_executable(data, size):
    """
    Detect GEMDOS executable files (0x601A magic): PRG/TOS/TTP/ACC or .O object files.

    This function implements the detection rules from filetypes/601A.md to distinguish
    between final executables (.PRG) and linkable object modules (.O).

    Detection rules:
    - Rule O1: DRI-style symbol table (slen % 14 == 0)
    - Rule O2: Tagged symbol values (high bit set) → DEFINITIVE .O
    - Rule O4: Invalid runtime relocation stream → .O
    - Rule X1: Valid relocation stream → .PRG

    Args:
        data: file content bytes
        size: file size

    Returns:
        tuple: (match: bool, ext: str, confidence: int, reason: str)
    """
    # Header is 28 bytes (0x1C)
    if size < 28:
        return False, '', 0, ''

    # Check magic: 0x601A (BRA +$1A)
    magic = read_be_word(data, 0x00)
    if magic != 0x601A:
        return False, '', 0, ''

    # Read segment sizes
    tlen = read_be_long(data, 0x02)
    dlen = read_be_long(data, 0x06)
    blen = read_be_long(data, 0x0A)  # BSS - not stored
    slen = read_be_long(data, 0x0E)  # Symbol table
    # 0x12-0x19: reserved (usually zero)
    # 0x1A: flags

    if any(x is None for x in [tlen, dlen, blen, slen]):
        return False, '', 0, ''

    # TEXT starts at 0x1C
    text_start = 0x1C

    # Minimum file size check
    min_size = 28 + tlen + dlen + slen
    if size < min_size:
        return False, '', 0, 'File too small for header values'

    # Sanity checks
    MAX_SEGMENT = 20 * 1024 * 1024  # 20MB max
    if tlen > MAX_SEGMENT or dlen > MAX_SEGMENT or slen > MAX_SEGMENT:
        return False, '', 0, 'Segment size unreasonable'

    if blen > MAX_SEGMENT:
        return False, '', 0, 'BSS size unreasonable'

    # Object vs Executable detection
    # CRITICAL: Check relocation stream FIRST (Rule X1 takes precedence over Rule O2)
    # Reason: Final executables CAN have tagged symbols if built from .O files

    is_object = False
    object_confidence = 0
    object_reason = ''

    reloc_start = 28 + tlen + dlen + slen
    has_valid_relocation = False
    has_invalid_relocation = False

    # Step 1: Check relocation table validity (Rule X1 vs Rule O4)
    if reloc_start < size:
        first_reloc = read_be_long(data, reloc_start)
        if first_reloc is not None:
            if first_reloc == 0:
                # No relocations - could be either format
                # Continue to symbol analysis
                pass
            elif first_reloc < tlen + dlen:
                # Rule X1: Valid runtime relocation offset
                # This is STRONG evidence of final executable
                has_valid_relocation = True
            else:
                # Rule O4: Relocation offset exceeds TEXT+DATA
                # This suggests linker-internal format (object file)
                has_invalid_relocation = True

    # Step 2: If we have valid relocation, it's an EXECUTABLE (ignore symbol tags)
    if has_valid_relocation:
        # Rule X1 wins: Valid relocation stream → EXECUTABLE
        return True, 'PRG', 92, 'GEMDOS executable (valid relocation stream)'

    # Step 3: Check symbols only if relocation didn't decide
    # (either no relocation, or invalid relocation)
    if slen > 0 and slen % 14 == 0:
        # Rule O1: DRI-style symbol table structure
        num_symbols = slen // 14
        symbol_offset = 28 + tlen + dlen

        # Rule O2: Check if symbols have tagged (relocatable) values
        # Check up to first 20 symbols or all if fewer
        check_count = min(20, num_symbols)
        tagged_count = 0

        for i in range(check_count):
            sym_off = symbol_offset + (i * 14)
            if sym_off + 14 <= size:
                # Symbol value is at offset +8 within the 14-byte entry
                sym_value = read_be_long(data, sym_off + 8)
                if sym_value is not None and (sym_value & 0x80000000) != 0:
                    tagged_count += 1

        # If significant portion (>= 1/3) of checked symbols are tagged
        if check_count > 0 and tagged_count >= check_count // 3:
            # Rule O2: Tagged symbols indicate object module
            is_object = True
            object_confidence = 95
            object_reason = f'GEMDOS object (.O): DRI symbols with tagged values ({tagged_count}/{check_count})'

            # If we also have invalid relocation, increase confidence
            if has_invalid_relocation:
                object_confidence = 98
                object_reason = f'GEMDOS object (.O): Tagged symbols + invalid relocation'

    # Final decision
    if is_object:
        return True, 'O', object_confidence, object_reason
    else:
        # Default to executable (PRG)
        return True, 'PRG', 92, 'GEMDOS executable (PRG/TOS/TTP/ACC)'


def detect_binary_executable(data, size):
    """
    Master detector for binary executables and objects.
    Tries all formats in priority order.

    Args:
        data: file content bytes
        size: file size

    Returns:
        tuple: (match: bool, ext: str, confidence: int, reason: str, extra_info: dict)
    """
    # Try Turbo-C first (most specific - exact size match)
    match, ext, conf, reason = detect_turboc_object(data, size)
    if match:
        return match, ext, conf, reason, {}

    # Try Devpac (distinctive signature + embedded filename)
    result = detect_devpac_object(data, size)
    if len(result) == 5:  # Has embedded_name
        match, ext, conf, reason, embedded_name = result
        if match:
            return match, ext, conf, reason, {'embedded_name': embedded_name}

    # Try GEMDOS executable last (most common, but less specific)
    match, ext, conf, reason = detect_gemdos_executable(data, size)
    if match:
        return match, ext, conf, reason, {}

    return False, '', 0, '', {}
