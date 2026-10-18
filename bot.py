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

def get_target_symbols():
    """Sənin qeyd etdiyin seçilmiş coinlərin simvollarını dəqiq müəyyən edir"""
    base_coins = ["BTC", "ETH", "SOL", "XRP", "SUI", "LINK", "DOGE", "NEAR", "ADA", "ARB", "UNI", "LTC", "ONDO", "XLM", "PUMP", "AVAX"]
    
    # Əvvəlcə birbaşa standart Phemex simvollarını yaradırıq (məs: BTCUSDT, uBTCUSDT)
    symbols = []
    for coin in base_coins:
        symbols.append(f"{coin}USDT")
        symbols.append(f"u{coin}USDT")
        
    return symbols

def get_klines(symbol):
    url = f"https://api.phemex.com/exchange/public/md/kline?symbol={symbol}&interval=300&limit=50"
    try:
        res = requests.get(url, timeout=5).json()
        if res.get("code") == 0 and "rows" in res.get("data", {}):
            rows = res["data"]["rows"]
            if not rows:
                return None
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
    symbols = get_target_symbols()
    signals = []
    summary_details = []
    checked_coins = set()

    for sym in symbols:
        # Eyni koinin həm BTCUSDT, həm uBTCUSDT kimi dublikatlarını yoxlamaq üçün təmiz adını götürürük
        clean_name = sym.replace("u", "").replace("USDT", "")
        if clean_name in checked_coins:
            continue
            
        df = get_klines(sym)
        # Əgər birinci variant tapılmasa, 'u' prefixli variantı yoxlayaq
        if df is None or len(df) < 30:
            alt_sym = f"u{sym}" if not sym.startswith("u") else sym.replace("u", "", 1)
            df = get_klines(alt_sym)
            sym = alt_sym
            
        if df is None or len(df) < 30:
            continue
            
        checked_coins.add(clean_name)
        
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
        
        # Faktiki göstəriciləri siyahıya əlavə edirik
        summary_details.append(f"• `{sym}` | Qiymət: `${price:.2f}` | EMA7: `{curr_ema7:.2f}` | EMA25: `{curr_ema25:.2f}` | RSI: `{curr_rsi:.1f}`")

        # ERKƏN TREND SÜZGƏCİ
        if prev_ema7 <= prev_ema25 and curr_ema7 > curr_ema25 and curr_rsi > 45:
            signals.append(f"🟢 **{sym}** — **LONG (Yeni Trend)**\n• Qiymət: ${price:.4f}\n• RSI: {curr_rsi:.1f}\n• Şərt: EMA 7/25 kəsişməsi baş verdi!")

        elif prev_ema7 >= prev_ema25 and curr_ema7 < curr_ema25 and curr_rsi < 55:
            signals.append(f"🔴 **{sym}** — **SHORT (Yeni Trend)**\n• Qiymət: ${price:.4f}\n• RSI: {curr_rsi:.1f}\n• Şərt: EMA 7/25 kəsişməsi baş verdi!")

    # Telegram Mesajı
    if signals:
        msg = f"⚡ **PHEMEX - SEÇİLMİŞ COİNLƏR SİQNALI (5M)**\n\n" + "\n\n".join(signals)
        send_telegram(msg)
    else:
        details_text = "\n".join(summary_details) if summary_details else "Məlumat toplandı, lakin göstərici tapılmadı."
        report = (
            f"🔄 *Seçilmiş Coinlər Skan Hesabatı*:\n"
            f"Siyahıdakı coinlər yoxlanıldı. Yeni kəsişmə tapılmadı.\n\n"
            f"**Faktiki Göstəricilər:**\n{details_text}"
        )
        send_telegram(report)

if __name__ == "__main__":
    analyze_market()
