# Implementation Plan: Atari ST Degas to PNG Converter

## Overview
This document captures the key learnings from implementing the Degas PI1/PI2/PI3 to PNG converter. Use this alongside CLAUDE.md and Images.md to reproduce the implementation.

## File Format Structure

### DEGAS Elite Uncompressed Format (32066 bytes)
```
Offset   Size   Description
------   ----   -----------
0        2      Resolution word (big-endian): 0=Low, 1=Medium, 2=High
2        32     Palette (16 words, big-endian)
34       32000  Image data (bitplanes)
32034    32     Animation tables (DEGAS Elite only)
```

### DEGAS Classic Format (32034 bytes)
Same as above but without the last 32 bytes.

## Resolution Modes

| Mode | Resolution | Planes | Colors | Extension |
|------|-----------|--------|--------|-----------|
| 0    | 320×200   | 4      | 16     | .PI1      |
| 1    | 640×200   | 2      | 4      | .PI2      |
| 2    | 640×400   | 1      | 2      | .PI3      |

## Critical Implementation Details

### 1. Palette Format (Atari ST Hardware Format)

The palette consists of 16 words (32 bytes) in big-endian format.

**Palette Word Structure:**
```
Bit pattern: 0000 0RRR 0GGG 0BBB
             ^^^^ ^^^^ ^^^^ ^^^^
             |    |    |    |
             |    Red  Green Blue
             |    (0-7) (0-7) (0-7)
             Always 0
```

**Extraction:**
```python
r = (pal_word >> 8) & 0x07
g = (pal_word >> 4) & 0x07
b = pal_word & 0x07

# Scale from 0-7 to 0-255
r = (r * 255) // 7
g = (g * 255) // 7
b = (b * 255) // 7
```

### 2. Bitplane Organization (THE CRITICAL PART!)

**❗ KEY INSIGHT:** Bitplanes are **interleaved by words within each scanline**, NOT stored as sequential planes.

#### Low Resolution (320×200, 4 bitplanes)

**WRONG Approach (Sequential Planes):**
```
Scanline layout:
[all 20 words of plane 0][all 20 words of plane 1][all 20 words of plane 2][all 20 words of plane 3]
```

**CORRECT Approach (Word-Interleaved):**
```
Scanline layout:
[word0_p0][word0_p1][word0_p2][word0_p3][word1_p0][word1_p1][word1_p2][word1_p3]...
```

Each scanline contains:
- 320 pixels ÷ 16 pixels/word = 20 word groups
- Each word group has 4 words (one per bitplane)
- Total: 20 × 4 words × 2 bytes = 160 bytes per scanline

**Decoding Algorithm:**
```python
words_per_line = 320 // 16  # 20 words

for y in range(200):
    line_offset = y * 20 * 4 * 2  # 20 words × 4 planes × 2 bytes

    for x in range(20):  # For each word group
        word_offset = line_offset + (x * 4 * 2)  # Skip 4 words (8 bytes)

        plane0 = read_word(word_offset + 0)
        plane1 = read_word(word_offset + 2)
        plane2 = read_word(word_offset + 4)
        plane3 = read_word(word_offset + 6)

        # Extract 16 pixels from MSB to LSB
        for bit in range(15, -1, -1):
            pixel = ((plane0 >> bit) & 1) | \
                   (((plane1 >> bit) & 1) << 1) | \
                   (((plane2 >> bit) & 1) << 2) | \
                   (((plane3 >> bit) & 1) << 3)
```

#### Medium Resolution (640×200, 2 bitplanes)

Same principle: **word-interleaved, not sequential.**

```
Scanline layout:
[word0_p0][word0_p1][word1_p0][word1_p1][word2_p0][word2_p1]...
```

Each scanline contains:
- 640 pixels ÷ 16 pixels/word = 40 word groups
- Each word group has 2 words (one per bitplane)
- Total: 40 × 2 words × 2 bytes = 160 bytes per scanline

**Decoding Algorithm:**
```python
words_per_line = 640 // 16  # 40 words

for y in range(200):
    line_offset = y * 40 * 2 * 2  # 40 words × 2 planes × 2 bytes

    for x in range(40):  # For each word group
        word_offset = line_offset + (x * 2 * 2)  # Skip 2 words (4 bytes)

        plane0 = read_word(word_offset + 0)
        plane1 = read_word(word_offset + 2)

        for bit in range(15, -1, -1):
            pixel = ((plane0 >> bit) & 1) | \
                   (((plane1 >> bit) & 1) << 1)
```

#### High Resolution (640×400, 1 bitplane - Monochrome)

Only one bitplane, so no interleaving issues.

```python
for y in range(400):
    line_offset = y * 80  # 80 bytes per scanline

    for x in range(40):  # 40 words
        word_offset = line_offset + (x * 2)
        word = read_word(word_offset)

        for bit in range(15, -1, -1):
            pixel = (word >> bit) & 1
```

### 3. Bit Extraction Order

Always extract pixels from **MSB to LSB** (bit 15 down to bit 0):
```python
for bit in range(15, -1, -1):  # MSB first
```

Not:
```python
for bit in range(0, 16):  # WRONG - LSB first
```

## Implementation Checklist

- [ ] Parse header (2 bytes, big-endian)
- [ ] Validate resolution is 0, 1, or 2
- [ ] Parse palette (16 words, big-endian, extract RGB from 12-bit format)
- [ ] Extract image data (32000 bytes starting at offset 34)
- [ ] Decode bitplanes using **word-interleaved** format
- [ ] Create indexed PNG with palette
- [ ] Save with same filename but .PNG extension

## Testing Strategy

To verify correct implementation:

1. Generate test images with different interpretations:
   - Sequential planes (will look garbled)
   - Word-interleaved (correct)
   - LSB-to-MSB bit order (will look garbled)

2. Visual inspection:
   - Low-res images should show clear text and graphics
   - Medium-res images should maintain proper aspect ratio
   - Colors should match Atari ST palette

## Common Pitfalls

1. **Sequential plane storage** - The most common mistake. Atari ST uses word-interleaved bitplanes.
2. **Wrong byte order** - Always use big-endian for words.
3. **Wrong bit extraction order** - Extract MSB to LSB, not LSB to MSB.
4. **Palette scaling** - Remember to scale 0-7 values to 0-255 for RGB.

## References

- Images.md: Detailed format specifications
- CLAUDE.md: Project requirements
- Atari Wiki: https://www.atari-wiki.com/index.php?title=DEGAS_file_format

## Verification

The correct implementation will show:
- Clear, readable text in images
- Proper colors (blues, reds, greens for typical Atari ST graphics)
- No horizontal displacement or garbling
- Smooth gradients and proper graphics alignment
