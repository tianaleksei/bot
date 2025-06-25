import os
import time
import json
import threading
import requests
from datetime import datetime
import numpy as np
from flask import Flask, request

# Конфигурация из переменных окружения
TELEGRAM_TOKEN = os.getenv("8112838643:AAEEIBuuEBrXzGWNs1CAm6KFv9PDXaLO4h0")
TELEGRAM_CHAT_ID = os.getenv("81109346")
BYBIT_API_KEY = os.getenv("oeWLdV0sj3FODLhzLD")
BYBIT_SECRET = os.getenv("S5r8m0YVbdWUAJU0o5EyVdXikqwox72jwi4T")

SAVE_FILE = "bot_state.json"

INITIAL_BALANCE = 200.0
RISK_PER_TRADE = 0.15

state = {
    "balance": INITIAL_BALANCE,
    "trade_log": [],
    "running": True,
}

def save_state():
    with open(SAVE_FILE, "w") as f:
        json.dump(state, f)

def load_state():
    if os.path.exists(SAVE_FILE):
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
            state.update(data)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        requests.post(url, data=data)
    except Exception as e:
        print("Ошибка отправки в Telegram:", e)

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

price_history = []
report_timer = time.time()

def send_daily_report():
    profit = round(state["balance"] - INITIAL_BALANCE, 2)
    percent_profit = round((state["balance"] / INITIAL_BALANCE - 1) * 100, 2)
    wins = sum(1 for t in state["trade_log"] if t['result'] == 'tp')
    losses = sum(1 for t in state["trade_log"] if t['result'] == 'sl')
    winrate = round((wins / len(state["trade_log"])) * 100, 2) if state["trade_log"] else 0

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

    send_telegram_message(msg)

def bot_loop():
    global price_history, report_timer
    send_telegram_message("Бот запущен и работает.")
    while state["running"]:
        price = get_fake_price()
        price_history.append(price)
        if len(price_history) > 100:
            price_history = price_history[-100:]

        rsi = calculate_rsi(price_history)
        entry_signal = rsi < 30 or (len(price_history) > 1 and (price / price_history[-2] - 1) < -0.02)

        if entry_signal:
            size = state["balance"] * RISK_PER_TRADE
            result = np.random.choice(['tp', 'sl'], p=[0.6, 0.4])
            if result == 'tp':
                profit = size * 0.01
                state["balance"] += profit
            else:
                loss = size * 0.01
                state["balance"] -= loss
            state["trade_log"].append({"price": price, "result": result, "balance": round(state["balance"], 2)})
            save_state()

        if time.time() - report_timer >= 1800:
            send_daily_report()
            report_timer = time.time()

        time.sleep(30)

app = Flask(__name__)

@app.route('/')
def index():
    return "Бот активен."

if __name__ == '__main__':
    load_state()
    threading.Thread(target=bot_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
