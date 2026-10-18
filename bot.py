import os
import requests
import pandas as pd
import pandas_ta as ta

# Telegram və Phemex parametrləri
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Telegram xətası: {e}")

def get_phemex_symbols():
    """Phemex-də aktiv USDT fyuçers cütlüklərini çəkir"""
    url = "https://api.phemex.com/public/products"
    res = requests.get(url).json()
    symbols = []
    if res.get("code") == 0:
        products = res.get("data", {}).get("products", [])
        for p in products:
            if p.get("type") == "Perpetual" and p.get("quoteCurrency") == "USDT":
                symbols.append(p.get("symbol"))
    return symbols[:30]  # Ən aktiv ilk 30 cütlük

def get_klines(symbol):
    """Phemex-dən 5 dəqiqəlik klines (şam) məlumatını çəkir"""
    url = f"https://api.phemex.com/exchange/public/md/kline?symbol={symbol}&interval=300&limit=50"
    res = requests.get(url).json()
    if res.get("code") == 0 and "rows" in res.get("data", {}):
        rows = res["data"]["rows"]
        df = pd.DataFrame(rows, columns=['time', 'interval', 'close', 'open', 'high', 'low', 'volume', 'turnover'])
        df['close'] = df['close'] / 10000.0 if df['close'].iloc[0] > 1000000 else df['close']
        df['volume'] = df['volume'] / 10000.0 if df['volume'].iloc[0] > 1000000 else df['volume']
        return df
    return None

def analyze_market():
    symbols = get_phemex_symbols()
    signals = []

    for sym in symbols:
        df = get_klines(sym)
        if df is None or len(df) < 30:
            continue
        
        # İndikatorların hesablanması
        df['EMA7'] = ta.ema(df['close'], length=7)
        df['EMA25'] = ta.ema(df['close'], length=25)
        df['RSI'] = ta.rsi(df['close'], length=14)
        
        prev_ema7 = df['EMA7'].iloc[-2]
        prev_ema25 = df['EMA25'].iloc[-2]
        curr_ema7 = df['EMA7'].iloc[-1]
        curr_ema25 = df['EMA25'].iloc[-1]
        curr_rsi = df['RSI'].iloc[-1]
        price = df['close'].iloc[-1]
        
        # TRENDİN ƏVVƏLİ SÜZGƏCİ (Kəsişmə məhz son şamda baş verib)
        if prev_ema7 <= prev_ema25 and curr_ema7 > curr_ema25 and curr_rsi > 45:
            signals.append(f"🟢 **{sym}** — **LONG (Yeni Trend)**\n• Qiymət: ${price:.4f}\n• RSI: {curr_rsi:.1f}\n• Şərt: EMA 7/25 kəsişməsi yenicə baş verdi!")

        elif prev_ema7 >= prev_ema25 and curr_ema7 < curr_ema25 and curr_rsi < 55:
            signals.append(f"🔴 **{sym}** — **SHORT (Yeni Trend)**\n• Qiymət: ${price:.4f}\n• RSI: {curr_rsi:.1f}\n• Şərt: EMA 7/25 kəsişməsi yenicə baş verdi!")

    if signals:
        msg = "⚡ **PHEMEX - ERKƏN TREND SİQNALI (5M)**\n\n" + "\n\n".join(signals)
        send_telegram(msg)
    else:
        print("Heç bir yeni trend başlanğıcı tapılmadı.")

if __name__ == "__main__":
    analyze_market()
