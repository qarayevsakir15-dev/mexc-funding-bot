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
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram xətası: {e}")

def get_phemex_klines(symbol):
    """Phemex Public API vasitəsilə 4 saatlıq (4h) kline məlumatlarını çəkir"""
    # Phemex-də 4 saatlıq interval saniyə ilə: 4 * 3600 = 14400
    url = f"https://api.phemex.com/exchange/public/md/kline?symbol={symbol}&interval=14400&limit=50"
    try:
        res = requests.get(url, timeout=5).json()
        if res.get("code") == 0 and "rows" in res.get("data", {}):
            rows = res["data"]["rows"]
            if not rows:
                return None
            df = pd.DataFrame(rows, columns=['time', 'interval', 'close', 'open', 'high', 'low', 'volume', 'turnover'])
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            
            # Phemex qiymətlərində bəzən 10000 çarpanı olur, onu tənzimləyirik
            if df['close'].iloc[0] > 1000000:
                df['close'] = df['close'] / 10000.0
                df['volume'] = df['volume'] / 10000.0
            return df
    except Exception as e:
        print(f"Phemex Kline xətası ({symbol}): {e}")
    return None

def analyze_market():
    # Sənin istədiyin coinlərin Phemex-dəki standart fyuçers simvol adları
    target_coins = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "SUIUSDT", 
        "LINKUSDT", "DOGEUSDT", "NEARUSDT", "ADAUSDT", "ARBUSDT", 
        "UNIUSDT", "LTCUSDT", "ONDOUSDT", "XLMUSDT", "PUMPUSDT", "AVAXUSDT"
    ]
    
    signals = []
    summary_details = []

    for sym in target_coins:
        df = get_phemex_klines(sym)
        
        # Əgər standart adla tapılmasa, Phemex-dəki 'u' prefixli alternativi yoxlayaq (məs: uBTCUSDT)
        if df is None or len(df) < 30:
            df = get_phemex_klines(f"u{sym}")
            used_sym = f"u{sym}"
        else:
            used_sym = sym

        if df is None or len(df) < 30:
            continue
        
        # 4H qrafik üzrə indikatorlar (EMA 7, EMA 25, RSI 14)
        df['EMA7'] = ta.trend.ema_indicator(df['close'], window=7)
        df['EMA25'] = ta.trend.ema_indicator(df['close'], window=25)
        df['RSI'] = ta.momentum.rsi(df['close'], window=14)
        
        prev_ema7 = df['EMA7'].iloc[-2]
        prev_ema25 = df['EMA25'].iloc[-2]
        curr_ema7 = df['EMA7'].iloc[-1]
        curr_ema25 = df['EMA25'].iloc[-1]
        curr_rsi = df['RSI'].iloc[-1]
        price = df['close'].iloc[-1]
        
        # Faktiki göstəriciləri yığırıq
        summary_details.append(f"• `{sym}` | Qiymət: `${price:.4f}` | EMA7: `{curr_ema7:.4f}` | EMA25: `{curr_ema25:.4f}` | RSI: `{curr_rsi:.1f}`")

        # 4H Tранд kəsişmə yoxlaması
        if prev_ema7 <= prev_ema25 and curr_ema7 > curr_ema25 and curr_rsi > 45:
            signals.append(f"🟢 **{sym}** — **LONG (4H Yeni Trend)**\n• Qiymət: ${price:.4f}\n• RSI: {curr_rsi:.1f}\n• Şərt: 4H EMA 7/25 kəsişməsi baş verdi!")

        elif prev_ema7 >= prev_ema25 and curr_ema7 < curr_ema25 and curr_rsi < 55:
            signals.append(f"🔴 **{sym}** — **SHORT (4H Yeni Trend)**\n• Qiymət: ${price:.4f}\n• RSI: {curr_rsi:.1f}\n• Şərt: 4H EMA 7/25 kəsişməsi baş verdi!")

    # Telegram Hesabatı
    if signals:
        msg = f"⚡ **PHEMEX - 4H SİQNALI (5M Yoxlama)**\n\n" + "\n\n".join(signals)
        send_telegram(msg)
    else:
        details_text = "\n".join(summary_details) if summary_details else "⚠️ Məlumat alınmadı."
        report = (
            f"🔄 *Phemex 4H Qrafik Skan Hesabatı*:\n"
            f"Siyahıdakı coinlər 4H intervalda yoxlanıldı. Yeni kəsişmə tapılmadı.\n\n"
            f"**Phemex 4H Faktiki Göstəricilər:**\n{details_text}"
        )
        send_telegram(report)

if __name__ == "__main__":
    analyze_market()
