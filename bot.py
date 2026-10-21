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
    """OKX Public API - GitHub Actions-ı bloklamır, 4 saatlıq (4H) qrafik məlumatlarını verir"""
    url = f"https://www.okx.com/api/v5/market/candles?instId={symbol}&bar=4H&limit=50"
    try:
        res = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        if res.status_code == 200:
            data = res.json()
            if data.get("code") == "0":
                rows = data.get("data", [])
                if not rows:
                    return None
                # OKX məlumatı tərsinə (ən yenidən köhnəyə) qaytarır, düzəldirik
                df = pd.DataFrame(rows, columns=['ts', 'open', 'high', 'low', 'close', 'vol', 'volCcy', 'volCcyQuote', 'confirm'])
                df = df.iloc[::-1].reset_index(drop=True)
                df['close'] = df['close'].astype(float)
                df['vol'] = df['vol'].astype(float)
                return df
    except Exception as e:
        print(f"Kline çəkmə xətası ({symbol}): {e}")
    return None

def analyze_market():
    # OKX fyuçers (SWAP) simvolları
    target_coins = [
        "BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP", "XRP-USDT-SWAP", "SUI-USDT-SWAP", 
        "LINK-USDT-SWAP", "DOGE-USDT-SWAP", "NEAR-USDT-SWAP", "ADA-USDT-SWAP", "ARB-USDT-SWAP", 
        "UNI-USDT-SWAP", "LTC-USDT-SWAP", "ONDO-USDT-SWAP", "XLM-USDT-SWAP", "AVAX-USDT-SWAP"
    ]
    
    signals = []
    summary_details = []

    for sym in target_coins:
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
        
        # Ekran üçün təmiz ad (məs: BTC)
        display_name = sym.replace("-USDT-SWAP", "")
        summary_details.append(f"• `{display_name}` | Qiymət: `${price:.4f}` | EMA7: `{curr_ema7:.4f}` | EMA25: `{curr_ema25:.4f}` | RSI: `{curr_rsi:.1f}`")

        # 4H Trend kəsişmə yoxlaması
        if prev_ema7 <= prev_ema25 and curr_ema7 > curr_ema25 and curr_rsi > 45:
            signals.append(f"🟢 **{display_name}** — **LONG (4H Yeni Trend)**\n• Qiymət: ${price:.4f}\n• RSI: {curr_rsi:.1f}\n• Şərt: 4H EMA 7/25 kəsişməsi baş verdi!")

        elif prev_ema7 >= prev_ema25 and curr_ema7 < curr_ema25 and curr_rsi < 55:
            signals.append(f"🔴 **{display_name}** — **SHORT (4H Yeni Trend)**\n• Qiymət: ${price:.4f}\n• RSI: {curr_rsi:.1f}\n• Şərt: 4H EMA 7/25 kəsişməsi baş verdi!")

    # Telegram Mesajı
    if signals:
        msg = f"⚡ **OKX - 4H SİQNALI (5M Yoxlama)**\n\n" + "\n\n".join(signals)
        send_telegram(msg)
    else:
        details_text = "\n".join(summary_details) if summary_details else "⚠️ Məlumat alınmadı."
        report = (
            f"🔄 *4H Qrafik Skan Hesabatı (OKX)*:\n"
            f"Siyahıdakı coinlər 4 saatlıq intervalda yoxlanıldı. Yeni kəsişmə tapılmadı.\n\n"
            f"**4H Faktiki Göstəricilər:**\n{details_text}"
        )
        send_telegram(report)

if __name__ == "__main__":
    analyze_market()
    
