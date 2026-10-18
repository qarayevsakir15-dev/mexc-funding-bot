import requests

# ================= MƏXFİ MƏLUMATLAR =================
TELEGRAM_TOKEN = "8967707588:AAHfwjPTAijCAx6-kTEHw1v_OS6ZUXIthlU"
TELEGRAM_CHAT_ID = "8489506661"
# ======================================================

def send_telegram(msg):
    """Telegram bota mesaj göndərən və cavabı yoxlayan funksiya"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        response = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID, 
            "text": msg, 
            "parse_mode": "Markdown"
        })
        print("Telegram-dan gələn cavab:", response.text)
    except Exception as e:
        print("Telegram xətası:", e)

def check_funding_rates():
    """MEXC fyuçers bazarından ən yüksək faiz verən coin-ləri axtarır"""
    try:
        response = requests.get("https://contract.mexc.com/api/v1/contract/detail")
        data = response.json()
        
        if not data.get("success"):
            send_telegram("⚠️ MEXC API-dən məlumat almaq mümkün olmadı.")
            return
            
        contracts = data.get("data", [])
        sorted_contracts = sorted(contracts, key=lambda x: x.get('fundingRate', 0), reverse=True)
        
        report = "📊 *MEXC Yüksək Funding Rate Hesabatı*\n\n"
        top_coins = 0
        
        for item in sorted_contracts:
            symbol = item.get('symbol', '').replace('_', '/')
            rate = item.get('fundingRate', 0) * 100
            
            if rate >= 0.01:
                report += f"🔹 *{symbol}*: `{rate:.4f}%` (Hər 8 saatdan bir)\n"
                top_coins += 1
                if top_coins >= 5:
                    break
        
        if top_coins == 0:
            report += "Hal-hazırda kritik dərəcədə yüksək faizli (>0.03%) coin yoxdur."
            
        send_telegram(report)
        
    except Exception as e:
        print("Xəta baş verdi:", e)
        send_telegram(f"⚠️ Bot xətası: {e}")

if __name__ == "__main__":
    send_telegram("🚀 Funding Rate Botu işə düşdü!")
    check_funding_rates()
