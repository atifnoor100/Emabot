import ccxt
import pandas as pd
import requests
import time
from datetime import datetime
import pytz

# --- ⚙️ CONFIGURATION ---
TELEGRAM_TOKEN = '8506498777:AAF3ui-xPOgbBe20-DRvGCj_HiN7c0uawjw'
TELEGRAM_CHAT_ID = '6088825847'

# ✅ BINANCE BYPASS SETUP
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
        # Fetch 250 candles to calculate EMA 200 accurately
        bars = future_ex.fetch_ohlcv(symbol, timeframe=tf, limit=250)
        if not bars or len(bars) < 210: return False, 0
            
        df = pd.DataFrame(bars, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        
        # ✅ MANUAL EMA CALCULATION (No extra library needed)
        df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
        
        curr_candle = df.iloc[-2]  # Last closed
        prev_candle = df.iloc[-3]  # Previous closed
        
        # Bullish Crossover: Niche se upar close hona
        if prev_candle['close'] <= prev_candle['ema200'] and curr_candle['close'] > curr_candle['ema200']:
            return True, curr_candle['close']
            
        return False, 0
    except:
        return False, 0

# --- MAIN ENGINE ---
if __name__ == "__main__":
    msg = f"✅ *EMA 200 Scanner Online*\n📍 *Status:* Crash-Proof Mode Active\n🕒 *Time:* {get_pkt_now()}"
    print(msg)
    send_telegram(msg)
    
    CHUNK_SIZE = 100
    SLEEP_TIME = 600 # 10 Minutes
    
    while True:
        try:
            all_symbols = get_active_futures()
            if not all_symbols:
                time.sleep(60); continue
            
            for i in range(0, len(all_symbols), CHUNK_SIZE):
                chunk = all_symbols[i : i + CHUNK_SIZE]
                
                for symbol in chunk:
                    # Check for 4h and 1h
                    for tf in ['4h', '1h']:
                        is_bullish, price = check_ema_crossover(symbol, tf)
                        if is_bullish:
                            clean_name = symbol.replace(':USDT', '')
                            alert = f"🚀 *EMA 200 BULLISH*\n🪙 *Coin:* {clean_name}\n⏰ *TF:* {tf}\n📈 *Signal:* Price Closed Above EMA 200\n💲 *Price:* {price}\n🕒 {get_pkt_now()}"
                            send_telegram(alert)
                        time.sleep(0.5) # Anti-ban delay
                
                print(f"Batch Done. Rest for 10m...")
                time.sleep(SLEEP_TIME)
                
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(60)
