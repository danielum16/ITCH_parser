# How to Build Level 2 Order Book Data from ITCH Messages

## Overview: From Raw Messages → Level 2 Data

Level 2 data shows the order book at specific points in time:
```
Ticker: BDO
Timestamp: 10:30:45.123
BID SIDE (5 levels)          ASK SIDE (5 levels)
Price    Volume              Price    Volume
------   -------              ------   -------
90.50    5,000                90.75    3,000
90.25    8,000                91.00    6,000
90.00    12,000               91.25    4,500
89.75    3,500                91.50    2,000
89.50    1,200                92.00    1,000
```

## Step 1: Extract Order Book Building Messages

From `output_tv.csv`, use these message types:

| Type | Message | Use For |
|------|---------|---------|
| **A** | Add Order | Add to order book |
| **U** | Replace Order | Update order quantity/price |
| **D** | Delete Order | Remove from order book |
| **e** | Execution | Reduce order quantity |
| **X** | Cancel Order | Remove/reduce order |

## Step 2: Track Orders in Memory

Build a data structure per ticker:

```python
order_book = {
    'BDO': {
        'orders': {
            12345: {'side': 'B', 'price': 9050, 'qty': 5000},  # Buy at 90.50
            12346: {'side': 'S', 'price': 9075, 'qty': 3000},  # Sell at 90.75
            12347: {'side': 'B', 'price': 9025, 'qty': 8000},
            # ... more orders
        },
        'last_update': '10:30:45.123'
    }
}
```

## Step 3: Aggregate by Price Level

Group orders by price and side:

```python
def build_level2(order_book, ticker, timestamp):
    """Build Level 2 from order book"""
    orders = order_book[ticker]['orders']
    
    # Group by side and price
    bids = {}  # price -> total_qty
    asks = {}  # price -> total_qty
    
    for order_id, order in orders.items():
        price = order['price']
        qty = order['qty']
        
        if order['side'] == 'B':  # Buy
            bids[price] = bids.get(price, 0) + qty
        else:  # Sell
            asks[price] = asks.get(price, 0) + qty
    
    # Sort and limit to top 5 levels
    bid_levels = sorted(bids.items(), reverse=True)[:5]
    ask_levels = sorted(asks.items())[:5]
    
    return {
        'ticker': ticker,
        'timestamp': timestamp,
        'bids': bid_levels,  # [(price, qty), ...]
        'asks': ask_levels,  # [(price, qty), ...]
    }
```

## Step 4: Output to CSV

Create a Level 2 CSV with this structure:

```
ticker,timestamp,bid_price_1,bid_qty_1,bid_price_2,bid_qty_2,...,ask_price_1,ask_qty_1,ask_price_2,ask_qty_2,...
BDO,10:30:45.123,9050,5000,9025,8000,9000,12000,8975,3500,8950,1200,9075,3000,9100,6000,9125,4500,9150,2000,9200,1000
ALI,10:30:45.124,25.50,100000,25.25,50000,...,25.75,75000,26.00,80000,...
```

---

## Complete Implementation

```python
import csv
from collections import defaultdict
from datetime import datetime

class OrderBook:
    def __init__(self):
        self.orders = {}  # order_id -> {side, price, qty, symbol, timestamp}
        self.order_id_to_symbol = {}  # order_id -> symbol
    
    def add_order(self, order_id, symbol, side, price, qty, timestamp):
        """Type A: Add Order"""
        self.orders[order_id] = {
            'symbol': symbol,
            'side': side,
            'price': price,
            'qty': qty,
            'timestamp': timestamp
        }
        self.order_id_to_symbol[order_id] = symbol
    
    def execute_order(self, order_id, exec_qty, timestamp):
        """Type e/E: Execution - reduce quantity"""
        if order_id in self.orders:
            self.orders[order_id]['qty'] -= exec_qty
            if self.orders[order_id]['qty'] <= 0:
                del self.orders[order_id]
    
    def delete_order(self, order_id, timestamp):
        """Type D/X: Delete Order"""
        if order_id in self.orders:
            del self.orders[order_id]
    
    def replace_order(self, old_order_id, new_order_id, new_qty, new_price, timestamp):
        """Type U: Replace Order"""
        if old_order_id in self.orders:
            order = self.orders[old_order_id]
            del self.orders[old_order_id]
            self.orders[new_order_id] = {
                'symbol': order['symbol'],
                'side': order['side'],
                'price': new_price if new_price else order['price'],
                'qty': new_qty if new_qty else order['qty'],
                'timestamp': timestamp
            }
    
    def get_level2(self, ticker):
        """Build Level 2 snapshot for a ticker"""
        bids = defaultdict(int)
        asks = defaultdict(int)
        
        for order_id, order in self.orders.items():
            if order['symbol'] != ticker:
                continue
            
            price = order['price']
            qty = order['qty']
            
            if order['side'] == 'B':
                bids[price] += qty
            else:
                asks[price] += qty
        
        # Sort and get top 5 levels
        bid_levels = sorted(bids.items(), key=lambda x: x[0], reverse=True)[:5]
        ask_levels = sorted(asks.items(), key=lambda x: x[0])[:5]
        
        return {
            'bids': bid_levels,
            'asks': ask_levels
        }

def build_level2_from_csv(input_csv, output_csv, snapshot_interval_ms=1000):
    """
    Build Level 2 data from ITCH messages
    
    Args:
        input_csv: output_tv.csv from simple_parser
        output_csv: Level 2 output file
        snapshot_interval_ms: Take snapshot every N milliseconds
    """
    
    order_book = OrderBook()
    level2_snapshots = []
    last_snapshot_time = {}  # ticker -> last_snapshot_timestamp
    
    with open(input_csv, 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            msg_type = row.get('message_type', '')
            timestamp = row.get('description', '')
            
            # Extract fields based on message type
            if msg_type == 'A':  # Add Order
                order_id = int(row.get('order_id', 0)) if row.get('order_id') else 0
                symbol = row.get('symbol', '')
                side = row.get('side', '')
                price = int(float(row.get('price', 0)) * 10000) if row.get('price') else 0
                qty = int(row.get('quantity', 0)) if row.get('quantity') else 0
                
                if order_id and symbol:
                    order_book.add_order(order_id, symbol, side, price, qty, timestamp)
            
            elif msg_type == 'e':  # Execution
                order_id = int(row.get('order_id', 0)) if row.get('order_id') else 0
                qty = int(row.get('quantity', 0)) if row.get('quantity') else 0
                
                if order_id:
                    order_book.execute_order(order_id, qty, timestamp)
            
            elif msg_type == 'D':  # Delete Order
                order_id = int(row.get('order_id', 0)) if row.get('order_id') else 0
                
                if order_id:
                    order_book.delete_order(order_id, timestamp)
            
            elif msg_type == 'U':  # Replace Order
                old_id = int(row.get('old_order_id', 0)) if row.get('old_order_id') else 0
                new_id = int(row.get('new_order_id', 0)) if row.get('new_order_id') else 0
                qty = int(row.get('quantity', 0)) if row.get('quantity') else 0
                price = int(float(row.get('price', 0)) * 10000) if row.get('price') else 0
                
                if old_id and new_id:
                    order_book.replace_order(old_id, new_id, qty, price, timestamp)
            
            elif msg_type == 'T':  # Timestamp - good time to take snapshot
                # Take Level 2 snapshot for all active tickers
                active_tickers = set()
                for order in order_book.orders.values():
                    active_tickers.add(order['symbol'])
                
                for ticker in active_tickers:
                    # Take snapshot at timestamp intervals
                    if ticker not in last_snapshot_time:
                        last_snapshot_time[ticker] = timestamp
                    
                    level2 = order_book.get_level2(ticker)
                    level2_snapshots.append({
                        'ticker': ticker,
                        'timestamp': timestamp,
                        'bid_1_price': level2['bids'][0][0] / 10000 if len(level2['bids']) > 0 else '',
                        'bid_1_qty': level2['bids'][0][1] if len(level2['bids']) > 0 else '',
                        'bid_2_price': level2['bids'][1][0] / 10000 if len(level2['bids']) > 1 else '',
                        'bid_2_qty': level2['bids'][1][1] if len(level2['bids']) > 1 else '',
                        'bid_3_price': level2['bids'][2][0] / 10000 if len(level2['bids']) > 2 else '',
                        'bid_3_qty': level2['bids'][2][1] if len(level2['bids']) > 2 else '',
                        'bid_4_price': level2['bids'][3][0] / 10000 if len(level2['bids']) > 3 else '',
                        'bid_4_qty': level2['bids'][3][1] if len(level2['bids']) > 3 else '',
                        'bid_5_price': level2['bids'][4][0] / 10000 if len(level2['bids']) > 4 else '',
                        'bid_5_qty': level2['bids'][4][1] if len(level2['bids']) > 4 else '',
                        'ask_1_price': level2['asks'][0][0] / 10000 if len(level2['asks']) > 0 else '',
                        'ask_1_qty': level2['asks'][0][1] if len(level2['asks']) > 0 else '',
                        'ask_2_price': level2['asks'][1][0] / 10000 if len(level2['asks']) > 1 else '',
                        'ask_2_qty': level2['asks'][1][1] if len(level2['asks']) > 1 else '',
                        'ask_3_price': level2['asks'][2][0] / 10000 if len(level2['asks']) > 2 else '',
                        'ask_3_qty': level2['asks'][2][1] if len(level2['asks']) > 2 else '',
                        'ask_4_price': level2['asks'][3][0] / 10000 if len(level2['asks']) > 3 else '',
                        'ask_4_qty': level2['asks'][3][1] if len(level2['asks']) > 3 else '',
                        'ask_5_price': level2['asks'][4][0] / 10000 if len(level2['asks']) > 4 else '',
                        'ask_5_qty': level2['asks'][4][1] if len(level2['asks']) > 4 else '',
                    })
    
    # Write to CSV
    if level2_snapshots:
        fieldnames = list(level2_snapshots[0].keys())
        with open(output_csv, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(level2_snapshots)
        
        print(f"✅ Built {len(level2_snapshots)} Level 2 snapshots")
        print(f"   Output: {output_csv}")
    else:
        print("❌ No Level 2 snapshots created")

if __name__ == '__main__':
    build_level2_from_csv(
        '/Users/danielum/Documents/repos/itch-parser/output_tv.csv',
        '/Users/danielum/Documents/repos/itch-parser/level2_data.csv'
    )
```

---

## Run It

Save the above as `build_level2.py` and run:

```bash
python3 build_level2.py
```

This will create **level2_data.csv** with:
- Ticker
- Timestamp
- Top 5 bid prices and volumes
- Top 5 ask prices and volumes

---

## Alternative: Real-time Streaming

For live data, you'd do this in a loop:

```python
def stream_level2(input_csv, output_file):
    """Stream Level 2 updates as they happen"""
    order_book = OrderBook()
    
    with open(input_csv) as f, open(output_file, 'w') as out:
        reader = csv.DictReader(f)
        writer = None
        
        for row in reader:
            # Update order book
            process_message(order_book, row)
            
            # Output Level 2 on every timestamp message
            if row['message_type'] == 'T':
                for ticker in get_active_tickers(order_book):
                    level2 = order_book.get_level2(ticker)
                    if writer is None:
                        writer = csv.DictWriter(out, fieldnames=get_fieldnames())
                        writer.writeheader()
                    writer.writerow(format_level2(ticker, row, level2))
                    out.flush()
```

---

## Summary

**CSV Files → Level 2:**

1. Read `output_tv.csv` messages sequentially
2. Maintain an in-memory order book by ticker
3. Update it with A/U/D/e messages
4. At timestamps (or fixed intervals), aggregate orders by price level
5. Output to CSV with bid/ask columns
