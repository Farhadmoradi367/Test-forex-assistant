import requests
import json
import time  # ۱. ابزار زمان پایتون را وارد می‌کنیم

TWELVE_DATA_API_KEY = "0ae022a265924aa98ec6084f6de7b353"
PUSHBULLET_API_KEY = "o.1xrZgZHp6t5M2dTdnqztZzMd5kVzDzVs"
symbol = "EUR/USD"

print("🚀 دستیار فارکس فرهاد روشن شد و کار خود را آغاز کرد...")

# ۲. این حلقه به زبان پایتون می‌گوید: این کار را تا ابد تکرار کن!
while True:
    
    # --- بخش دریافت قیمت ---
    url_twelve = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVE_DATA_API_KEY}"
    
    try:
        response = requests.get(url_twelve)
        data = response.json()
        eurusd_price = data.get("price", "نامشخص")
    except:
        eurusd_price = "نامشخص"

    # --- بخش ارسال نوتیفیکیشن ---
    if eurusd_price != "نامشخص":
        push_url = "https://api.pushbullet.com/v2/pushes"
        headers = {
            "Access-Token": PUSHBULLET_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "type": "note",
            "title": "💰 قیمت لحظه‌ای EUR/USD",
            "body": f"قیمت فعلی یورو به دلار: {eurusd_price}"
        }
        requests.post(push_url, headers=headers, data=json.dumps(payload))
        print(f"✅ قیمت {eurusd_price} ارسال شد. رفتن به خواب برای ۱ ساعت دیگر...")
    else:
        print("⚠️ خطا در دریافت قیمت. ۱۰ ثانیه دیگر دوباره تلاش می‌کنم...")
        time.sleep(10)
        continue

    # ۳. مهم‌ترین خط: به پایتون می‌گوییم ۳۶۰۰ ثانیه (معادل ۱ ساعت) کپه بکش و هیچ کاری نکن!
    time.sleep(7200)
