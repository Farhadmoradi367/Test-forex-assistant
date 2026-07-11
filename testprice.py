import requests

TWELVE_DATA_API_KEY = "0ae022a265924aa98ec6084f6de7b353"
symbol = "EUR/USD"

def analyze_market_structure():
    print("⏳ در حال دریافت دیتا و تحلیل ساختار بازار (بازه ۱۰ ساعته)...")
    # افزایش خروجی به ۱۲۰ کندل ۵ دقیقه‌ای برای داشتن دید کلان و دقیق
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=5min&outputsize=120&apikey={TWELVE_DATA_API_KEY}"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if "values" not in data:
            print("❌ خطا در دریافت دیتا از API.")
            return

        # مرتب کردن کندل‌ها از قدیم به جدید برای تحلیل درست زمانی
        candles = data["values"][::-1]
        
        highs = [float(c['high']) for c in candles]
        lows = [float(c['low']) for c in candles]
        closes = [float(c['close']) for c in candles]
        times = [c['datetime'] for c in candles]

        swing_highs = []
        swing_lows = []

        # ۱. الگوریتم پیدا کردن سقف و کف‌های اصلی (قانون کندل ایزوله)
        for i in range(2, len(candles) - 2):
            # بررسی سقف اصلی (بلندتر از ۲ کندل قبل و ۲ کندل بعد)
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                swing_highs.append({'price': highs[i], 'time': times[i]})
            
            # بررسی کف اصلی (پایین‌تر از ۲ کندل قبل و ۲ کندل بعد)
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                swing_lows.append({'price': lows[i], 'time': times[i]})

        print(f"🔍 تعداد {len(swing_highs)} سقف اصلی و {len(swing_lows)} کف اصلی در ۱۰ ساعت گذشته یافت شد.\n")

        if not swing_highs or not swing_lows:
            print("⚠️ دیتای کافی برای ساختار یافت نشد. بازار در این بازه بسیار فشرده یا تک‌روند بوده است.")
            return

        # پیدا کردن آخرین سقف و کف تایید شده بازار
        last_swing_high = swing_highs[-1]
        last_swing_low = swing_lows[-1]
        current_close = closes[-1]

        print(f"📌 آخرین سقف اصلی تایید شده: {last_swing_high['price']} (زمان: {last_swing_high['time']})")
        print(f"📌 آخرین کف اصلی تایید شده: {last_swing_low['price']} (زمان: {last_swing_low['time']})")
        print(f"⚡ قیمت فعلی بازار (کلوز آخرین کندل): {current_close}\n")

        # ۲. الگوریتم تشخیص شیفت جریان (MSS)
        print("🤖 وضعیت ارزیابی ربات:")
        if current_close < last_swing_low['price']:
            print("🚨🚨🚨 هشدارهای ترید: شیفت جریان (MSS) نزولی رخ داده است! قیمت زیر کف اصلی بسته شد.")
        elif current_close > last_swing_high['price']:
            print("🚀🚀🚀 هشدارهای ترید: شیفت جریان (MSS) صعودی رخ داده است! قیمت بالای سقف اصلی بسته شد.")
        else:
            print("🟢 ساختار حفظ شده است. جریان پول تغییر نکرده و بازار درون محدوده قبلی حرکت می‌کند.")

    except Exception as e:
        print(f"❌ خطا در اجرای الگوریتم: {e}")

if __name__ == "__main__":
    analyze_market_structure()
    
