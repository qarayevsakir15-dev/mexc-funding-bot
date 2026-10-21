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
    url = f"https://www.okx.com/api/v5/market/candles?instId={symbol}&bar=4H&limit=60"
    try:
        res = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        if res.status_code == 200:
            data = res.json()
            if data.get("code") == "0":
                rows = data.get("data", [])
                if not rows:
                    return None
                df = pd.DataFrame(rows, columns=['ts', 'open', 'high', 'low', 'close', 'vol', 'volCcy', 'volCcyQuote', 'confirm'])
                df = df.iloc[::-1].reset_index(drop=True)
                for col in ['open', 'high', 'low', 'close', 'vol']:
                    df[col] = df[col].astype(float)
                return df
    except Exception as e:
        print(f"Kline çəkmə xətası ({symbol}): {e}")
    return None

def analyze_market():
    # 35 ədəd seçilmiş yüksək likvidli koin siyahısı
    target_coins = [
        "BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP", "XRP-USDT-SWAP", "SUI-USDT-SWAP", 
        "LINK-USDT-SWAP", "DOGE-USDT-SWAP", "NEAR-USDT-SWAP", "ADA-USDT-SWAP", "ARB-USDT-SWAP", 
        "UNI-USDT-SWAP", "LTC-USDT-SWAP", "ONDO-USDT-SWAP", "XLM-USDT-SWAP", "AVAX-USDT-SWAP",
        "APT-USDT-SWAP", "RENDER-USDT-SWAP", "INJ-USDT-SWAP", "TIA-USDT-SWAP", "FET-USDT-SWAP",
        "PEPE-USDT-SWAP", "SHIB-USDT-SWAP", "AR-USDT-SWAP", "OP-USDT-SWAP", "ATOM-USDT-SWAP",
        "FIL-USDT-SWAP", "NEAR-USDT-SWAP", "ICP-USDT-SWAP", "POL-USDT-SWAP", "ETC-USDT-SWAP",
        "KAS-USDT-SWAP", "SEI-USDT-SWAP", "TIA-USDT-SWAP", "NEAR-USDT-SWAP", "HBAR-USDT-SWAP"
    ]
    # Təkrar düşənləri təmizləyirik
    target_coins = list(dict.fromkeys(target_coins))

    # Əvvəlcə Bitcoin-in (BTC) ümumi 4H trendini təyin edirik (Makro Süzgəc üçün)
    btc_df = get_klines("BTC-USDT-SWAP")
    btc_bullish = True
    if btc_df is not None and len(btc_df) >= 30:
        btc_df['EMA7'] = ta.trend.ema_indicator(btc_df['close'], window=7)
        btc_df['EMA25'] = ta.trend.ema_indicator(btc_df['close'], window=25)
        # Bağlanmış son şam üzrə BTC trendi
        btc_bullish = btc_df['EMA7'].iloc[-2] > btc_df['EMA25'].iloc[-2]

    signals = []
    summary_details = []

    for sym in target_coins:
        df = get_klines(sym)
        if df is None or len(df) < 40:
            continue
        
        # İndikatorlar
        df['EMA7'] = ta.trend.ema_indicator(df['close'], window=7)
        df['EMA25'] = ta.trend.ema_indicator(df['close'], window=25)
        df['RSI'] = ta.momentum.rsi(df['close'], window=14)
        df['ATR'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
        df['Vol_SMA'] = df['vol'].rolling(window=20).mean()
        
        # BAXILAN ŞAM: Bağlanmış sonuncu tamamlanmış 4H şamı (index -2) və ondan əvvəlki (index -3)
        prev_ema7 = df['EMA7'].iloc[-3]
        prev_ema25 = df['EMA25'].iloc[-3]
        curr_ema7 = df['EMA7'].iloc[-2]
        curr_ema25 = df['EMA25'].iloc[-2]
        curr_rsi = df['RSI'].iloc[-1] # Cari RSI
        price = df['close'].iloc[-1]   # Cari canlı qiymət
        atr = df['ATR'].iloc[-2]
        current_vol = df['vol'].iloc[-2]
        avg_vol = df['Vol_SMA'].iloc[-2]
        
        display_name = sym.replace("-USDT-SWAP", "")
        summary_details.append(f"• `{display_name}` | Qiymət: `${price:.4f}` | RSI: `{curr_rsi:.1f}`")

        # Həcm Süzgəci: Bağlanmış şamın həcmi son 20 şamın ortalamasından azı 20% çox olmalıdır
        is_volume_valid = current_vol > (avg_vol * 1.2)

        # 4H Kəsişmə Şərtləri (Bağlanmış şamlar əsasında)
        # LONG Şərti
        if prev_ema7 <= prev_ema25 and curr_ema7 > curr_ema25 and curr_rsi > 45 and is_volume_valid:
            # Əgər BTC trendi tərsinədirsə, əlavə qoruma tətbiq edə bilərik, amma burada əsas siqnalı veririk
            sl = price - (1.5 * atr)
            tp1 = price + (2.0 * atr)
            tp2 = price + (3.5 * atr)
            
            signals.append(
                f"🟢 **{display_name}** — **LONG (4H Yeni Trend)**\n"
                f"• Giriş Qiyməti: `${price:.4f}`\n"
                f"• RSI: `{curr_rsi:.1f}` | Həcmli Kəsişmə ✅\n"
                f"• 🛑 Stop-Loss: `${sl:.4f}`\n"
                f"• 🎯 TP1: `${tp1:.4f}` | TP2: `${tp2:.4f}`"
            )

        # SHORT Şərti
        elif prev_ema7 >= prev_ema25 and curr_ema7 < curr_ema25 and curr_rsi < 55 and is_volume_valid:
            sl = price + (1.5 * atr)
            tp1 = price - (2.0 * atr)
            tp2 = price - (3.5 * atr)
            
            signals.append(
                f"🔴 **{display_name}** — **SHORT (4H Yeni Trend)**\n"
                f"• Giriş Qiyməti: `${price:.4f}`\n"
                f"• RSI: `{curr_rsi:.1f}` | Həcmli Kəsişmə ✅\n"
                f"• 🛑 Stop-Loss: `${sl:.4f}`\n"
                f"• 🎯 TP1: `${tp1:.4f}` | TP2: `${tp2:.4f}`"
            )

    # Telegram Hesabatı
    if signals:
        msg = f"⚡ **PRO KRİPTO - 4H SİQNALI (5M Skan)**\n\n" + "\n\n".join(signals)
        send_telegram(msg)
    else:
        details_text = "\n".join(summary_details) if summary_details else "⚠️ Məlumat alınmadı."
        report = (
            f"🔄 *4H Peşəkar Skan Hesabatı (OKX)*:\n"
            f"35 seçilmiş koin yoxlanıldı. Yeni həcmli kəsişmə tapılmadı.\n\n"
            f"**Cari Qiymətlər & RSI:**\n{details_text}"
        )
        send_telegram(report)

if __name__ == "__main__":
    analyze_market()
