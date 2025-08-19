import os
import telebot
import requests
from flask import Flask
from threading import Thread

# ========================
# CONFIG
# ========================
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # put your bot token in Replit secrets
ADMIN_ID = int(os.environ.get("ADMIN_ID", "123456789"))  # your Telegram user ID
bot = telebot.TeleBot(BOT_TOKEN)

# ========================
# KEEP ALIVE (for UptimeRobot ping)
# ========================
app = Flask('')

@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ========================
# BINANCE API HELPER
# ========================
BINANCE_URL = "https://api.binance.com/api/v3"

def get_price(symbol: str):
    try:
        resp = requests.get(f"{BINANCE_URL}/ticker/price", params={"symbol": symbol.upper()})
        data = resp.json()
        return float(data["price"])
    except Exception:
        return None

def get_stats(symbol: str):
    try:
        resp = requests.get(f"{BINANCE_URL}/ticker/24hr", params={"symbol": symbol.upper()})
        data = resp.json()
        return {
            "lastPrice": float(data["lastPrice"]),
            "high": float(data["highPrice"]),
            "low": float(data["lowPrice"]),
            "volume": float(data["volume"]),
            "change": float(data["priceChangePercent"])
        }
    except Exception:
        return None

# ========================
# COMMANDS
# ========================
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if message.chat.type == "private":  # only private chats
        bot.reply_to(message, 
            "👋 Welcome!\n\n"
            "Here are my commands:\n"
            "📊 /price <symbol> → Current price (e.g. /price BTCUSDT)\n"
            "📈 /stats <symbol> → 24h stats (e.g. /stats BTCUSDT)\n"
            "💱 /convert <amount> <from> <to> → Convert (e.g. /convert 1 BTC USDT)\n"
            "🛠️ /say <text> → (Admin only) broadcast"
        )

@bot.message_handler(commands=['price'])
def price_handler(message):
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "❌ Usage: /price BTCUSDT")
        return
    symbol = parts[1].upper()
    price = get_price(symbol)
    if price:
        bot.reply_to(message, f"💰 {symbol} = {price:.2f}")
    else:
        bot.reply_to(message, "❌ Invalid symbol")

@bot.message_handler(commands=['stats'])
def stats_handler(message):
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "❌ Usage: /stats BTCUSDT")
        return
    symbol = parts[1].upper()
    stats = get_stats(symbol)
    if stats:
        reply = (
            f"📊 {symbol} 24h Stats\n"
            f"Price: {stats['lastPrice']:.2f}\n"
            f"High: {stats['high']:.2f}\n"
            f"Low: {stats['low']:.2f}\n"
            f"Volume: {stats['volume']:.2f}\n"
            f"Change: {stats['change']:.2f}%"
        )
        bot.reply_to(message, reply)
    else:
        bot.reply_to(message, "❌ Invalid symbol")

@bot.message_handler(commands=['convert'])
def convert_handler(message):
    parts = message.text.split()
    if len(parts) != 4:
        bot.reply_to(message, "❌ Usage: /convert <amount> <from> <to>")
        return
    try:
        amount = float(parts[1])
        from_symbol = parts[2].upper()
        to_symbol = parts[3].upper()
        symbol = from_symbol + to_symbol
        price = get_price(symbol)
        if not price:
            bot.reply_to(message, "❌ Invalid pair")
            return
        converted = amount * price
        bot.reply_to(message, f"💱 {amount} {from_symbol} = {converted:.4f} {to_symbol}")
    except Exception:
        bot.reply_to(message, "⚠️ Error, check input")

@bot.message_handler(commands=['say'])
def say_handler(message):
    if message.from_user.id == ADMIN_ID:
        text = message.text.replace("/say", "").strip()
        if text:
            bot.send_message(message.chat.id, f"📢 {text}")
        else:
            bot.reply_to(message, "❌ Usage: /say <text>")
    else:
        bot.reply_to(message, "🚫 You are not allowed.")

# ========================
# RUN
# ========================
keep_alive()
print("🤖 Bot is running...")
bot.infinity_polling()
