import ccxt
import pandas as pd
import requests
import time
from datetime import datetime
import pytz

# --- CONFIG ---
TELEGRAM_TOKEN = '8506498777:AAF3ui-xPOgbBe20-DRvGCj_HiN7c0uawjw'
TELEGRAM_CHAT_ID = '6088825847'

future_ex = ccxt.binance({
    'options': {'defaultType': 'future'}, 
    'enableRateLimit': True,
    'urls': {'api': {'public': 'https://api1.binance.com/api/v3'}}
})

pkt_timezone = pytz.timezone('Asia/Karachi')

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def check_ema_crossover(symbol, tf):
    try:
        bars = future_ex.fetch_ohlcv(symbol, timeframe=tf, limit=250)
        if not bars or len(bars) < 210: return False, 0
        df = pd.DataFrame(bars, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        # Manual EMA Calculation
        df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()
        curr, prev = df.iloc[-2], df.iloc[-3]
        if prev['close'] <= prev['ema200'] and curr['close'] > curr['ema200']:
            return True, curr['close']
        return False, 0
    except: return False, 0

if __name__ == "__main__":
    send_telegram(f"✅ *EMA Bot Online (Clean Mode)*")
    while True:
        try:
            markets = future_ex.load_markets()
            symbols = [s for s, m in markets.items() if '/USDT' in s and s.endswith(':USDT')]
            
            for i in range(0, len(symbols), 100):
                chunk = symbols[i : i + 100]
                for s in chunk:
                    for tf in ['4h', '1h']:
                        is_bull, price = check_ema_crossover(s, tf)
                        if is_bull:
                            send_telegram(f"🚀 *BULLISH:* {s.replace(':USDT','')}\n⏰ *TF:* {tf}\n💲 *Price:* {price}")
                        time.sleep(0.5)
                time.sleep(600) # 10m sleep after 100 coins
        except: time.sleep(60)
