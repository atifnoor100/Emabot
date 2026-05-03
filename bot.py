import ccxt
import pandas as pd
import requests
import time
from datetime import datetime
import pytz

# --- ⚙️ CONFIGURATION ---
TELEGRAM_TOKEN = '8506498777:AAF3ui-xPOgbBe20-DRvGCj_HiN7c0uawjw'
TELEGRAM_CHAT_ID = '6088825847'

future_ex = ccxt.binance({
    'options': {'defaultType': 'future'}, 
    'enableRateLimit': True,
    'urls': {
        'api': {
            'public': 'https://api1.binance.com/api/v3',
            'private': 'https://api1.binance.com/api/v3',
        }
    }
})

pkt_timezone = pytz.timezone('Asia/Karachi')

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def get_pkt_now():
    return datetime.now(pkt_timezone).strftime('%d-%m-%Y | %I:%M:%S %p')

def calculate_ema(data, window):
    """Pandas use karke khud EMA calculate karna (No pandas_ta required)"""
    return data.ewm(span=window, adjust=False).mean()

def get_active_futures():
    symbols = []
    try:
        markets = future_ex.load_markets()
        for s, m in markets.items():
            if m.get('active', True) and '/USDT' in s and s.endswith(':USDT'):
                symbols.append(s)
    except: pass
    return symbols

def check_ema_crossover(symbol, tf):
    try:
        bars = future_ex.fetch_ohlcv(symbol, timeframe=tf, limit=250)
        if not bars or len(bars) < 210: return False, 0
            
        df = pd.DataFrame(bars, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        # Manual EMA calculation
        df['ema200'] = calculate_ema(df['close'], 200)
        
        curr, prev = df.iloc[-2], df.iloc[-3]
        
        if prev['close'] <= prev['ema200'] and curr['close'] > curr['ema200']:
            return True, curr['close']
        return False, 0
    except: return False, 0

if __name__ == "__main__":
    send_telegram(f"🚀 *EMA 200 Scanner Re-Started*\n📍 *Status:* Library Dependency Removed\n🕒 *PST:* {get_pkt_now()}")
    
    CHUNK_SIZE = 100
    SLEEP_AFTER_CHUNK = 600 
    
    while True:
        try:
            all_symbols = get_active_futures()
            if not all_symbols:
                time.sleep(60); continue
                
            for i in range(0, len(all_symbols), CHUNK_SIZE):
                chunk = all_symbols[i : i + CHUNK_SIZE]
                for symbol in chunk:
                    # Check 4h and 1h
                    for tf in ['4h', '1h']:
                        is_bull, price = check_ema_crossover(symbol, tf)
                        if is_bull:
                            clean_sym = symbol.replace(':USDT', '')
                            send_telegram(f"🚀 *BULLISH SIGNAL*\n🪙 *Coin:* {clean_sym}\n⏰ *TF:* {tf}\n📈 *Logic:* Price > EMA 200\n💲 *Price:* {price}")
                        time.sleep(0.5)
                
                print(f"Batch completed. Sleeping 10m...")
                time.sleep(SLEEP_AFTER_CHUNK)
        except:
            time.sleep(60)
