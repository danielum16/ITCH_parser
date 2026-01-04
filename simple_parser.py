import struct
import csv
from datetime import datetime, timezone

def parse_itch(file_path, output_csv):
    """
    Simple ITCH parser that extracts key message types and writes to CSV
    """
    records = []
    
    with open(file_path, 'rb') as f:
        while True:
            # 1. Read the 2-byte Length (Big-Endian)
            len_bytes = f.read(2)
            if not len_bytes:
                break
            
            msg_len = struct.unpack('>H', len_bytes)[0]
            
            # 2. Read the full message payload
            payload = f.read(msg_len)
            if not payload:
                break
            
            msg_type = chr(payload[0])
            
            # 3. Parse different message types
            record = {'message_type': msg_type, 'raw_length': msg_len}
            
            try:
                if msg_type == 'T':  # Seconds Timestamp
                    if len(payload) >= 5:
                        seconds = struct.unpack('>I', payload[1:5])[0]
                        record['seconds'] = seconds
                        record['description'] = f"Timestamp: {seconds}s past midnight"
                
                elif msg_type == 'R':  # Stock Directory
                    if len(payload) >= 47:
                        symbol = payload[11:23].decode('ascii', errors='replace').strip()
                        market = payload[43:47].decode('ascii', errors='replace').strip()
                        record['symbol'] = symbol
                        record['market'] = market
                        record['description'] = f"Symbol: {symbol}, Market: {market}"
                
                elif msg_type == 'S':  # System Event
                    if len(payload) >= 18:
                        event_code = chr(payload[17])
                        record['event_code'] = event_code
                        record['description'] = f"System Event: {event_code}"
                
                elif msg_type == 'H':  # Trading Status
                    if len(payload) >= 21:
                        symbol = payload[11:23].decode('ascii', errors='replace').strip()
                        status = chr(payload[20])
                        record['symbol'] = symbol
                        record['status'] = status
                        record['description'] = f"Trading Status: {symbol} = {status}"
                
                elif msg_type == 'Y':  # Reg SHO
                    if len(payload) >= 20:
                        symbol = payload[11:23].decode('ascii', errors='replace').strip()
                        action = chr(payload[19])
                        record['symbol'] = symbol
                        record['action'] = action
                        record['description'] = f"Reg SHO: {symbol} = {action}"
                
                elif msg_type == 'L':  # IPO
                    if len(payload) >= 20:
                        symbol = payload[11:23].decode('ascii', errors='replace').strip()
                        record['symbol'] = symbol
                        record['description'] = f"IPO: {symbol}"
                
                elif msg_type == 'V':  # LULD
                    if len(payload) >= 35:
                        symbol = payload[11:23].decode('ascii', errors='replace').strip()
                        record['symbol'] = symbol
                        record['description'] = f"LULD: {symbol}"
                
                elif msg_type == 'W':  # IPO Quoting
                    if len(payload) >= 20:
                        symbol = payload[11:23].decode('ascii', errors='replace').strip()
                        record['symbol'] = symbol
                        record['description'] = f"IPO Quoting: {symbol}"
                
                elif msg_type == 'A':  # Add Order (PSE format: 30 bytes)
                    if len(payload) >= 30:
                        timestamp = struct.unpack('>I', payload[1:5])[0]
                        order_id = struct.unpack('>Q', payload[5:13])[0]
                        symbol = payload[13:21].decode('ascii', errors='replace').strip()
                        qty = struct.unpack('>I', payload[21:25])[0]
                        price = struct.unpack('>I', payload[25:29])[0]
                        side = chr(payload[29])
                        record['timestamp'] = timestamp
                        record['order_id'] = order_id
                        record['symbol'] = symbol
                        record['quantity'] = qty
                        record['price'] = price / 100  # PSE scale
                        record['side'] = side
                        record['description'] = f"Add Order: {symbol} {qty}@{price/100:.2f} {side}"
                
                elif msg_type == 'e':  # Order Executed (PSE format: 37 bytes typically)
                    if len(payload) >= 25:
                        timestamp = struct.unpack('>I', payload[1:5])[0]
                        order_id = struct.unpack('>Q', payload[5:13])[0]
                        qty = struct.unpack('>I', payload[13:17])[0]
                        price = struct.unpack('>I', payload[17:21])[0]
                        record['timestamp'] = timestamp
                        record['order_id'] = order_id
                        record['quantity'] = qty
                        record['price'] = price / 100  # PSE scale
                        record['description'] = f"Execute: {qty}@{price/100:.2f}"
                
                elif msg_type == 'E':  # Order Executed
                    if len(payload) >= 30:
                        order_id = struct.unpack('>Q', payload[11:19])[0]
                        qty = struct.unpack('>I', payload[19:23])[0]
                        price = struct.unpack('>I', payload[23:27])[0]
                        record['order_id'] = order_id
                        record['quantity'] = qty
                        record['price'] = price / 10000
                        record['description'] = f"Executed: {qty}@{price/10000:.2f}"
                
                elif msg_type == 'C':  # Order Executed (Partial)
                    if len(payload) >= 35:
                        order_id = struct.unpack('>Q', payload[11:19])[0]
                        qty = struct.unpack('>I', payload[19:23])[0]
                        price = struct.unpack('>I', payload[23:27])[0]
                        record['order_id'] = order_id
                        record['quantity'] = qty
                        record['price'] = price / 10000
                        record['description'] = f"Executed (Partial): {qty}@{price/10000:.2f}"
                
                elif msg_type == 'X':  # Cancel Order
                    if len(payload) >= 23:
                        order_id = struct.unpack('>Q', payload[11:19])[0]
                        qty = struct.unpack('>I', payload[19:23])[0]
                        record['order_id'] = order_id
                        record['quantity'] = qty
                        record['description'] = f"Cancel Order: -{qty}"
                
                elif msg_type == 'D':  # Delete Order (PSE format: 13 bytes)
                    if len(payload) >= 13:
                        timestamp = struct.unpack('>I', payload[1:5])[0]
                        order_id = struct.unpack('>Q', payload[5:13])[0]
                        record['timestamp'] = timestamp
                        record['order_id'] = order_id
                        record['quantity'] = 0
                        record['description'] = f"Delete Order: {order_id}"
                
                elif msg_type == 'U':  # Replace Order (PSE format)
                    if len(payload) >= 25:
                        timestamp = struct.unpack('>I', payload[1:5])[0]
                        old_order_id = struct.unpack('>Q', payload[5:13])[0]
                        new_order_id = struct.unpack('>Q', payload[13:21])[0]
                        qty = struct.unpack('>I', payload[21:25])[0]
                        record['timestamp'] = timestamp
                        record['old_order_id'] = old_order_id
                        record['order_id'] = new_order_id
                        record['quantity'] = qty
                        record['description'] = f"Replace Order: {old_order_id} -> {new_order_id} {qty}"
                
                elif msg_type == 'P':  # Trade (Non-Cross)
                    if len(payload) >= 43:
                        order_id = struct.unpack('>Q', payload[11:19])[0]
                        qty = struct.unpack('>I', payload[19:23])[0]
                        symbol = payload[23:35].decode('ascii', errors='replace').strip()
                        price = struct.unpack('>I', payload[35:39])[0]
                        buyer_order_id = struct.unpack('>Q', payload[39:47])[0]
                        record['order_id'] = order_id
                        record['quantity'] = qty
                        record['symbol'] = symbol
                        record['price'] = price / 10000
                        record['buyer_order_id'] = buyer_order_id
                        record['description'] = f"Trade: {symbol} {qty}@{price/10000:.2f}"
                
                elif msg_type == 'Q':  # Trade (Cross)
                    if len(payload) >= 43:
                        qty = struct.unpack('>I', payload[11:15])[0]
                        symbol = payload[15:27].decode('ascii', errors='replace').strip()
                        price = struct.unpack('>I', payload[27:31])[0]
                        record['quantity'] = qty
                        record['symbol'] = symbol
                        record['price'] = price / 10000
                        record['description'] = f"Cross Trade: {symbol} {qty}@{price/10000:.2f}"
                
                elif msg_type == 'B':  # Broken Trade
                    if len(payload) >= 19:
                        order_id = struct.unpack('>Q', payload[11:19])[0]
                        record['order_id'] = order_id
                        record['description'] = f"Broken Trade: {order_id}"
                
                elif msg_type == 'A':  # NOII
                    if len(payload) >= 49:
                        pairing_qty = struct.unpack('>Q', payload[11:19])[0]
                        imbalance_qty = struct.unpack('>Q', payload[19:27])[0]
                        imbalance_side = chr(payload[27])
                        symbol = payload[28:40].decode('ascii', errors='replace').strip()
                        far_price = struct.unpack('>I', payload[40:44])[0]
                        near_price = struct.unpack('>I', payload[44:48])[0]
                        record['pairing_qty'] = pairing_qty
                        record['imbalance_qty'] = imbalance_qty
                        record['imbalance_side'] = imbalance_side
                        record['symbol'] = symbol
                        record['far_price'] = far_price / 10000
                        record['near_price'] = near_price / 10000
                        record['description'] = f"NOII: {symbol} Imbalance: {imbalance_qty} {imbalance_side}"
                
                records.append(record)
            
            except Exception as e:
                record['error'] = str(e)
                records.append(record)
    
    # Write to CSV
    if records:
        fieldnames = set()
        for record in records:
            fieldnames.update(record.keys())
        fieldnames = sorted(list(fieldnames))
        
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for record in records:
                writer.writerow(record)
        
        print(f"✅ Wrote {len(records)} records to {output_csv}")
        print(f"   Message types found: {sorted(set(r.get('message_type') for r in records))}")
        return records
    else:
        print("❌ No records found")
        return []


if __name__ == '__main__':
    # Parse both files
    print("Parsing ITCH files...")
    print()
    
    print("1. Parsing ITCHINDEX file...")
    records1 = parse_itch(
        '/Users/danielum/Documents/repos/itch-parser/data/ipxs-ipxs1-ITCHINDEX-1704668548.log',
        '/Users/danielum/Documents/repos/itch-parser/output_index.csv'
    )
    
    print()
    print("2. Parsing ITCHTV file...")
    records2 = parse_itch(
        '/Users/danielum/Documents/repos/itch-parser/data/ipxs-ipxs5-ITCHTV-1704668548.log',
        '/Users/danielum/Documents/repos/itch-parser/output_tv.csv'
    )
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"ITCHINDEX records: {len(records1)}")
    print(f"ITCHTV records: {len(records2)}")
    print(f"Total: {len(records1) + len(records2)}")
    print()
    print("Output files:")
    print("  - output_index.csv")
    print("  - output_tv.csv")
