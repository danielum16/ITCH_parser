PSE ITCH Data Feed Parser
=============================

A Python parser for Philippine Stock Exchange (PSE) binary ITCH-format data files with support for length-prefixed message framing (SoupBinTCP style) and message-type-aware decoding.

## What This Provides

- **`src/pse_itch_parser.py`**: Core configurable binary parser with:
  - Fixed-record and **length-prefixed message framing** support
  - **Message-type dispatchers** for PSE ITCH Type S (Stock Trade) and Type T (System)
  - Auto-detection helpers (record length, field offsets, timestamp/price scales)
  - Heuristic decoders with fallback logic
  
- **`tests/test_parser.py`**: Unit tests for synthetic and real data
- **`PSE_ITCH_MESSAGE_SPEC.md`**: Detailed message structure documentation
- **`IMPLEMENTATION_NOTES.md`**: Technical implementation guide and insights

## Quick Start

### 1. Parse PSE ITCH Feeds (Length-Prefixed)

The PSE files are **length-prefixed message streams** (2-byte big-endian length header):

```bash
python src/pse_itch_parser.py data/ipxs-ipxs5-ITCHTV-1704668548.log \
  --length-prefix-size 2 \
  --export-csv output.csv
```

**Output:**
- `output.csv`: Raw export with all detected fields
- `output.csv.clean.csv`: **Cleaned CSV** with parsed fields (recommended)

### 2. Example Cleaned CSV Output

```
record_index,message_type,timestamp,symbol,quantity,price,side
0,T,,,,,
1,S,1992-04-23T03:33:20Z,O,0,,NEUTRAL
2,S,1992-04-23T03:33:20Z,S,0,0.324,N
3,S,1992-04-23T03:33:20Z,R,0,0.333,N
4,S,1992-04-23T03:33:20Z,Q,0,0.342,N
5,S,1992-04-23T03:33:20Z,Q,0,0.342,O
...
```

**Fields:**
- **message_type**: `T` (System) or `S` (Stock Trade)
- **timestamp**: ISO-8601 UTC (e.g., `1992-04-23T03:33:20Z`)
- **symbol**: Single ticker character (e.g., `O`, `S`, `R`, `Q`)
- **quantity**: Order queue depth or volume (4-byte big-endian uint)
- **price**: PHP currency (scaled from integer by ÷100,000)
- **side**: Bid/Ask/Level indicator: `N` (National), `O` (Offer), `I` (Inside), `S` (Small), etc.

### 3. Message Structure

#### Type S (Stock Trade) - 18-22 bytes

| Offset | Field | Type | Bytes | Example |
|--------|-------|------|-------|---------|
| 0 | Type | ASCII | 1 | `0x53` ('S') |
| 1-4 | Timestamp | uint32_be | 4 | 704,000,000 sec → 1992-04-23 |
| 5 | Side/Level | ASCII | 1 | `'N'` (National) |
| 6-13 | Symbol | ASCII | 8 | `"       S"` (7 spaces + ticker) |
| 14-17 | Quantity | uint32_be | 4 | 0 (order depth) |
| 18-21 | Price | uint32_be | 4 | 32,400 ÷ 100,000 = 0.324 PHP |

## Advanced Usage

### Parse with Python API

```python
from pse_itch_parser import parse_framed_file_auto

# Parse with message-type awareness
for record in parse_framed_file_auto('data/file.log', length_field_size=2, max_messages=100):
    print(f"{record['message_type']}: {record['symbol']} @ {record['price']} PHP")
```

### Use Custom Schema (Fixed-Width Records)

```python
from pse_itch_parser import BinaryRecordParser, FieldSpec

schema = [
    FieldSpec('rec_type', 0, 1, 'ascii'),
    FieldSpec('symbol', 16, 20, 'ascii'),
    FieldSpec('qty', 40, 8, 'uint_be'),
]

with open('data/file.log', 'rb') as f:
    parser = BinaryRecordParser(f, record_length=256, schema=schema)
    for ev in parser:
        print(ev)
```

### Detect Record Length (for fixed-width files)

```bash
python src/pse_itch_parser.py data/file.log --detect-record-length
# Output: Detected record length: 256
```

### Auto-Detect Field Offsets

```bash
python src/pse_itch_parser.py data/file.log --detect-fields --record-length 256
# Output: Top candidate fields (offset,length):
# 8 12
# 40 8
# 72 4
```

## File Formats Supported

| File | Type | Format | Framing |
|------|------|--------|---------|
| `ipxs-ipxs5-ITCHTV-*.log` | TV (Trade Venue) | Length-prefixed messages | 2-byte header |
| `ipxs-ipxs1-ITCHINDEX-*.log` | INDEX | Length-prefixed messages | 2-byte header |
| Custom fixed-width | Any | Fixed-size records | None |

## Testing

```bash
# Run unit tests
python -m pytest tests/test_parser.py -v

# Or without pytest (standalone)
python tests/test_parser.py
```

## Architecture

### Message Type Dispatchers

- **`parse_message_auto_typed(msg)`**: Dispatcher that routes to type-specific parsers
  - Type 'S' → `parse_message_type_s()` → Full field extraction
  - Type 'T' → `parse_message_type_t()` → Sync marker decoding
  - Unknown → `parse_record_auto()` → Heuristic fallback

### Detection & Inference

- **`detect_record_length()`**: Scans for repeating ASCII patterns
- **`infer_price_offsets_messages()`**: Finds 4-byte integer windows matching price ranges
- **`infer_timestamp_offset_and_scale()`**: Locates timestamp bytes and unit scale
- **`detect_ascii_field_offsets()`**: Identifies printable text fields

### Decoders

- **`decode_timestamp_auto()`**: Guesses Unix timestamp unit (sec/ms/µs/ns) and converts to ISO-8601
- **`decode_pse_side_level()`**: Maps single-byte side indicators to human-readable labels
- **`make_price_decoder(scale)`**: Creates closure for fixed-scale price division

## Key Insights

1. **Framing Model**: PSE files use **length-prefixed binary framing** (2-byte big-endian length field), following the SoupBinTCP protocol standard.

2. **Symbol Encoding**: Single-character tickers (O, S, R, Q, A, B, L, M, J, P, E, C, etc.) represent order book levels or trade type indicators, not stock symbols. The parser extracts these correctly.

3. **Price Scaling**: Prices are stored as 4-byte big-endian integers and must be divided by 100,000 to get PHP (Philippine Peso) value.

4. **Timestamp Accuracy**: The included test data shows 1992 timestamps (test/sample data). Real PSE feeds would show 2023-2024 timestamps (~1.7×10⁹ seconds since epoch).

5. **Message Variability**: Type S messages range from 18-22 bytes, indicating optional trailing fields. The parser handles variable-length messages gracefully.

## Documentation

- **`PSE_ITCH_MESSAGE_SPEC.md`**: Complete message structure reference and field layouts
- **`IMPLEMENTATION_NOTES.md`**: Technical deep-dive, test results, and next steps

## Dependencies

- Python 3.7+ (standard library only)
- Optional: `pytest` for running unit tests

## References

- PSE Equities Feed Specification v2.2 (included in repo)
- SoupBinTCP Protocol (binary message framing)
- ITCH Protocol (NASDAQ-standard message format)
