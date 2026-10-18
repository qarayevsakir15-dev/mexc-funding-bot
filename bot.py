import os
import requests
import pandas as pd
import ta

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
    """Phemex-də mövcud olan BÜTÜN aktiv USDT fyuçers cütlüklərini tam bazardan çəkir"""
    url = "https://api.phemex.com/public/products"
    try:
        res = requests.get(url).json()
        symbols = []
        if res.get("code") == 0:
            products = res.get("data", {}).get("products", [])
            for p in products:
                # Bütün Perpetual (Fyuçers) və USDT cütlüklərini götürürük
                if p.get("type") == "Perpetual" and p.get("quoteCurrency") == "USDT":
                    sym = p.get("symbol")
                    if sym:
                        symbols.append(sym)
        return symbols
    except Exception as e:
        print(f"Symbol çəkmə xətası: {e}")
        return []

def get_klines(symbol):
    url = f"https://api.phemex.com/exchange/public/md/kline?symbol={symbol}&interval=300&limit=50"
    try:
        res = requests.get(url).json()
        if res.get("code") == 0 and "rows" in res.get("data", {}):
            rows = res["data"]["rows"]
            df = pd.DataFrame(rows, columns=['time', 'interval', 'close', 'open', 'high', 'low', 'volume', 'turnover'])
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            if df['close'].iloc[0] > 1000000:
                df['close'] = df['close'] / 10000.0
                df['volume'] = df['volume'] / 10000.0
            return df
    except Exception as e:
        print(f"Kline çəkmə xətası ({symbol}): {e}")
    return None

def analyze_market():
    symbols = get_phemex_symbols()
    print(f"Cəmi tapılan simvol sayı: {len(symbols)}")
    
    signals = []
    btc_info = ""

    for sym in symbols:
        df = get_klines(sym)
        if df is None or len(df) < 30:
            continue
        
        # İndikatorların hesablanması
        df['EMA7'] = ta.trend.ema_indicator(df['close'], window=7)
        df['EMA25'] = ta.trend.ema_indicator(df['close'], window=25)
        df['RSI'] = ta.momentum.rsi(df['close'], window=14)
        
        prev_ema7 = df['EMA7'].iloc[-2]
        prev_ema25 = df['EMA25'].iloc[-2]
        curr_ema7 = df['EMA7'].iloc[-1]
        curr_ema25 = df['EMA25'].iloc[-1]
        curr_rsi = df['RSI'].iloc[-1]
        price = df['close'].iloc[-1]
        
        # Bitcoin məlumatını bütün bazardan tapıb yadda saxlayırıq
        if "BTC" in sym.upper() and not btc_info:
            btc_info = f"📊 **Bitcoin ({sym})**\n• Qiymət: ${price:.2f}\n• EMA 7: {curr_ema7:.2f}\n• EMA 25: {curr_ema25:.2f}\n• RSI: {curr_rsi:.1f}"

        # ERKƏN TREND SÜZGƏCİ (EMA 7/25 kəsişməsi və RSI şərti)
        if prev_ema7 <= prev_ema25 and curr_ema7 > curr_ema25 and curr_rsi > 45:
            signals.append(f"🟢 **{sym}** — **LONG (Yeni Trend)**\n• Qiymət: ${price:.4f}\n• RSI: {curr_rsi:.1f}\n• Şərt: EMA 7/25 kəsişməsi yenicə baş verdi!")

        elif prev_ema7 >= prev_ema25 and curr_ema7 < curr_ema25 and curr_rsi < 55:
            signals.append(f"🔴 **{sym}** — **SHORT (Yeni Trend)**\n• Qiymət: ${price:.4f}\n• RSI: {curr_rsi:.1f}\n• Şərt: EMA 7/25 kəsişməsi yenicə baş verdi!")

    # Telegram Mesajı
    if signals:
        msg = f"⚡ **PHEMEX - BÜTÜN BAZAR ERKƏN TREND SİQNALI (5M)**\n\n" + "\n\n".join(signals)
        send_telegram(msg)
    else:
        report = f"🔄 *Phemex Bot Skan Hesabatı*:\nBütün bazar ({len(symbols)} cütlük) yoxlanıldı. Yeni kəsişmə tapılmadı.\n\n" + (btc_info if btc_info else "Bitcoin məlumatı tapıldı.")
        send_telegram(report)

if __name__ == "__main__":
    analyze_market()
