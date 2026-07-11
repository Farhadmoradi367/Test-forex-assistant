import requests
import json
import sys

TWELVE_DATA_API_KEY = "0ae022a265924aa98ec6084f6de7b353"
PUSHBULLET_API_KEY = "o.1xrZgZHp6t5M2dTdnqztZzMd5kVzDzVs"
symbol = "EUR/USD"

def get_forex_price():
    """دریافت قیمت لحظه‌ای"""
    url_twelve = f"https://api.twelvedata.com/price?symbol={symbol}&apikey={TWELVE_DATA_API_KEY}"
    try:
        response = requests.get(url_twelve, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("price")
    except Exception as e:
        print(f"❌ خطا در دریافت قیمت: {e}")
        return None

def send_notification(price):
    """ارسال نوتیفیکیشن"""
    push_url = "https://api.pushbullet.com/v2/pushes"
    headers = {
        "Access-Token": PUSHBULLET_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "type": "note",
        "title": "💰 قیمت لحظه‌ای EUR/USD",
        "body": f"قیمت فعلی یورو به دلار: {price}"
    }
    try:
        response = requests.post(push_url, headers=headers, 
                               data=json.dumps(payload), timeout=10)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"❌ خطا در ارسال نوتیفیکیشن: {e}")
        return False

def main():
    print("🚀 دستیار فارکس فرهاد روشن شد و کار خود را آغاز کرد...")
    price = get_forex_price()
    
    if price:
        print(f"💰 قیمت دریافت شد: {price}")
        if send_notification(price):
            print(f"✅ قیمت {price} ارسال شد. کار با موفقیت پایان یافت.")
        else:
            print("⚠️ ارسال نوتیفیکیشن ناموفق بود.")
            sys.exit(1)
    else:
        print("❌ دریافت قیمت ناموفق بود.")
        sys.exit(1)

if __name__ == "__main__":
    main()
    
