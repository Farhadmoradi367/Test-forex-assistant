import requests
import pandas as pd
import numpy as np
import sys
import json

# ======================== تنظیمات اصلی ========================
SYMBOL = "EUR/USD"
TWELVEDATA_API_KEY = "0ae022a265924aa98ec6084f6de7b353"
TWELVEDATA_BASE_URL = "https://api.twelvedata.com/time_series"

PUSHBULLET_TOKEN = "o.S9w7mC9uR7v60q8A8bH7k2N9z7X5c3V1" # توکن فعال شما
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

# ======================== موتور سیگنال ========================
def run_analysis():
    print("🔄 چرخه تحلیل هوشمند SMC (15 دقیقه) شروع شد...")
    df_1h = fetch_klines(SYMBOL, "1h", limit=100)
    df_15m = fetch_klines(SYMBOL, "15min", limit=200)
    
    if df_1h is None or df_15m is None:
        print("❌ خطا در دریافت اطلاعات از سرور.")
        return

    htf_trend = get_htf_bias(df_1h)
    print(f"📈 روند تایم‌فریم بالا (1H): {htf_trend}")
    if htf_trend == "NEUTRAL": return

    swings_high, swings_low = find_swings(df_15m, lookback=7)
    if not swings_high or not swings_low: return

    liquidity = is_liquidity_swept(df_15m, swings_high, swings_low)
    if not liquidity:
        print("🟢 نقدینگی شکار نشد. خروج امن.")
        return
    print(f"🎯 شکار نقدینگی: {liquidity}")

    mss = check_mss(df_15m, htf_trend, swings_high, swings_low)
    if not mss: return

    fvgs = detect_fvg(df_15m, lookback=40)
    target_fvg = None
    for direction, upper, lower in fvgs:
        if (htf_trend == "BULLISH" and direction == "BULLISH") or (htf_trend == "BEARISH" and direction == "BEARISH"):
            target_fvg = (direction, upper, lower)
            break
            
    if not target_fvg: return

    last_close = df_15m['close'].iloc[-1]
    fvg_dir, fvg_upper, fvg_lower = target_fvg

    # صادر کردن سیگنال نهایی
    if fvg_dir == "BULLISH" and fvg_lower <= last_close <= fvg_upper and confirm_candle(df_15m) and last_close > df_15m['open'].iloc[-1]:
        sl = min(swings_low[-1][1], fvg_lower - (fvg_upper - fvg_lower) * 0.2)
        entry = last_close
        tp = entry + (entry - sl) * RISK_REWARD_RATIO
        send_notification("BUY", entry, sl, tp)

    elif fvg_dir == "BEARISH" and fvg_lower <= last_close <= fvg_upper and confirm_candle(df_15m) and last_close < df_15m['open'].iloc[-1]:
        sl = max(swings_high[-1][1], fvg_upper + (fvg_upper - fvg_lower) * 0.2)
        entry = last_close
        tp = entry - (sl - entry) * RISK_REWARD_RATIO
        send_notification("SELL", entry, sl, tp)

def send_notification(action, entry, sl, tp):
    emoji = "🟢" if action == "BUY" else "🔴"
    title = f"{emoji} سیگنال {action} {SYMBOL} (15Min)"
    body = f"ورود: {round(entry, 5)}\nحد ضرر: {round(sl, 5)}\nحد سود: {round(tp, 5)}\nنسبت: 1:2\nاستراتژی: FVG + MSS + Sweep"
    
    headers = {"Access-Token": PUSHBULLET_TOKEN, "Content-Type": "application/json"}
    payload = {"type": "note", "title": title, "body": body}
    requests.post(PUSHBULLET_URL, json=payload, headers=headers)
    print(f"📱 اعلان سیگنال {action} با موفقیت به گوشی فرستاده شد!")

if __name__ == "__main__":
    run_analysis()
        
