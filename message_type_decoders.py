"""
Message Type Decoders for PSE ITCH Feed

This module implements decoders for the 10 discovered message types:
- 'A' (Add Order) - 30 bytes
- 'R' (Trade Report/Unknown) - 90 bytes
- 'k' (Order Book/Unknown) - 30 bytes  
- 'H' (Trading Status) - 11 bytes
- 'f' (Unknown PSE type) - 24 bytes
- 'L' (Listing) - 17 bytes
- 's' (Unknown PSE type) - 22 bytes
- 'M' (Unknown PSE type) - 25 bytes
- 'S' (Stock Trade) - 18-22 bytes
- 'T' (System/Sync) - 5 bytes

Based on analysis of binary ITCH feed: ipxs-ipxs5-ITCHTV-1704668548.log

Message Type A (Add Order) - 30 bytes
Field layout (estimated from ITCH standard):
  0:1   - Message Type ('A')
  1:5   - Timestamp (4 bytes, big-endian seconds)
  5:13  - Order ID (8 bytes)
  13:21 - Security Symbol (8 bytes ASCII)
  21:25 - Quantity (4 bytes, big-endian)
  25:29 - Price (4 bytes, big-endian fixed-point with 2 decimals)
  29:30 - Side ('B' for buy, 'S' for sell)

Message Type R (Trade Report) - 90 bytes
Field layout (PSE-specific extension):
  0:1   - Message Type ('R')
  1:5   - Timestamp (4 bytes)
  5:13  - Order ID (8 bytes)
  [remaining 77 bytes - to be determined from PDF spec]

Message Type H (Trading Status) - 11 bytes
Field layout:
  0:1   - Message Type ('H')
  1:5   - Timestamp (4 bytes)
  5:11  - Status Code or Security Identifier (6 bytes)

Message Type k (Order Book/Quote) - 30 bytes
Similar structure to Type A with quote/depth information

"""

import struct
from typing import Dict, Any, Optional


def decode_timestamp(data: bytes) -> Optional[float]:
    """Decode 4-byte big-endian timestamp (Unix seconds)"""
    if len(data) < 4:
        return None
    try:
        return struct.unpack('>I', data[:4])[0]
    except:
        return None


def decode_qty(data: bytes) -> Optional[int]:
    """Decode 4-byte big-endian quantity"""
    if len(data) < 4:
        return None
    try:
        return struct.unpack('>I', data[:4])[0]
    except:
        return None


def decode_price(data: bytes, scale: int = 2) -> Optional[float]:
    """Decode 4-byte big-endian fixed-point price"""
    if len(data) < 4:
        return None
    try:
        cents = struct.unpack('>i', data[:4])[0]  # signed
        return cents / (10 ** scale)
    except:
        return None


def decode_side(byte: bytes) -> Optional[str]:
    """Decode order side from single byte"""
    if not byte:
        return None
    try:
        c = chr(byte[0])
        if c in ['B', 'S']:
            return c
        return f'0x{byte[0]:02X}'
    except:
        return None


def parse_message_type_a(msg: bytes) -> Dict[str, Any]:
    """Parse Type A: Add Order (30 bytes)
    
    Structure:
    0:1   - Message Type ('A')
    1:5   - Timestamp (seconds)
    5:13  - Order ID (8 bytes)
    13:21 - Symbol (8 bytes ASCII)
    21:25 - Quantity
    25:29 - Price (cents, /100)
    29:30 - Side
    """
    rec = {
        'message_type': 'A',
        'type_name': 'Add Order',
        'message_length': 30,
    }
    
    if len(msg) >= 1:
        rec['msg_type_byte'] = msg[0:1]
    if len(msg) >= 5:
        rec['timestamp'] = decode_timestamp(msg[1:5])
    if len(msg) >= 13:
        rec['order_id'] = int.from_bytes(msg[5:13], 'big', signed=False)
    if len(msg) >= 21:
        rec['symbol'] = msg[13:21].rstrip(b'\x00 ').decode('ascii', errors='replace')
    if len(msg) >= 25:
        rec['quantity'] = struct.unpack('>I', msg[21:25])[0]
    if len(msg) >= 29:
        rec['price'] = decode_price(msg[25:29], scale=2)
    if len(msg) >= 30:
        rec['side'] = decode_side(msg[29:30])
    
    return rec


def parse_message_type_r(msg: bytes) -> Dict[str, Any]:
    """Parse Type R: Trade Report (90 bytes)
    
    This is a PSE-specific type. Full structure TBD from PDF.
    Currently extracting known fields and preserving raw data.
    """
    rec = {
        'message_type': 'R',
        'type_name': 'Trade Report (PSE-specific)',
        'message_length': len(msg),
    }
    
    if len(msg) >= 1:
        rec['msg_type_byte'] = msg[0:1]
    if len(msg) >= 5:
        rec['timestamp'] = decode_timestamp(msg[1:5])
    if len(msg) >= 13:
        rec['order_id'] = int.from_bytes(msg[5:13], 'big', signed=False)
    
    # Preserve raw data for inspection
    if len(msg) > 13:
        rec['raw_payload'] = msg[13:].hex()
    
    # Try to extract symbol-like data (8 bytes around offset 20-28)
    if len(msg) >= 28:
        try:
            rec['symbol_raw'] = msg[13:21].rstrip(b'\x00 ').decode('ascii', errors='ignore')
        except:
            pass
    
    return rec


def parse_message_type_k(msg: bytes) -> Dict[str, Any]:
    """Parse Type k: Order Book/Quote (30 bytes)
    
    This is a PSE-specific type for order book or quote updates.
    Structure similar to Type A.
    """
    rec = {
        'message_type': 'k',
        'type_name': 'Order Book/Quote Update (PSE-specific)',
        'message_length': 30,
    }
    
    if len(msg) >= 1:
        rec['msg_type_byte'] = msg[0:1]
    if len(msg) >= 5:
        rec['timestamp'] = decode_timestamp(msg[1:5])
    if len(msg) >= 13:
        rec['order_id'] = int.from_bytes(msg[5:13], 'big', signed=False)
    if len(msg) >= 21:
        rec['symbol'] = msg[13:21].rstrip(b'\x00 ').decode('ascii', errors='replace')
    if len(msg) >= 25:
        rec['quantity'] = struct.unpack('>I', msg[21:25])[0]
    if len(msg) >= 29:
        rec['price'] = decode_price(msg[25:29], scale=2)
    if len(msg) >= 30:
        rec['side'] = decode_side(msg[29:30])
    
    return rec


def parse_message_type_h(msg: bytes) -> Dict[str, Any]:
    """Parse Type H: Trading Status (11 bytes)
    
    Structure (estimated):
    0:1   - Message Type ('H')
    1:5   - Timestamp
    5:11  - Status Code or Security Code (6 bytes)
    """
    rec = {
        'message_type': 'H',
        'type_name': 'Trading Status',
        'message_length': 11,
    }
    
    if len(msg) >= 1:
        rec['msg_type_byte'] = msg[0:1]
    if len(msg) >= 5:
        rec['timestamp'] = decode_timestamp(msg[1:5])
    if len(msg) >= 11:
        # Try to decode as ASCII or hex
        status_bytes = msg[5:11]
        try:
            rec['status_code'] = status_bytes.rstrip(b'\x00 ').decode('ascii', errors='ignore')
        except:
            rec['status_code'] = status_bytes.hex()
    
    return rec


def parse_message_type_f(msg: bytes) -> Dict[str, Any]:
    """Parse Type f: Unknown PSE Type (24 bytes)
    
    Structure TBD. Extracting available fields.
    """
    rec = {
        'message_type': 'f',
        'type_name': 'Unknown PSE Type (f)',
        'message_length': 24,
    }
    
    if len(msg) >= 1:
        rec['msg_type_byte'] = msg[0:1]
    if len(msg) >= 5:
        rec['timestamp'] = decode_timestamp(msg[1:5])
    
    if len(msg) > 5:
        rec['raw_payload'] = msg[5:].hex()
    
    return rec


def parse_message_type_l(msg: bytes) -> Dict[str, Any]:
    """Parse Type L: Listing/IPO (17 bytes)
    
    Used for new IPO listings or symbol listings.
    """
    rec = {
        'message_type': 'L',
        'type_name': 'Listing/IPO',
        'message_length': 17,
    }
    
    if len(msg) >= 1:
        rec['msg_type_byte'] = msg[0:1]
    if len(msg) >= 5:
        rec['timestamp'] = decode_timestamp(msg[1:5])
    if len(msg) >= 13:
        rec['symbol'] = msg[5:13].rstrip(b'\x00 ').decode('ascii', errors='replace')
    if len(msg) >= 17:
        rec['extra_data'] = msg[13:17].hex()
    
    return rec


def parse_message_type_s(msg: bytes) -> Dict[str, Any]:
    """Parse Type s: Unknown PSE Type (22 bytes)
    
    Structure TBD.
    """
    rec = {
        'message_type': 's',
        'type_name': 'Unknown PSE Type (s)',
        'message_length': 22,
    }
    
    if len(msg) >= 1:
        rec['msg_type_byte'] = msg[0:1]
    if len(msg) >= 5:
        rec['timestamp'] = decode_timestamp(msg[1:5])
    if len(msg) >= 13:
        try:
            rec['identifier'] = msg[5:13].rstrip(b'\x00 ').decode('ascii', errors='replace')
        except:
            rec['identifier'] = msg[5:13].hex()
    
    if len(msg) > 13:
        rec['raw_payload'] = msg[13:].hex()
    
    return rec


def parse_message_type_m(msg: bytes) -> Dict[str, Any]:
    """Parse Type M: Unknown PSE Type (25 bytes)
    
    Structure TBD.
    """
    rec = {
        'message_type': 'M',
        'type_name': 'Unknown PSE Type (M)',
        'message_length': 25,
    }
    
    if len(msg) >= 1:
        rec['msg_type_byte'] = msg[0:1]
    if len(msg) >= 5:
        rec['timestamp'] = decode_timestamp(msg[1:5])
    
    if len(msg) > 5:
        rec['raw_payload'] = msg[5:].hex()
    
    return rec


def parse_message_type_s_stock(msg: bytes) -> Dict[str, Any]:
    """Parse Type S: Stock Trade (18-22 bytes)
    
    This is a standard ITCH message type for executed trades.
    """
    rec = {
        'message_type': 'S',
        'type_name': 'Stock Trade',
        'message_length': len(msg),
    }
    
    if len(msg) >= 1:
        rec['msg_type_byte'] = msg[0:1]
    if len(msg) >= 5:
        rec['timestamp'] = decode_timestamp(msg[1:5])
    if len(msg) >= 13:
        rec['order_id'] = int.from_bytes(msg[5:13], 'big', signed=False)
    if len(msg) >= 21:
        rec['symbol'] = msg[13:21].rstrip(b'\x00 ').decode('ascii', errors='replace')
    if len(msg) >= 25:
        try:
            rec['quantity'] = struct.unpack('>I', msg[21:25])[0]
        except:
            pass
    
    return rec


def parse_message_type_t(msg: bytes) -> Dict[str, Any]:
    """Parse Type T: System Sync (5 bytes)
    
    Simple synchronization message.
    """
    rec = {
        'message_type': 'T',
        'type_name': 'System Sync',
        'message_length': 5,
    }
    
    if len(msg) >= 1:
        rec['msg_type_byte'] = msg[0:1]
    if len(msg) >= 5:
        # Typically contains a counter or sequence number
        rec['counter'] = struct.unpack('>I', msg[1:5])[0]
    
    return rec


# Dispatcher function
def decode_message(msg: bytes) -> Dict[str, Any]:
    """Decode a message based on its type byte"""
    if not msg or len(msg) < 1:
        return {'error': 'Empty message'}
    
    msg_type = chr(msg[0]) if 32 <= msg[0] < 127 else f'0x{msg[0]:02X}'
    
    decoders = {
        'A': parse_message_type_a,
        'R': parse_message_type_r,
        'k': parse_message_type_k,
        'H': parse_message_type_h,
        'f': parse_message_type_f,
        'L': parse_message_type_l,
        's': parse_message_type_s,
        'M': parse_message_type_m,
        'S': parse_message_type_s_stock,
        'T': parse_message_type_t,
    }
    
    decoder = decoders.get(msg_type)
    if decoder:
        return decoder(msg)
    else:
        return {
            'message_type': msg_type,
            'type_name': 'Unknown',
            'message_length': len(msg),
            'raw': msg.hex(),
        }


if __name__ == '__main__':
    # Test the decoders with sample data
    print("Message Type Decoders loaded successfully")
    print("Supported types: A, R, k, H, f, L, s, M, S, T")
