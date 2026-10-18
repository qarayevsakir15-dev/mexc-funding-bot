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
    url = "https://api.phemex.com/public/products"
    try:
        res = requests.get(url).json()
        symbols = []
        if res.get("code") == 0:
            products = res.get("data", {}).get("products", [])
            for p in products:
                if p.get("type") == "Perpetual" and p.get("quoteCurrency") == "USDT":
                    symbols.append(p.get("symbol"))
        return symbols[:30]
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
    signals = []
    debug_info = []

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
        
        # Əgər BTC və ya ETH-dirsə, diaqnostika üçün qeyd edək
        if sym in ["BTCUSDT", "ETHUSDT"]:
            debug_info.append(f"📊 `{sym}` -> Qiymət: ${price:.2f} | EMA7: {curr_ema7:.2f} | EMA25: {curr_ema25:.2f} | RSI: {curr_rsi:.1f}")

        # ƏRKƏN TREND SÜZGƏCİ (Kəsişmə yoxlaması)
        if prev_ema7 <= prev_ema25 and curr_ema7 > curr_ema25 and curr_rsi > 45:
            signals.append(f"🟢 **{sym}** — **LONG (Yeni Trend)**\n• Qiymət: ${price:.4f}\n• RSI: {curr_rsi:.1f}\n• Şərt: EMA 7/25 kəsişməsi yenicə baş verdi!")

        elif prev_ema7 >= prev_ema25 and curr_ema7 < curr_ema25 and curr_rsi < 55:
            signals.append(f"🔴 **{sym}** — **SHORT (Yeni Trend)**\n• Qiymət: ${price:.4f}\n• RSI: {curr_rsi:.1f}\n• Şərt: EMA 7/25 kəsişməsi yenicə baş verdi!")

    # Siqnal varsa onları göndər, yoxdursa cari analiz məlumatlarını hesabat kimi at
    if signals:
        msg = "⚡ **PHEMEX - ERKƏN TREND SİQNALI (5M)**\n\n" + "\n\n".join(signals)
        send_telegram(msg)
    else:
        report = "🔄 *Phemex Bot Skan Hesabatı*:\nYeni kəsişmə yoxdur. Phemex-dən alınan son test göstəriciləri:\n\n" + "\n".join(debug_info)
        send_telegram(report)

if __name__ == "__main__":
    analyze_market()
