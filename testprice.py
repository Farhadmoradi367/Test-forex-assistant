import requests

TWELVE_DATA_API_KEY = "0ae022a265924aa98ec6084f6de7b353"
PUSHBULLET_API_KEY = "o.S9w7mC9uR7v60q8A8bH7k2N9z7X5c3V1" # توکن پوش‌بولت شما
symbol = "EUR/USD"

def send_notification(title, body):
    url = "https://api.pushbullet.com/v2/pushes"
    headers = {
        "Access-Token": PUSHBULLET_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "type": "note",
        "title": title,
        "body": body
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        if response.status_code == 200:
            print("📣 نوتیفیکیشن با موفقیت به گوشی ارسال شد.")
        else:
            print(f"❌ خطا در ارسال نوتیفیکیشن: {response.text}")
    except Exception as e:
        print(f"❌ خطای ارتباطی پوش‌بولت: {e}")

def analyze_market_structure():
    print("⏳ در حال دریافت دیتا و تحلیل ساختار بازار...")
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=120&apikey={TWELVE_DATA_API_KEY}"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if "values" not in data:
            print("❌ خطا در دریافت دیتا.")
            return

        candles = data["values"][::-1]
        highs = [float(c['high']) for c in candles]
        lows = [float(c['low']) for c in candles]
        closes = [float(c['close']) for c in candles]
        times = [c['datetime'] for c in candles]

        swing_highs = []
        swing_lows = []

        # ۱. الگوریتم سقف و کف‌های اصلی
        for i in range(2, len(candles) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                swing_highs.append({'price': highs[i], 'time': times[i]})
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                swing_lows.append({'price': lows[i], 'time': times[i]})

        if not swing_highs or not swing_lows:
            print("⚠️ دیتای ساختاری کافی یافت نشد.")
            return

        last_swing_high = swing_highs[-1]
        last_swing_low = swing_lows[-1]
        current_close = closes[-1]

        print(f"📌 سقف اصلی: {last_swing_high['price']} | کف اصلی: {last_swing_low['price']} | قیمت فعلی: {current_close}")

        # ۲. بررسی شیفت ساختار و ارسال نوتیفیکیشن در صورت وقوع حادثه
        if current_close < last_swing_low['price']:
            msg_title = f"🚨 شیفت جریان نزولی ({symbol})"
            msg_body = f"ساختار بازار رو به پایین شکست!\nقیمت کلوز: {current_close}\nکف معتبر قبلی: {last_swing_low['price']}"
            print(msg_body)
            send_notification(msg_title, msg_body)
            
        elif current_close > last_swing_high['price']:
            msg_title = f"🚀 شیفت جریان صعودی ({symbol})"
            msg_body = f"ساختار بازار رو به بالا شکست!\nقیمت کلوز: {current_close}\nسقف معتبر قبلی: {last_swing_high['price']}"
            print(msg_body)
            send_notification(msg_title, msg_body)
            
        else:
            print("🟢 ساختار حفظ شده است. جابجایی شدیدی رخ نداده؛ نوتیفیکیشنی ارسال نمی‌شود.")

    except Exception as e:
        print(f"❌ خطا: {e}")

if __name__ == "__main__":
    analyze_market_structure()
                                 
