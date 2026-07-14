import requests
import pandas as pd
import numpy as np
import sys
import json
from datetime import datetime, timedelta

# ======================== تنظیمات اصلی ========================
SYMBOL = "EUR/USD"
TWELVEDATA_API_KEY = "0ae022a265924aa98ec6084f6de7b353"
TWELVEDATA_BASE_URL = "https://api.twelvedata.com/time_series"

PUSHBULLET_TOKEN = "o.S9w7mC9uR7v60q8A8bH7k2N9z7X5c3V1"
PUSHBULLET_URL = "https://api.pushbullet.com/v2/pushes"

RISK_REWARD_RATIO = 2.0
MIN_CANDLE_BODY_RATIO = 0.6

# ======================== دریافت داده ========================
def fetch_klines(symbol, interval, limit=200):
    params = {"symbol": symbol, "interval": interval, "outputsize": limit, "apikey": TWELVEDATA_API_KEY}
    try:
        resp = requests.get(TWELVEDATA_BASE_URL, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('status') == 'error':
                print(f"خطای TwelveData: {data.get('message')}")
                return None
            if 'values' in data and data['values']:
                df = pd.DataFrame(data['values'])
                df[['open', 'high', 'low', 'close']] = df[['open', 'high', 'low', 'close']].astype(float)
                return df.iloc[::-1].reset_index(drop=True)
    except Exception as e:
        print(f"خطا در دریافت دیتا: {e}")
    return None

# ======================== تحلیل پرایس اکشن (SMC) ========================
def find_swings(df, lookback=7):
    highs, lows = [], []
    for i in range(lookback, len(df) - lookback):
        if all(df['high'].iloc[i] > df['high'].iloc[i - j] for j in range(1, lookback + 1)) and \
           all(df['high'].iloc[i] > df['high'].iloc[i + j] for j in range(1, lookback + 1)):
            highs.append((i, df['high'].iloc[i]))
        if all(df['low'].iloc[i] < df['low'].iloc[i - j] for j in range(1, lookback + 1)) and \
           all(df['low'].iloc[i] < df['low'].iloc[i + j] for j in range(1, lookback + 1)):
            lows.append((i, df['low'].iloc[i]))
    return highs, lows

def get_htf_bias(df_1h):
    highs, lows = find_swings(df_1h, lookback=3)
    if len(highs) < 2 or len(lows) < 2: return "NEUTRAL"
    if highs[-1][1] > highs[-2][1] and lows[-1][1] > lows[-2][1]: return "BULLISH"
    elif highs[-1][1] < highs[-2][1] and lows[-1][1] < lows[-2][1]: return "BEARISH"
    return "NEUTRAL"

def detect_fvg(df, lookback=40):
    fvgs = []
    for i in range(len(df) - lookback, len(df) - 2):
        if df['close'].iloc[i] < df['open'].iloc[i] and df['close'].iloc[i+1] > df['open'].iloc[i+1] and \
           df['close'].iloc[i+1] > df['high'].iloc[i] and df['low'].iloc[i+2] > df['high'].iloc[i]:
            fvgs.append(('BULLISH', df['high'].iloc[i], df['low'].iloc[i+2]))
        elif df['close'].iloc[i] > df['open'].iloc[i] and df['close'].iloc[i+1] < df['open'].iloc[i+1] and \
             df['close'].iloc[i+1] < df['low'].iloc[i] and df['high'].iloc[i+2] < df['low'].iloc[i]:
            fvgs.append(('BEARISH', df['low'].iloc[i], df['high'].iloc[i+2]))
    return fvgs

def is_liquidity_swept(df, swings_high, swings_low):
    if not swings_high or not swings_low: return None
    last_close, last_high, last_low = df['close'].iloc[-1], df['high'].iloc[-1], df['low'].iloc[-1]
    if last_high > swings_high[-1][1] and last_close < swings_high[-1][1]: return "BUY_SIDE_SWEPT"
    if last_low < swings_low[-1][1] and last_close > swings_low[-1][1]: return "SELL_SIDE_SWEPT"
    return None

def check_mss(df, htf_bias, swings_high, swings_low):
    if htf_bias == "BULLISH" and swings_low:
        if df['close'].iloc[-1] > swings_low[-1][1] and df['close'].iloc[-2] <= swings_low[-1][1]: return "BULLISH_MSS"
    elif htf_bias == "BEARISH" and swings_high:
        if df['close'].iloc[-1] < swings_high[-1][1] and df['close'].iloc[-2] >= swings_high[-1][1]: return "BEARISH_MSS"
    return None

def confirm_candle(df):
    last = df.iloc[-1]
    body = abs(last['close'] - last['open'])
    total = last['high'] - last['low']
    return total > 0 and (body / total) >= MIN_CANDLE_BODY_RATIO

# ======================== ارسال نوتیفیکیشن گزارش وضعیت ========================
def send_status_report(trend_4h, status_msg):
    iran_time = datetime.utcnow() + timedelta(hours=3, minutes=30)
    time_str = iran_time.strftime('%H:%M')
    
    trend_emoji = "⚪"
    if trend_4h == "BULLISH": trend_emoji = "📈"
    elif trend_4h == "BEARISH": trend_emoji = "📉"
    
    title = f"🤖 گزارش وضعیت ربات EUR/USD"
    body = (
        f"وضعیت: فعال و در حال بررسی چارت ⏱️\n"
        f"روند کلی چارت (4H): {trend_emoji} {trend_4h}\n"
        f"آخرین تحلیل: {status_msg}\n"
        f"ساعت به وقت ایران: {time_str}"
    )
    
    headers = {"Access-Token": PUSHBULLET_TOKEN, "Content-Type": "application/json"}
    payload = {"type": "note", "title": title, "body": body}
    try:
        requests.post(PUSHBULLET_URL, json=payload, headers=headers, timeout=10)
        print(f"📱 گزارش وضعیت ربات با موفقیت به گوشی ارسال شد.")
    except Exception as e:
        print(f"⚠️ خطا در ارسال گزارش وضعیت: {e}")

# ======================== موتور سیگنال برای هر تایم‌فریم ========================
def analyze_timeframe(signal_tf, htf_tf, htf_lookback=100, signal_lookback=200):
    print(f"\n{'='*50}")
    print(f"🔍 تحلیل تایم‌فریم {signal_tf} با روند {htf_tf}")
    print(f"{'='*50}")
    
    df_htf = fetch_klines(SYMBOL, htf_tf, limit=htf_lookback)
    df_signal = fetch_klines(SYMBOL, signal_tf, limit=signal_lookback)
    
    if df_htf is None or df_signal is None:
        print(f"❌ خطا در دریافت اطلاعات برای {signal_tf}")
        if signal_tf == "4h":
            send_status_report("نامشخص", "خطا در دریافت داده‌ها از وب‌سایت مرجع")
        return False

    htf_trend = get_htf_bias(df_htf)
    print(f"📈 روند تایم‌فریم بالا ({htf_tf}): {htf_trend}")
    if htf_trend == "NEUTRAL":
        print(f"⏸️ روند خنثی - صرف‌نظر از {signal_tf}")
        if signal_tf == "4h":
            send_status_report(htf_trend, "بازار روند مشخصی ندارد (رنج)")
        return False

    swings_high, swings_low = find_swings(df_signal, lookback=7)
    if not swings_high or not swings_low:
        print(f"⚠️ نوسان‌های کافی در {signal_tf} یافت نشد")
        if signal_tf == "4h":
            send_status_report(htf_trend, "نوسان کافی (High/Low) در چارت پیدا نشد")
        return False

    liquidity = is_liquidity_swept(df_signal, swings_high, swings_low)
    if not liquidity:
        print(f"🟢 نقدینگی در {signal_tf} شکار نشد")
        if signal_tf == "4h":
            send_status_report(htf_trend, "نقدینگی چارت شکار نشد")
        return False
    print(f"🎯 شکار نقدینگی: {liquidity}")

    mss = check_mss(df_signal, htf_trend, swings_high, swings_low)
    if not mss:
        print(f"❌ تغییر ساختار بازار در {signal_tf} مشاهده نشد")
        if signal_tf == "4h":
            send_status_report(htf_trend, f"نقدینگی شکار شد ({liquidity}) اما ساختار بازار (MSS) تغییر نکرد")
        return False
    print(f"✅ تغییر ساختار بازار: {mss}")

    fvgs = detect_fvg(df_signal, lookback=40)
    target_fvg = None
    for direction, upper, lower in fvgs:
        if (htf_trend == "BULLISH" and direction == "BULLISH") or (htf_trend == "BEARISH" and direction == "BEARISH"):
            target_fvg = (direction, upper, lower)
            break
            
    if not target_fvg:
        print(f"❌ FVG هم‌جهت در {signal_tf} یافت نشد")
        if signal_tf == "4h":
            send_status_report(htf_trend, "تغییر ساختار رخ داد اما FVG هم‌جهت پیدا نشد")
        return False
    print(f"✅ FVG پیدا شد: {target_fvg[0]}")

    last_close = df_signal['close'].iloc[-1]
    fvg_dir, fvg_upper, fvg_lower = target_fvg
    last_candle_confirmed = confirm_candle(df_signal)

    if not last_candle_confirmed:
        print(f"❌ شمع آخر در {signal_tf} تأیید نشد")
        if signal_tf == "4h":
            send_status_report(htf_trend, "الگوها تکمیل شدند اما کندل تایید نهایی صادر نشد")
        return False

    # بخش صدور سیگنال واقعی
    if fvg_dir == "BULLISH" and fvg_lower <= last_close <= fvg_upper and last_close > df_signal['open'].iloc[-1]:
        sl = min(swings_low[-1][1], fvg_lower - (fvg_upper - fvg_lower) * 0.2)
        entry = last_close
        tp = entry + (entry - sl) * RISK_REWARD_RATIO
        send_notification("BUY", entry, sl, tp, signal_tf)
        return True

    elif fvg_dir == "BEARISH" and fvg_lower <= last_close <= fvg_upper and last_close < df_signal['open'].iloc[-1]:
        sl = max(swings_high[-1][1], fvg_upper + (fvg_upper - fvg_lower) * 0.2)
        entry = last_close
        tp = entry - (sl - entry) * RISK_REWARD_RATIO
        send_notification("SELL", entry, sl, tp, signal_tf)
        return True
    
    print(f"⏸️ شرایط نهایی برای {signal_tf} برآورده نشد")
    if signal_tf == "4h":
        send_status_report(htf_trend, "قیمت خارج از محدوده معاملاتی FVG قرار دارد")
    return False

# ======================== ارسال نوتیفیکیشن سیگنال ========================
def send_notification(action, entry, sl, tp, timeframe):
    iran_time = datetime.utcnow() + timedelta(hours=3, minutes=30)
    time_str = iran_time.strftime('%H:%M')
    
    emoji = "🟢" if action == "BUY" else "🔴"
    title = f"{emoji} سیگنال {action} {SYMBOL} ({timeframe})"
    body = f"ورود: {round(entry, 5)}\nحد ضرر: {round(sl, 5)}\nحد سود: {round(tp, 5)}\nنسبت: 1:2\nاستراتژی: FVG + MSS + Sweep\nزمان ایران: {time_str}"
    
    headers = {"Access-Token": PUSHBULLET_TOKEN, "Content-Type": "application/json"}
    payload = {"type": "note", "title": title, "body": body}
    try:
        requests.post(PUSHBULLET_URL, json=payload, headers=headers, timeout=10)
        print(f"📱 اعلان سیگنال {action} ({timeframe}) با موفقیت ارسال شد!")
    except Exception as e:
        print(f"⚠️ خطا در ارسال نوتیفیکیشن: {e}")

# ======================== اجرای اصلی ========================
def run_analysis():
    iran_now = datetime.utcnow() + timedelta(hours=3, minutes=30)
    print("🔄 چرخه تحلیل هوشمند SMC شروع شد...")
    print(f"⏰ زمان ایران: {iran_now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    signals_found = 0
    
    # اول تایم فریم ۱ ساعته را بررسی می‌کنیم (روند ۴ ساعته)
    if analyze_timeframe("1h", "4h", htf_lookback=80, signal_lookback=150):
        signals_found += 1
    
    # سپس ۴ ساعته را بررسی می‌کنیم (روند روزانه). نوتیفیکیشن گزارش وضعیت به این متصل است.
    if analyze_timeframe("4h", "1day", htf_lookback=60, signal_lookback=120):
        signals_found += 1
    
    if signals_found == 0:
        print("\n❌ هیچ سیگنالی در هیچ تایم‌فریمی پیدا نشد.")
    else:
        print(f"\n✅ مجموع سیگنال‌های صادر شده: {signals_found}")

if __name__ == "__main__":
    run_analysis()
