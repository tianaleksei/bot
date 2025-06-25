import os
import time
import json
import numpy as np
from flask import Flask

app = Flask(__name__)

# === Telegram config ===
import requests
BOT_TOKEN = "8112838643:AAEEIBuuEBrXzGWNs1CAm6KFv9PDXaLO4h0"
CHAT_ID = "8112838643"

# === Constants ===
STATE_FILE = "state.json"
STOP_FILE = "stop"

# === Initial state ===
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"balance": 100.0, "trade_log": [], "report_timer": time.time(), "open_trade": None}

def save_state():
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

state = load_state()
balance = state.get("balance", 100.0)
trade_log = state.get("trade_log", [])
report_timer = state.get("report_timer", time.time())
open_trade = state.get("open_trade")

# === Telegram ===
def send_telegram_message(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Telegram error: {e}")

def send_telegram_report():
    message = "📊 Ежедневный отчёт (Render)\n"
    for t in trade_log[-10:]:
        message += f"Цена: {t['price']}, Результат: {t['result']}, Баланс: {t['balance']}\n"
    send_telegram_message(message)
    print("📤 Отправлен Telegram отчёт")

# === Bot logic ===
def get_price():
    return round(np.random.uniform(30000, 40000), 2)

def run_bot_once():
    global balance, trade_log, report_timer, open_trade

    price = get_price()
    print(f"🔄 Проверка рынка. Цена: {price}")

    if open_trade:
        print("📈 Есть открытая сделка, проверяем TP/SL")
        entry = open_trade['entry_price']
        direction = open_trade['direction']
        tp = open_trade['tp']
        sl = open_trade['sl']

        if (direction == "long" and price >= tp) or (direction == "short" and price <= tp):
            result = "tp"
            balance += 0.01 * price
        elif (direction == "long" and price <= sl) or (direction == "short" and price >= sl):
            result = "sl"
            balance -= 0.01 * price
        else:
            print("💤 Сделка в рынке. TP/SL не достигнуты.")
            return

        trade_log.append({"price": price, "result": result, "balance": round(balance, 2)})
        open_trade = None
        print(f"✅ Сделка закрыта по {result.upper()}. Баланс: {round(balance, 2)}")

    else:
        entry_price = price
        tp = entry_price * 1.01
        sl = entry_price * 0.99
        open_trade = {"entry_price": entry_price, "direction": "long", "tp": tp, "sl": sl}
        print(f"📥 Открыта сделка: Long {entry_price}, TP: {tp}, SL: {sl}")

    state["balance"] = balance
    state["trade_log"] = trade_log
    state["report_timer"] = report_timer
    state["open_trade"] = open_trade
    save_state()

    if time.time() - report_timer > 3600:
        send_telegram_report()
        report_timer = time.time()

    time.sleep(30)

def stop_signal_detected():
    return os.path.exists(STOP_FILE)

@app.route("/")
def index():
    return "Bot is running."

if __name__ == "__main__":
    send_telegram_message("✅ Бот запущен на Render. Начинаем работу.")
    print("✅ Бот запущен на Render")

    try:
        while True:
            run_bot_once()
            if stop_signal_detected():
                send_telegram_message("🛑 Получен сигнал остановки. Бот завершает работу.")
                os.remove(STOP_FILE)
                break
    except Exception as e:
        send_telegram_message(f"⚠️ Ошибка: {e}")
        print(f"⚠️ Ошибка: {e}")
