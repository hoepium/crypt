import os
import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ================== CONFIG ==================
TOKEN = os.getenv("BOT_TOKEN")  # put your Telegram bot token in Replit secrets
ADMIN_ID = int(os.getenv("ADMIN_ID", "123456789"))  # your Telegram user id
BINANCE_API = "https://api.binance.com/api/v3/ticker/24hr"

# Flask app for webhook
app = Flask(__name__)

# Telegram bot application
application = Application.builder().token(TOKEN).build()

# ============== HELPER FUNCTIONS ==============
def get_binance_price(symbol: str):
    try:
        url = f"{BINANCE_API}?symbol={symbol.upper()}USDT"
        data = requests.get(url).json()
        return {
            "symbol": symbol.upper(),
            "price": data["lastPrice"],
            "change": data["priceChangePercent"]
        }
    except Exception:
        return None

# ============== COMMAND HANDLERS ==============
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        await update.message.reply_text(
            "👋 Hey! I’m your Crypto Bot.\n\n"
            "Available commands:\n"
            "/price <symbol> → Get current price\n"
            "/change <symbol> → 24h price change\n"
            "/send <chat_id> <message> → (admin only)"
        )

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /price BTC")
        return
    coin = context.args[0].upper()
    data = get_binance_price(coin)
    if data:
        await update.message.reply_text(
            f"💰 {data['symbol']} Price: ${data['price']}"
        )
    else:
        await update.message.reply_text("❌ Invalid symbol or API error.")

async def change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /change BTC")
        return
    coin = context.args[0].upper()
    data = get_binance_price(coin)
    if data:
        await update.message.reply_text(
            f"📊 {data['symbol']} 24h Change: {data['change']}%"
        )
    else:
        await update.message.reply_text("❌ Invalid symbol or API error.")

async def send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 You are not allowed to use this.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("⚠️ Usage: /send <chat_id> <message>")
        return
    chat_id = context.args[0]
    msg = " ".join(context.args[1:])
    try:
        await context.bot.send_message(chat_id, msg)
        await update.message.reply_text("✅ Message sent.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# ============== REGISTER HANDLERS ==============
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("price", price))
application.add_handler(CommandHandler("change", change))
application.add_handler(CommandHandler("send", send))

# ============== FLASK WEBHOOK ENDPOINT ==============
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "ok", 200

@app.route("/", methods=["GET"])
def index():
    return "Bot is running!", 200

# ============== RUN ==============
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
