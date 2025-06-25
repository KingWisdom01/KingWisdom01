import os
import asyncio
import json
import ssl
import math
from collections import deque, defaultdict

import websockets
import aiohttp

# Load credentials from environment variables
DERIV_TOKEN = os.environ.get("DERIV_API_TOKEN")
DERIV_APP_ID = os.environ.get("DERIV_APP_ID")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if not all([DERIV_TOKEN, DERIV_APP_ID, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
    raise EnvironmentError("Missing API credentials in environment variables")

SYMBOLS = [
    "R_10", "R_25", "R_50", "R_75", "R_100",
    "1HZ10V", "1HZ25V", "1HZ50V", "1HZ75V", "1HZ100V",
    "1HZ150V", "1HZ200V", "1HZ300V",
    "BOOM_500", "BOOM_1000", "CRASH_500", "CRASH_1000",
    "STEP_10", "STEP_25", "STEP_50", "STEP_100",
    "JD10", "JD25", "JD50", "JD75", "JD100",
]

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

candles = defaultdict(list)  # symbol -> list of candle dicts
current_candle = {}

def update_candle(symbol, price, epoch):
    minute = epoch - epoch % 60
    candle = current_candle.get(symbol)
    if candle is None:
        candle = {
            "start": minute,
            "open": price,
            "high": price,
            "low": price,
            "close": price,
        }
        current_candle[symbol] = candle
    elif candle["start"] == minute:
        candle["high"] = max(candle["high"], price)
        candle["low"] = min(candle["low"], price)
        candle["close"] = price
    else:
        candles[symbol].append(candle)
        current_candle[symbol] = {
            "start": minute,
            "open": price,
            "high": price,
            "low": price,
            "close": price,
        }
        if len(candles[symbol]) > 200:
            candles[symbol] = candles[symbol][-200:]


def check_bullish_engulfing(prev, cur):
    return (
        prev["open"] > prev["close"] and
        cur["open"] < cur["close"] and
        cur["open"] <= prev["close"] and
        cur["close"] >= prev["open"]
    )


def check_bearish_engulfing(prev, cur):
    return (
        prev["close"] > prev["open"] and
        cur["close"] < cur["open"] and
        cur["close"] <= prev["open"] and
        cur["open"] >= prev["close"]
    )


def support_resistance_break(symbol, price):
    data = candles[symbol][-20:]
    if len(data) < 20:
        return None
    highs = [c["high"] for c in data]
    lows = [c["low"] for c in data]
    resistance = max(highs)
    support = min(lows)
    if price > resistance:
        return "Resistance Break"
    if price < support:
        return "Support Break"
    return None


def trend_line_break(symbol, price):
    data = candles[symbol][-30:]
    if len(data) < 30:
        return False
    x = list(range(len(data)))
    closes = [c["close"] for c in data]
    n = len(data)
    x_mean = sum(x) / n
    y_mean = sum(closes) / n
    num = sum((x[i] - x_mean) * (closes[i] - y_mean) for i in range(n))
    den = sum((x[i] - x_mean) ** 2 for i in range(n)) or 1
    slope = num / den
    intercept = y_mean - slope * x_mean
    trend_price = slope * (n - 1) + intercept
    prev_trend_price = slope * (n - 2) + intercept
    prev_close = closes[-1]
    return (prev_close <= prev_trend_price and price > trend_price) or (
        prev_close >= prev_trend_price and price < trend_price
    )


async def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    async with aiohttp.ClientSession() as session:
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
        await session.post(url, data=payload)


async def process_tick(data):
    tick = data["tick"]
    symbol = tick["symbol"]
    price = float(tick["quote"])
    epoch = int(tick["epoch"])

    update_candle(symbol, price, epoch)
    candle_list = candles[symbol]
    if len(candle_list) < 2:
        return
    prev, cur = candle_list[-2], candle_list[-1]
    alerts = []
    if check_bullish_engulfing(prev, cur):
        alerts.append("Bullish Engulfing")
    if check_bearish_engulfing(prev, cur):
        alerts.append("Bearish Engulfing")
    sr = support_resistance_break(symbol, price)
    if sr:
        alerts.append(sr)
    if trend_line_break(symbol, price):
        alerts.append("Trend Line Break")
    if alerts:
        msg = f"\u26a0\ufe0f PATTERN ALERT\nSymbol: {symbol}\n" + ", ".join(alerts)
        await send_telegram(msg)


async def main():
    url = f"wss://ws.binaryws.com/websockets/v3?app_id={DERIV_APP_ID}"
    async with websockets.connect(url, ssl=ssl_context) as ws:
        await ws.send(json.dumps({"authorize": DERIV_TOKEN, "req_id": 1}))
        await ws.recv()  # authorization response
        for symbol in SYMBOLS:
            await ws.send(json.dumps({"ticks": symbol, "subscribe": 1}))
        while True:
            data = json.loads(await ws.recv())
            if "tick" in data:
                await process_tick(data)


if __name__ == "__main__":
    asyncio.run(main())
