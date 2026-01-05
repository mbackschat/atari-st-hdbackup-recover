# Implementation Plan: Atari ST File Extractor

## Overview
Extract files from binary HD backup containing Atari ST files in fragment format.

## Architecture

### Main Components

1. **Fragment Header Parser**
   - Read 8-byte header (big-endian)
   - Parse: length (4 bytes), compression flag (2 bytes), last fragment flag (2 bytes)
   - Return structured header data

2. **RLE Decompressor**
   - Scan for 0xC7 marker bytes
   - Read repetition count and value
   - Expand: 0xC7 + count + value → value repeated count times
   - Handle non-RLE bytes (copy as-is)

3. **Fragment Processor**
   - Read fragment content (length bytes from header)
   - Decompress if compression flag is set
   - Append to current file buffer
   - Handle 2-byte alignment padding (if length is odd)

4. **File Assembler**
   - Accumulate fragments until last-fragment flag is set
   - Write complete file to output directory
   - Increment file counter
   - Reset buffer for next file

5. **Output Manager**
   - Handle output directory creation/backup
   - Generate Atari ST compatible filenames (00001.TXT format)
   - Move existing files to backup subfolder if needed

## Implementation Steps

### Step 1: CLI Argument Parsing
```python
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input_file', help='Binary file to extract from')
    parser.add_argument('output_dir', nargs='?', default='extracted')
```

### Step 2: Output Directory Handling
```python
def prepare_output_dir(output_dir):
    if os.path.exists(output_dir):
        # Move existing files to random backup subfolder
        backup_name = f"backup_{timestamp or uuid}"
        move_existing_files(output_dir, backup_name)
    else:
        os.makedirs(output_dir)
```

### Step 3: Fragment Header Parsing
```python
def read_fragment_header(file):
    header_bytes = file.read(8)
    if len(header_bytes) < 8:
        return None  # EOF

    length = struct.unpack('>I', header_bytes[0:4])[0]
    compressed = struct.unpack('>H', header_bytes[4:6])[0]
    last_fragment = struct.unpack('>H', header_bytes[6:8])[0]

    return {
        'length': length,
        'compressed': bool(compressed),
        'last_fragment': bool(last_fragment)
    }
```

### Step 4: RLE Decompression
**RLE Rule Clarification**:
- 0xC7 is ALWAYS a marker
- Format: 0xC7 + count + value → outputs 'value' repeated 'count' times
- To output literal 0xC7: use 0xC7 0x01 0xC7 (repeat 0xC7 once)

```python
def decompress_rle(data):
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
                # Malformed RLE at end of data
                raise ValueError(f"Incomplete RLE sequence at position {i}")
        else:
            result.append(data[i])
            i += 1
    return bytes(result)
```

### Step 5: Main Extraction Loop
```python
def extract_files(input_file, output_dir):
    file_counter = 1
    current_file_data = bytearray()

    with open(input_file, 'rb') as f:
        while True:
            header = read_fragment_header(f)
            if header is None:
                break  # EOF

            # Read fragment content
            content = f.read(header['length'])

            # Decompress if needed
            if header['compressed']:
                content = decompress_rle(content)

            # Append to current file
            current_file_data.extend(content)

            # Handle alignment padding
            if header['length'] % 2 == 1:
                f.read(1)  # Skip padding byte

            # Write file if last fragment
            if header['last_fragment']:
                write_file(output_dir, file_counter, current_file_data)
                file_counter += 1
                current_file_data = bytearray()
```

### Step 6: File Writing
```python
def write_file(output_dir, counter, data):
    filename = f"{counter:05d}.TXT"  # 00001.TXT format
    filepath = os.path.join(output_dir, filename)
    with open(filepath, 'wb') as f:
        f.write(data)
```

## Error Handling

1. **File not found**: Clear error message if input file doesn't exist
2. **Truncated data**: Warn if fragment content is shorter than header length
3. **Invalid header**: Detect and skip malformed headers
4. **Write errors**: Handle disk full or permission issues

## Testing Strategy

1. Test with example headers from spec
2. Verify RLE decompression with known sequences
3. Test alignment padding (odd/even lengths)
4. Test multi-fragment file assembly
5. Test output directory backup functionality

## Open Questions

1. ~~**RLE escape sequence**: Can 0xC7 appear as literal data?~~ **ANSWERED**: 0xC7 is always a marker. Use 0xC7 0x01 0xC7 for literal 0xC7.
2. **Validation level**: Should we validate checksums or just process blindly?
3. **Logging**: Add verbose mode to show fragment processing details?
4. **Backup folder naming**: Timestamp vs UUID vs random string?

## File Structure
```
atari_extractor.py      # Main implementation
CLAUDE.md               # Specification
PLAN.md                 # This file
extracted/              # Default output directory
  00001.TXT
  00002.TXT
  ...
```
