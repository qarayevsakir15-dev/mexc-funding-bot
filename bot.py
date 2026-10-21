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

def get_klines(symbol):
    """Binance Futures API - 4 saatlıq (4h) qrafikləri çəkir və xəta kodunu qeyd edir"""
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval=4h&limit=50"
    try:
        res = requests.get(url, timeout=5)
        print(f"{symbol} Status: {res.status_code}") # GitHub loglarında görünəcək
        if res.status_code == 200:
            rows = res.json()
            if not rows or not isinstance(rows, list):
                return None
            df = pd.DataFrame(rows, columns=[
                'open_time', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_asset_volume', 'number_of_trades',
                'taker_buy_base', 'taker_buy_quote', 'ignore'
            ])
            df['close'] = df['close'].astype(float)
            df['volume'] = df['volume'].astype(float)
            return df
        else:
            print(f"Xəta cavabı ({symbol}): {res.text}")
    except Exception as e:
        print(f"Kline çəkmə xətası ({symbol}): {e}")
    return None

def analyze_market():
    # Binance Futures-də 100% mövcud olan əsas simvollar
    target_coins = [
        "BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "SUIUSDT", 
        "LINKUSDT", "DOGEUSDT", "NEARUSDT", "ADAUSDT", "ARBUSDT", 
        "UNIUSDT", "LTCUSDT", "ONDOUSDT", "XLMUSDT", "AVAXUSDT"
    ]
    
    signals = []
    summary_details = []
    error_logs = []

    for sym in target_coins:
        url_test = f"https://fapi.binance.com/fapi/v1/klines?symbol={sym}&interval=4h&limit=50"
        try:
            r = requests.get(url_test, timeout=5)
            if r.status_code != 200:
                error_logs.append(f"{sym}: HTTP {r.status_code}")
                continue
        except Exception as ex:
            error_logs.append(f"{sym}: {str(ex)}")
            continue

        df = get_klines(sym)
        if df is None or len(df) < 30:
            continue
        
        # 4 Saatlıq (4H) qrafik üzrə indikatorlar (EMA 7, EMA 25, RSI 14)
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

        # 4H Trend kəsişmə yoxlaması
        if prev_ema7 <= prev_ema25 and curr_ema7 > curr_ema25 and curr_rsi > 45:
            signals.append(f"🟢 **{sym}** — **LONG (4H Yeni Trend)**\n• Qiymət: ${price:.4f}\n• RSI: {curr_rsi:.1f}\n• Şərt: 4H EMA 7/25 kəsişməsi baş verdi!")

        elif prev_ema7 >= prev_ema25 and curr_ema7 < curr_ema25 and curr_rsi < 55:
            signals.append(f"🔴 **{sym}** — **SHORT (4H Yeni Trend)**\n• Qiymət: ${price:.4f}\n• RSI: {curr_rsi:.1f}\n• Şərt: 4H EMA 7/25 kəsişməsi baş verdi!")

    # Telegram Mesajı
    if signals:
        msg = f"⚡ **KRİPTO - 4H SİQNALI (5M Yoxlama)**\n\n" + "\n\n".join(signals)
        send_telegram(msg)
    else:
        details_text = "\n".join(summary_details) if summary_details else f"⚠️ Məlumat alınmadı.\nXətalar: {', '.join(error_logs[:5])}"
        report = (
            f"🔄 *4H Qrafik Skan Hesabatı*:\n"
            f"Siyahıdakı coinlər 4 saatlıq intervalda yoxlanıldı. Yeni kəsişmə tapılmadı.\n\n"
            f"**4H Faktiki Göstəricilər:**\n{details_text}"
        )
        send_telegram(report)

if __name__ == "__main__":
    analyze_market()
