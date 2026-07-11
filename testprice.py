import requests
import json

TWELVE_DATA_API_KEY = "0ae022a265924aa98ec6084f6de7b353"
symbol = "EUR/USD"

def get_candle_history():
    print("⏳ در حال دریافت دیتای کندل‌های ۵ دقیقه‌ای...")
    # درخواست ۳۰ کندل آخر ۵ دقیقه‌ای با جزییات کامل (باز شدن، بسته شدن، سقف و کف)
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=30&apikey={TWELVE_DATA_API_KEY}"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if "values" in data:
            candles = data["values"]
            print(f"✅ با موفقیت {len(candles)} کندل دریافت شد.\n")
            
            # چاپ کردن وضعیت ۵ کندل آخر برای نمونه
            print("📋 وضعیت آخرین کندل‌های بازار (از جدید به قدیم):")
            for i, candle in enumerate(candles[:5]):
                print(f"کندل {i+1} -> زمان: {candle['datetime']} | سقف (High): {candle['high']} | کف (Low): {candle['low']} | کلوز: {candle['close']}")
        else:
            print("❌ دیتای کندل‌ها در پاسخ API یافت نشد:", data)
            
    except Exception as e:
        print(f"❌ خطا در ارتباط با سرور: {e}")

if __name__ == "__main__":
    get_candle_history()
            
