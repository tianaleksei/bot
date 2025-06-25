import pandas as pd
import numpy as np
import time
import requests
from datetime import datetime
import threading
import flask
import json
import os

# ==== CONFIGURATION ====
INITIAL_BALANCE = 200.0
USE_PERCENT = True
RISK_PER_TRADE = 0.15
USE_PAPER_TRADING = True

# Telegram
TELEGRAM_TOKEN = os.getenv("8112838643:AAEEIBuuEBrXzGWNs1CAm6KFv9PDXaLO4h0")
TELEGRAM_CHAT_ID = os.getenv("81109346")

SAVE_FILE = "bot_state.json"
STOP_FILE = "stop_signal.txt"

if os.path.exists(SAVE_FILE):
    with open(SAVE_FILE, 'r') as f:
        saved = json.load(f)
        balance = saved.get("balance", INITIAL_BALANCE)
        trade_log = saved.get("trade_log", [])
else:
    balance = INITIAL_BALANCE
    trade_log = []

price_history = []
report_timer = time.time()

def save_state():
    with open(SAVE_FILE, 'w') as f:
        json.dump({"balance": balance, "trade_log": trade_log}, f)

def get_fake_price():
    base_price = 3500
    volatility = 0.01
    change = np.random.normal(0, volatility)
    price = get_fake_price.last_price * (1 + change)
    get_fake_price.last_price = price
    return round(price, 2)
get_fake_price.last_price = 3500

def calculate_rsi(prices, period=14):
    if len(prices) < period:
        return 50
    delta = np.diff(prices[-period:])
    gains = [d for d in delta if d > 0]
    losses = [-d for d in delta if d < 0]
    gain = np.mean(gains) if gains else 0
    loss = np.mean(losses) if losses else 0
    if loss == 0:
        return 100
    rs = gain / loss
    return round(100 - (100 / (1 + rs)), 2)

def send_telegram_message(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Ошибка Telegram:", e)

def send_telegram_report():
    profit = round(balance - INITIAL_BALANCE, 2)
    percent_profit = round((balance / INITIAL_BALANCE - 1) * 100, 2)
    wins = sum(1 for t in trade_log if t['result'] == 'tp')
    losses = sum(1 for t in trade_log if t['result'] == 'sl')
    winrate = round((wins / len(trade_log)) * 100, 2) if trade_log else 0

    message = (
    f"Ежедневный отчёт (Render)\n"
    f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    f"\n"
    f"Прибыль: {profit} USDT ({percent_profit}%)\n"
    f"Баланс: {round(balance, 2)} USDT\n"
    f"Сделок: {len(trade_log)}\n"
    f"Победы: {wins}\n"
    f"Поражения: {losses}\n"
    f"Winrate: {winrate}%\n"
)
    send_telegram_message(message)

app = flask.Flask(__name__)
@app.route('/')
def home():
    return "Bot is running"

def run_flask():
    app.run(host='0.0.0.0', port=10000)

threading.Thread(target=run_flask).start()

def run_bot_once():
    global balance, trade_log, price_history, report_timer

    price = get_fake_price()
    price_history.append(price)
    if len(price_history) > 100:
        price_history = price_history[-100:]

    rsi = calculate_rsi(price_history)
    entry_signal = rsi < 30 or (len(price_history) > 1 and (price / price_history[-2] - 1) < -0.02)

    if entry_signal:
        size = balance * RISK_PER_TRADE if USE_PERCENT else 10
        tp = price * 1.01
        sl = price * 0.99
        outcome = np.random.choice(['tp', 'sl'], p=[0.6, 0.4])

        if outcome == 'tp':
            balance += size * 0.01
        else:
            balance -= size * 0.01

        trade_log.append({"price": price, "result": outcome, "balance": round(balance, 2)})
        save_state()

    if time.time() - report_timer > 3600:
        send_telegram_report()
        report_timer = time.time()

    save_state()
    time.sleep(30)

def stop_signal_detected():
    return os.path.exists(STOP_FILE)

while True:
    send_telegram_message("✅ Бот запущен на Render. Начинаем работу.")
    try:
        while True:
            run_bot_once()
            if stop_signal_detected():
                send_telegram_message("📴 Получен сигнал остановки. Бот завершает работу.")
                os.remove(STOP_FILE)
                break
    except Exception as e:
        send_telegram_message(f"⚠️ Ошибка: {e}")
        time.sleep(5)
