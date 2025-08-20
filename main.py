import os
import json
import requests
from telegram import Update, Chat
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, filters

# CoinGecko API base URL (free tier, no API key needed for basic endpoints)
COINGECKO_API = "https://api.coingecko.com/api/v3"

# File to store user IDs for broadcasting (persists on Replit)
USERS_FILE = "users.json"

# Load stored user IDs
def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return set(json.load(f))
    except FileNotFoundError:
        return set()

# Save user IDs
def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(list(users), f)

users = load_users()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user_id = update.effective_user.id
    
    if chat.type == Chat.PRIVATE:
        # Add user to broadcast list if not already
        users.add(user_id)
        save_users(users)
        
        greeting = (
            "👋 Welcome to the Crypto Bot!\n"
            "I can help with real-time crypto prices and conversions.\n\n"
            "Commands:\n"
            "- /price <symbol> (e.g., /price BTC)\n"
            "- /convert <amount> <from> <to> (e.g., /convert 1 BTC ETH)\n"
            "- /fiat <amount> <crypto> <currency> (e.g., /fiat 1 BTC INR)\n\n"
            "Type a command to get started! 🚀"
        )
        await update.message.reply_text(greeting)

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    admin_id = int(os.getenv("ADMIN_ID", 0))  # Set this in Replit Secrets
    if update.effective_user.id != admin_id:
        await update.message.reply_text("🚫 Access denied. This command is for admins only.")
        return
    
    if not context.args:
        await update.message.reply_text("🚫 Usage: /broadcast <message>")
        return
    
    message = " ".join(context.args)
    successful = 0
    failed = 0
    
    for user_id in list(users):  # Copy to avoid modification issues
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            successful += 1
        except Exception:
            failed += 1
            # Optionally remove blocked users: users.remove(user_id); save_users(users)
    
    await update.message.reply_text(f"📢 Broadcast sent to {successful} users ({failed} failed).")

async def sendgroup(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    admin_id = int(os.getenv("ADMIN_ID", 0))
    if update.effective_user.id != admin_id:
        await update.message.reply_text("🚫 Access denied. This command is for admins only.")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("🚫 Usage: /sendgroup <group_id> <message>")
        return
    
    try:
        group_id = int(context.args[0])
        message = " ".join(context.args[1:])
        await context.bot.send_message(chat_id=group_id, text=message)
        await update.message.reply_text(f"📢 Message sent to group {group_id}.")
    except ValueError:
        await update.message.reply_text("❌ Invalid group ID. It must be a number (e.g., -1001234567890).")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to send: {str(e)} (Ensure bot is in the group with permissions).")

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("🚫 Usage: /price <crypto_symbol> (e.g., /price BTC)")
        return

    symbol = context.args[0].lower()
    try:
        response = requests.get(f"{COINGECKO_API}/simple/price?ids={symbol}&vs_currencies=usd,inr")
        response.raise_for_status()
        data = response.json()
         if symbol not in data or not data[symbol]:
             raise ValueError("Invalid cryptocurrency symbol")
        
        usd_price = data[symbol]['usd']
        inr_price = data[symbol]['inr']
        
        await update.message.reply_text(
            f"💰 {symbol.upper()} Price:\n"
            f"USD: ${usd_price:,.2f}\n"
            f"INR: ₹{inr_price:,.2f}"
        )
    except requests.RequestException as e:
        await update.message.reply_text(f"❌ Error fetching data from API: {str(e)}. Please try again later.")
    except ValueError:
        await update.message.reply_text("🚫 Invalid cryptocurrency symbol. Please check and try again.")

async def convert(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 3:
        await update.message.reply_text("🚫 Usage: /convert <amount> <from_crypto> <to_crypto> (e.g., /convert 1 BTC ETH)")
        return

    try:
        amount = float(context.args[0])
        from_symbol = context.args[1].lower()
        to_symbol = context.args[2].lower()
        
        response = requests.get(f"{COINGECKO_API}/simple/price?ids={from_symbol},{to_symbol}&vs_currencies=usd")
        response.raise_for_status()
        data = response.json()
        
        if from_symbol not in data or to_symbol not in data:
            raise ValueError("Invalid cryptocurrency symbols")
        
        from_price_usd = data[from_symbol]['usd']
        to_price_usd = data[to_symbol]['usd']
        
        equivalent = amount * (from_price_usd / to_price_usd)
        
        await update.message.reply_text(
            f"🔄 Conversion:\n"
            f"{amount} {from_symbol.upper()} = {equivalent:,.4f} {to_symbol.upper()}"
        )
    except (ValueError, requests.RequestException) as e:
        await update.message.reply_text(f"❌ Error: Invalid input or API issue ({str(e)}). Please check symbols and try again.")

async def fiat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if len(context.args) != 3:
        await update.message.reply_text("🚫 Usage: /fiat <amount> <crypto> <currency> (e.g., /fiat 1 BTC INR)")
        return

    try:
        amount = float(context.args[0])
        symbol = context.args[1].lower()
        currency = context.args[2].lower()
        
        response = requests.get(f"{COINGECKO_API}/simple/price?ids={symbol}&vs_currencies={currency}")
        response.raise_for_status()
        data = response.json()
        
        if symbol not in data or currency not in data[symbol]:
            raise ValueError("Invalid cryptocurrency symbol or currency")
        
        fiat_price = data[symbol][currency]
        converted = amount * fiat_price
        
        await update.message.reply_text(
            f"💵 Conversion:\n"
            f"{amount} {symbol.upper()} = {converted:,.2f} {currency.upper()}"
        )
    except (ValueError, requests.RequestException) as e:
        await update.message.reply_text(f"❌ Error: Invalid input or API issue ({str(e)}). Please check symbols/currency and try again.")

def main() -> None:
    token = os.getenv("TELEGRAM_TOKEN")
    admin_id = os.getenv("ADMIN_ID")  # Add this in Replit Secrets as your Telegram user ID
    if not token:
        raise ValueError("TELEGRAM_TOKEN environment variable not set")
    if not admin_id:
        print("Warning: ADMIN_ID not set. Admin features won't work.")

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast, filters=filters.ChatType.PRIVATE))  # Restrict to private for security
    app.add_handler(CommandHandler("sendgroup", sendgroup, filters=filters.ChatType.PRIVATE))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("convert", convert))
    app.add_handler(CommandHandler("fiat", fiat))

    app.run_polling()

if name == "main":
    main()
        
        if symbol not in data or not data[symbol]:
