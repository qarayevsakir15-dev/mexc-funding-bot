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
    """Phemex bazarından sənin istədiyin coinlərin ən dəqiq və aktiv simvol adlarını avtomatik tapır"""
    target_bases = ["BTC", "ETH", "SOL", "XRP", "SUI", "LINK", "DOGE", "NEAR", "ADA", "ARB", "UNI", "LTC", "ONDO", "XLM", "PUMP", "AVAX"]
    
    url = "https://api.phemex.com/public/products"
    valid_symbols = []
    try:
        res = requests.get(url).json()
        data = res.get("data", [])
        products = data if isinstance(data, list) else data.get("products", data.get("perpProducts", []))
        
        for p in products:
            sym = p.get("symbol", "").upper()
            quote = p.get("quoteCurrency", "").upper()
            p_type = p.get("type", "")
            
            if "USDT" in sym and (p_type == "Perpetual" or quote == "USDT"):
                for base in target_bases:
                    # Əgər simvolun içində həm baz coin, həm də USDT varsa
                    if sym == f"{base}USDT" or sym == f"U{base}USDT" or sym == f"1000{base}USDT" or sym.startswith(base):
                        # Dəqiq uyğunluq yoxlaması
                        clean_sym = sym.replace("U", "", 1) if sym.startswith("U") else sym
                        if clean_sym.startswith(base) or base in clean_sym:
                            valid_symbols.append(p.get("symbol"))
                            break
    except Exception as e:
        print(f"Symbol çəkmə xətası: {e}")

    # Əgər siyahı boş qalsa, standart formatları əlavə edirik
    if not valid_symbols:
        for base in target_bases:
            valid_symbols.append(f"{base}USDT")

    # Təkrar düşənləri təmizləyirik
    return list(dict.fromkeys(valid_symbols))

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
    print(f"Tapılan hədəf simvollar: {symbols}")
    
    signals = []
    summary_details = []

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
        
        # Hər bir uğurla yoxlanılan coin üçün faktiki göstəriciləri əlavə edirik
        summary_details.append(f"• `{sym}` | Qiymət: `${price:.4f}` | EMA7: `{curr_ema7:.4f}` | EMA25: `{curr_ema25:.4f}` | RSI: `{curr_rsi:.1f}`")

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
        details_text = "\n".join(summary_details) if summary_details else "⚠️ Məlumat oxundu, lakin heç bir coin kline qaytarmadı."
        report = (
            f"🔄 *Seçilmiş Coinlər Skan Hesabatı*:\n"
            f"Siyahıdakı coinlər yoxlanıldı. Yeni kəsişmə tapılmadı.\n\n"
            f"**Faktiki Göstəricilər:**\n{details_text}"
        )
        send_telegram(report)

if __name__ == "__main__":
    analyze_market()
