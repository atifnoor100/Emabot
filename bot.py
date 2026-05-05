import ccxt
import pandas as pd
import requests
import time
from datetime import datetime
import pytz

# --- ⚙️ CONFIGURATION ---
TELEGRAM_TOKEN = '8506498777:AAF3ui-xPOgbBe20-DRvGCj_HiN7c0uawjw'
TELEGRAM_CHAT_ID = '6088825847'

# ✅ BINANCE SETUP
future_ex = ccxt.binance({
    'options': {'defaultType': 'future'}, 
    'enableRateLimit': True,
    'urls': {'api': {'public': 'https://api1.binance.com/api/v3'}}
})

pkt_timezone = pytz.timezone('Asia/Karachi')
# Memory to track signals: { 'BTC/USDT': {'rsi_4h': timestamp, 'ema_4h': timestamp} }
signal_tracker = {}

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"}, timeout=10)
    except: pass

def get_pkt_now():
    return datetime.now(pkt_timezone).strftime('%d-%m-%Y | %I:%M:%S %p')

def calculate_rsi_wilders(series, period=14):
    """
    Wilder's Smoothing RSI - Exactly matches TradingView and Binance RSI.
    """
    delta = series.diff()
    # Wilder's smoothing alpha = 1/period
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_top_100_gainers():
    try:
        tickers = future_ex.fetch_tickers()
        active_gainers = []
        for symbol, data in tickers.items():
            if '/USDT' in symbol and symbol.endswith(':USDT'):
                if data.get('percentage') is not None:
                    active_gainers.append({'symbol': symbol, 'change': data['percentage']})
        
        # Sort by 24h gain
        sorted_gainers = sorted(active_gainers, key=lambda x: x['change'], reverse=True)
        return [x['symbol'] for x in sorted_gainers[:100]]
    except Exception as e:
        print(f"Error fetching tickers: {e}")
        return []

def analyze_coin(symbol):
    global signal_tracker
    try:
        # --- 4-HOUR TIMEFRAME SCAN ---
        # Fetch 300 candles to ensure Wilder's RSI 'warm-up' is accurate
        bars_4h = future_ex.fetch_ohlcv(symbol, timeframe='4h', limit=300)
        
        # Validation: Skip if data is not enough (No crash)
        if not bars_4h or len(bars_4h) < 250:
            return

        df_4h = pd.DataFrame(bars_4h, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
        
        # RSI Calculation (Wilder's 14)
        df_4h['rsi'] = calculate_rsi_wilders(df_4h['close'], 14)
        # EMA Calculation
        df_4h['ema200'] = df_4h['close'].ewm(span=200, adjust=False).mean()
        
        curr_4h = df_4h.iloc[-1]   # Live candle
        prev_4h = df_4h.iloc[-2]   # Last closed candle
        prev2_4h = df_4h.iloc[-3]  # 2nd last closed candle
        
        clean_name = symbol.replace(':USDT', '')
        if symbol not in signal_tracker:
            signal_tracker[symbol] = {}

        # 🎯 1. RSI 68 Breakout (Real-time)
        if prev_4h['rsi'] <= 68 and curr_4h['rsi'] > 68:
            # Send signal if not already sent for this 4h candle
            if signal_tracker[symbol].get('rsi_4h') != curr_4h['ts']:
                msg = f"⚡ *RSI BREAKOUT (4H)* ⚡\n🪙 *Coin:* {clean_name}\n📈 *RSI:* {round(curr_4h['rsi'], 2)}\n💲 *Price:* {curr_4h['close']}\n🕒 {get_pkt_now()}"
                send_telegram(msg)
                signal_tracker[symbol]['rsi_4h'] = curr_4h['ts']

        # 🎯 2. EMA 200 Crossover (4H - Closed Candle)
        if prev2_4h['close'] <= prev2_4h['ema200'] and prev_4h['close'] > prev_4h['ema200']:
            if signal_tracker[symbol].get('ema_4h') != prev_4h['ts']:
                msg = f"🟢 *EMA 200 BULLISH (4H)* 🟢\n🪙 *Coin:* {clean_name}\n📊 *Status:* Closed Above EMA 200\n💲 *Price:* {prev_4h['close']}\n🕒 {get_pkt_now()}"
                send_telegram(msg)
                signal_tracker[symbol]['ema_4h'] = prev_4h['ts']

        # --- 1-HOUR TIMEFRAME SCAN (EMA ONLY) ---
        time.sleep(0.2) # Small delay for stability
        bars_1h = future_ex.fetch_ohlcv(symbol, timeframe='1h', limit=250)
        if bars_1h and len(bars_1h) >= 210:
            df_1h = pd.DataFrame(bars_1h, columns=['ts', 'o', 'h', 'l', 'close', 'v'])
            df_1h['ema200'] = df_1h['close'].ewm(span=200, adjust=False).mean()
            
            p1h = df_1h.iloc[-2]  # Last closed
            p2h = df_1h.iloc[-3]  # 2nd last
            
            if p2h['close'] <= p2h['ema200'] and p1h['close'] > p1h['ema200']:
                if signal_tracker[symbol].get('ema_1h') != p1h['ts']:
                    msg = f"🟢 *EMA 200 BULLISH (1H)* 🟢\n🪙 *Coin:* {clean_name}\n💲 *Price:* {p1h['close']}\n🕒 {get_pkt_now()}"
                    send_telegram(msg)
                    signal_tracker[symbol]['ema_1h'] = p1h['ts']

    except Exception as e:
        # Fail-safe: Any error in a single coin will just skip it
        print(f"Skipping {symbol} due to error: {e}")
        pass

if __name__ == "__main__":
    welcome = f"🚀 *Binance Top 100 Gainer Bot*\n📍 *Strategies:* RSI 68 (Wilder's) + EMA 200\n⏱️ *Sleep:* 3 Minutes\n🕒 {get_pkt_now()}"
    send_telegram(welcome)
    
    while True:
        try:
            # 1. Fetch top 100 gainers
            top_100 = get_top_100_gainers()
            
            if top_100:
                for symbol in top_100:
                    analyze_coin(symbol)
                    time.sleep(0.1) # Micro-sleep to avoid Binance rate limits
            
            # 2. Resource Management Sleep (As requested: 3 Minutes)
            print(f"Scan complete at {get_pkt_now()}. Sleeping for 3 minutes...")
            time.sleep(180) 
            
        except Exception as e:
            print(f"Main loop error: {e}")
            time.sleep(60)
