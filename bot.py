import ccxt
import pandas as pd
import pandas_ta as ta
import requests
import time
from datetime import datetime
import pytz

# --- ⚙️ CONFIGURATION ---
TELEGRAM_TOKEN = '8506498777:AAF3ui-xPOgbBe20-DRvGCj_HiN7c0uawjw'
TELEGRAM_CHAT_ID = '6088825847'

# ✅ BINANCE SETUP WITH 451 ERROR BYPASS
future_ex = ccxt.binance({
    'options': {'defaultType': 'future'}, 
    'enableRateLimit': True,
    'urls': {
        'api': {
            'public': 'https://api1.binance.com/api/v3',
            'private': 'https://api1.binance.com/api/v3',
        },
        'fapiPublic': 'https://fapi.binance.com/fapi/v1',
        'fapiPrivate': 'https://fapi.binance.com/fapi/v1',
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
    """Sirf active USDT futures pairs nikalta hai"""
    symbols = []
    try:
        markets = future_ex.load_markets()
        for s, m in markets.items():
            if m.get('active', True) and '/USDT' in s and s.endswith(':USDT'):
                symbols.append(s)
    except Exception as e:
        print(f"Error fetching markets: {e}")
    return symbols

def check_ema_crossover(symbol, tf):
    """Fetch data aur check karta hai ke kya latest closed candle EMA 200 ke upar aayi hai"""
    try:
        # Limit 210 rakhi hai taake EMA 200 properly calculate ho sake
        bars = future_ex.fetch_ohlcv(symbol, timeframe=tf, limit=210)
        if not bars or len(bars) < 200:
            return False, 0
            
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['ema200'] = ta.ema(df['close'], length=200)
        
        # ccxt mein iloc[-1] current (chalti hui) candle hoti hai, isliye hum closed candles check karenge
        curr_candle = df.iloc[-2] # Last fully closed candle
        prev_candle = df.iloc[-3] # Us se peechli candle
        
        # Condition: Pehli candle EMA se niche thi, aur latest closed candle EMA ke upar close hui
        if prev_candle['close'] <= prev_candle['ema200'] and curr_candle['close'] > curr_candle['ema200']:
            return True, curr_candle['close']
            
        return False, 0
    except Exception as e:
        # Error aane par chup chap skip kar dega, crash nahi hoga
        return False, 0

# --- MASTER LOOP ---
if __name__ == "__main__":
    start_msg = f"🚀 *EMA 200 Scanner Online*\n🕒 *PST:* {get_pkt_now()}\n⚙️ *Mode:* 100 Coins Batch -> 10m Sleep"
    print(start_msg)
    send_telegram(start_msg)
    
    CHUNK_SIZE = 100
    SLEEP_AFTER_CHUNK = 600 # 10 Minutes (in seconds)
    
    while True:
        try:
            print("Fetching active futures markets...")
            all_symbols = get_active_futures()
            
            if not all_symbols:
                time.sleep(60)
                continue
                
            total_coins = len(all_symbols)
            print(f"Total coins found: {total_coins}. Starting scan...")
            
            # List ko 100-100 ke hissay mein todna
            for i in range(0, total_coins, CHUNK_SIZE):
                chunk = all_symbols[i : i + CHUNK_SIZE]
                print(f"Scanning chunk {i+1} to {i+len(chunk)}...")
                
                for symbol in chunk:
                    # 1. Check 4-Hour Timeframe
                    is_bullish_4h, close_price_4h = check_ema_crossover(symbol, '4h')
                    if is_bullish_4h:
                        clean_sym = symbol.replace(':USDT', '')
                        msg = f"🚀 *BULLISH SIGNAL* 🚀\n🪙 *Coin:* {clean_sym}\n⏰ *TF:* 4-Hour (4h)\n📈 *Logic:* Candle Closed ABOVE EMA 200\n💲 *Price:* {close_price_4h}\n🕒 *Time:* {get_pkt_now()}"
                        send_telegram(msg)
                    
                    time.sleep(0.5) # API Rate limit safe rakhne ke liye halka sa pause
                    
                    # 2. Check 1-Hour Timeframe
                    is_bullish_1h, close_price_1h = check_ema_crossover(symbol, '1h')
                    if is_bullish_1h:
                        clean_sym = symbol.replace(':USDT', '')
                        msg = f"🚀 *BULLISH SIGNAL* 🚀\n🪙 *Coin:* {clean_sym}\n⏰ *TF:* 1-Hour (1h)\n📈 *Logic:* Candle Closed ABOVE EMA 200\n💲 *Price:* {close_price_1h}\n🕒 *Time:* {get_pkt_now()}"
                        send_telegram(msg)
                        
                    time.sleep(0.5) # API Rate limit safe rakhne ke liye halka sa pause
                
                # Ek batch (100 coins) complete hone ke baad 10 minutes (600s) ka sleep
                print(f"Chunk completed. Sleeping for {SLEEP_AFTER_CHUNK/60} minutes...")
                time.sleep(SLEEP_AFTER_CHUNK)
                
            print("All coins scanned. Restarting master loop...")
            
        except Exception as e:
            error_msg = f"⚠️ Main Loop Error: {e}\nRestarting in 60s..."
            print(error_msg)
            time.sleep(60) # Agar koi bara masla aye toh 1 minute baad khud restart hoga