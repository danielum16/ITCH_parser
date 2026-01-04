#!/usr/bin/env python3
"""
Bare-bons Level 2 Order Book Builder

Instead of maintaining a full order book in memory, 
just extract order and execute messages and output them directly.
"""

import csv
from collections import defaultdict

def build_level2_simple(input_csv, output_csv):
    """Extract order book relevant messages directly"""
    
    print(f"Reading {input_csv}...")
    
    # Track current orders by ID
    orders = {}  # order_id -> {symbol, side, price, qty}
    
    # Track aggregated level 2 by ticker/time
    snapshots_by_ticker = defaultdict(list)  # ticker -> list of {timestamp, bids, asks}
    
    msg_count = 0
    
    with open(input_csv, 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            msg_count += 1
            if msg_count % 50000 == 0:
                print(f"  Processed {msg_count:,} messages...")
            
            msg_type = row.get('message_type')
            
            # Type A: Add Order
            if msg_type == 'A':
                order_id = row.get('order_id')
                symbol = row.get('symbol', '').strip()
                side = row.get('side', 'B').strip()
                price_str = row.get('price', '0')
                qty_str = row.get('quantity', '0')
                timestamp = row.get('timestamp', row.get('seconds', '0'))
                
                try:
                    if order_id and symbol:
                        orders[order_id] = {
                            'symbol': symbol,
                            'side': side,
                            'price': float(price_str) if price_str else 0,
                            'qty': int(qty_str) if qty_str else 0,
                            'timestamp': int(timestamp) if timestamp else 0
                        }
                except (ValueError, TypeError):
                    pass
            
            # Type e: Execute Order
            elif msg_type == 'e':
                order_id = row.get('order_id')
                exec_qty_str = row.get('quantity', '0')
                
                try:
                    if order_id in orders:
                        exec_qty = int(exec_qty_str) if exec_qty_str else 0
                        orders[order_id]['qty'] -= exec_qty
                        if orders[order_id]['qty'] <= 0:
                            del orders[order_id]
                except (ValueError, TypeError):
                    pass
            
            # Type D: Delete Order
            elif msg_type == 'D':
                order_id = row.get('order_id')
                if order_id and order_id in orders:
                    del orders[order_id]
            
            # Type U: Replace Order
            elif msg_type == 'U':
                old_id = row.get('old_order_id')
                new_id = row.get('order_id')
                new_qty_str = row.get('quantity', '0')
                new_price_str = row.get('price', '0')
                
                try:
                    if old_id in orders:
                        old_order = orders[old_id]
                        del orders[old_id]
                        
                        orders[new_id] = {
                            'symbol': old_order['symbol'],
                            'side': old_order['side'],
                            'price': float(new_price_str) if new_price_str and new_price_str != '0' else old_order['price'],
                            'qty': int(new_qty_str) if new_qty_str else old_order['qty'],
                            'timestamp': old_order['timestamp']
                        }
                except (ValueError, TypeError, KeyError):
                    pass
            
            # Type T: Timestamp - snapshot the order book
            elif msg_type == 'T':
                timestamp = row.get('seconds', '0')
                
                # Group by ticker
                tickers = defaultdict(lambda: {'bids': {}, 'asks': {}})
                for order_id, order in orders.items():
                    ticker = order['symbol']
                    price = order['price']
                    qty = order['qty']
                    
                    if order['side'] == 'B':
                        tickers[ticker]['bids'][price] = tickers[ticker]['bids'].get(price, 0) + qty
                    else:
                        tickers[ticker]['asks'][price] = tickers[ticker]['asks'].get(price, 0) + qty
                
                # Store snapshots for this timestamp
                for ticker, levels in tickers.items():
                    bid_prices = sorted(levels['bids'].keys(), reverse=True)[:5]
                    ask_prices = sorted(levels['asks'].keys())[:5]
                    
                    bid_data = {bid_prices[i]: levels['bids'][bid_prices[i]] for i in range(len(bid_prices))}
                    ask_data = {ask_prices[i]: levels['asks'][ask_prices[i]] for i in range(len(ask_prices))}
                    
                    snapshots_by_ticker[ticker].append({
                        'timestamp': timestamp,
                        'bids': bid_data,
                        'asks': ask_data
                    })
    
    # Write to CSV
    print(f"\n✅ Processed {msg_count:,} messages")
    print(f"   Order book has {len(orders):,} active orders")
    print(f"   Captured {len(snapshots_by_ticker)} tickers in snapshots")
    
    # Write Level 2 snapshots
    with open(output_csv, 'w', newline='') as f:
        fieldnames = ['ticker', 'timestamp', 
                     'bid_1_price', 'bid_1_qty', 'bid_2_price', 'bid_2_qty',
                     'bid_3_price', 'bid_3_qty', 'bid_4_price', 'bid_4_qty',
                     'bid_5_price', 'bid_5_qty',
                     'ask_1_price', 'ask_1_qty', 'ask_2_price', 'ask_2_qty',
                     'ask_3_price', 'ask_3_qty', 'ask_4_price', 'ask_4_qty',
                     'ask_5_price', 'ask_5_qty']
        
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        snapshot_count = 0
        for ticker, snapshots in sorted(snapshots_by_ticker.items()):
            for snap in snapshots:
                row_data = {'ticker': ticker, 'timestamp': snap['timestamp']}
                
                # Fill in bid levels
                bid_prices = sorted(snap['bids'].keys(), reverse=True)
                for i in range(5):
                    if i < len(bid_prices):
                        price = bid_prices[i]
                        row_data[f'bid_{i+1}_price'] = f"{price:.2f}"
                        row_data[f'bid_{i+1}_qty'] = snap['bids'][price]
                    else:
                        row_data[f'bid_{i+1}_price'] = ''
                        row_data[f'bid_{i+1}_qty'] = ''
                
                # Fill in ask levels
                ask_prices = sorted(snap['asks'].keys())
                for i in range(5):
                    if i < len(ask_prices):
                        price = ask_prices[i]
                        row_data[f'ask_{i+1}_price'] = f"{price:.2f}"
                        row_data[f'ask_{i+1}_qty'] = snap['asks'][price]
                    else:
                        row_data[f'ask_{i+1}_price'] = ''
                        row_data[f'ask_{i+1}_qty'] = ''
                
                writer.writerow(row_data)
                snapshot_count += 1
        
        print(f"\n✅ Wrote {snapshot_count:,} Level 2 snapshots to {output_csv}")

if __name__ == '__main__':
    build_level2_simple(
        '/Users/danielum/Documents/repos/itch-parser/output_tv.csv',
        '/Users/danielum/Documents/repos/itch-parser/level2_data.csv'
    )
