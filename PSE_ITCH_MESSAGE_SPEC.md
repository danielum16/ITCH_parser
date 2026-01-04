# PSE ITCH Message Specification (Inferred from Binary Analysis)

## Overview
The PSE (Philippine Stock Exchange) feeds binary ITCH-style messages using **length-prefixed framing**:
- 2-byte big-endian **length field** (message payload size)
- Variable-length **message payload**

## Framing Model
```
[length: 2 bytes (big-endian)] [message payload: length bytes]
[length: 2 bytes (big-endian)] [message payload: length bytes]
...
```

## Message Types

### Type 'T' (0x54) - System Header / Sync
**Length:** 5 bytes  
**Structure:**
- Byte 0: Message type = 0x54 ('T')
- Bytes 1-4: Nanosecond timestamp or sync marker

**Purpose:** Marks the start of a trading session or synchronization event.

---

### Type 'S' (0x53) - Stock Trade / Level 1 Data
**Length:** 18-22 bytes (variable)

**Structure:**
| Offset | Field | Type | Length | Description |
|--------|-------|------|--------|-------------|
| 0 | Message Type | ASCII | 1 | 0x53 ('S') or 0x73 ('s') |
| 1-4 | Timestamp | uint32_be | 4 | Seconds since Unix epoch (or milliseconds) |
| 5 | Side/Level | ASCII | 1 | Buy/Sell/Order level: 'N', 'O', 'I', 'S', 'R', 'Q', 'A', 'B' |
| 6-13 | Symbol | ASCII | 8 | Stock ticker (space-padded right) |
| 14-17 | Quantity or Order Level | uint32_be | 4 | Trading volume or order queue depth |
| 18-21 | Price | uint32_be | 4 | Scaled price (divide by 1e5 for trading price) |
| 22+ | (Optional) | bytes | variable | Padding or additional fields |

**Field Interpretations:**

#### **Side/Level Indicator (Byte 5)**
- `'N'` = National level / Best bid-ask
- `'O'` = Offer (ask) side
- `'I'` = Immediate or Inside (best prices)
- `'S'` = Small order (retail trade)
- `'R'` = Request / Regular order
- `'Q'` = Quote
- `'A'` = Ask
- `'B'` = Bid

#### **Symbol (Bytes 6-13)**
- 8-byte field (ASCII)
- Right-space-padded (e.g., `"STOCK   "` for "STOCK")
- Represents the ticker symbol

#### **Quantity (Bytes 14-17)**
- Big-endian unsigned 32-bit integer
- Number of shares or trade volume
- May represent order queue depth in Level 1 feeds

#### **Price (Bytes 18-21)**
- Big-endian unsigned 32-bit integer
- **Scale factor:** Divide by 100,000 (1e5) to get the actual trading price
- Example: raw value 2500000 → 2500000 / 100000 = 25.00 PHP

---

## Timestamp Encoding

**Byte Length:** 4 bytes (32-bit)  
**Format:** Big-endian unsigned integer  

### Interpretation:
The timestamp is typically encoded as seconds since Unix epoch (1970-01-01 00:00:00 UTC), but may also be milliseconds or nanoseconds. Heuristic detection based on magnitude:

- If value ≈ 1.7×10⁹–2×10⁹ → **Seconds** (2024)
- If value > 1×10¹² → **Milliseconds**
- If value > 1×10¹⁵ → **Microseconds**
- If value > 1×10¹⁸ → **Nanoseconds**

For PSE data with timestamp ≈ 1.7×10⁹–1.8×10⁹, **seconds** is the expected unit.

---

## Example Message Decoding

### Raw Example (Framed Message #1):
```
Hex: 53 29 f6 30 00 20 20 20 20 20 20 20 20 4f 00 00 00 00
ASCII: S).0.        O....
```

**Breakdown:**
- `53` = Message type 'S'
- `29 f6 30 00` = Timestamp (0x29f63000 = 703,311,872 seconds since epoch ≈ 1992-03-30)
- `20` = Side indicator: 0x20 (space) — may indicate "neutral" or "meta"
- `20 20 20 20 20 20 20 20` = 8 spaces → Empty/null symbol
- `4f 00 00 00` = Quantity or price: 0x4f000000 = 1,308,622,848

This appears to be a **header or synchronization message**.

### Raw Example (Framed Message #2):
```
Hex: 73 29 f6 30 00 4e 20 20 20 20 20 20 20 53 00 00 00 00 00 00 7e 90
ASCII: s).0.N       S......~.
```

**Breakdown:**
- `73` = Message type 's' (lowercase variant of 'S')
- `29 f6 30 00` = Timestamp (same as before)
- `4e` = Side: 'N' (National level / best bid-ask)
- `20 20 20 20 20 20 20 20` = 8 spaces → Empty symbol (or header)
- `53 00 00 00` = Quantity/Order level: 0x53000000 = 1,392,508,928
- `00 00 7e 90` = Price: 0x00007e90 = 32,400 (÷1e5 = 0.324 PHP) **or** this could be padding

---

## Current Limitations & Next Steps

1. **Timestamp Unit Confirmation:** PSE spec should clarify whether timestamp is in seconds, milliseconds, or other unit.
2. **Symbol Field Validation:** Confirm exact position and padding behavior for stock tickers.
3. **Quantity vs. Price Scale:** The 4-byte fields at offset 14-17 and 18-21 need precise scale factors confirmed.
4. **Message Type Coverage:** Identify other message types (if any) beyond 'T' and 'S'.
5. **Optional Fields:** Determine if message length variations (18 vs. 22 bytes) indicate presence of optional trailing fields.

---

## Files Tested Against

- `data/ipxs-ipxs5-ITCHTV-1704668548.log` (TV Feed)
- `data/ipxs-ipxs1-ITCHINDEX-1704668548.log` (Index Feed)

Both are **length-prefixed binary streams** with 2-byte big-endian length headers.

---

## References

- PSE Equities Feed Specification v2.2 (PDF)
- SoupBinTCP Protocol (binary framing standard)
- ITCH Protocol (NASDAQ-derived message format)
