import telebot
from telebot.types import Message
from flask import Flask, request
from threading import Thread
import os

# Load from environment variables (keep these in Render's settings)
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")

# Create the bot
bot = telebot.TeleBot(BOT_TOKEN)

# Create Flask app
app = Flask(__name__)

# Set webhook once when app starts
@app_got_first_request
def set_webhook():
    webhook_url = f"https://anon-deal-bot.onrender.com/{WEBHOOK_SECRET}"
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)

# Handle webhook calls
@app.route(f"/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.data.decode("utf-8"))
    bot.process_new_updates([update])
    return "ok", 200

# Flask runner
def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Bot logic below
ADMIN_ID = 754292820
GROUP_ID = -1002792963711

session = {
    "buyer": None,
    "seller": None,
    "active": False
}

@bot.message_handler(commands=['start'])
def send_welcome(message: Message):
    bot.send_message(message.chat.id, "Welcome! Please wait for admin instructions.")

@bot.message_handler(commands=['setbuyer'])
def set_buyer(message: Message):
    if message.from_user.id != ADMIN_ID:
        return bot.send_message(message.chat.id, "❌ Only admin can set the buyer.")
    if session["active"]:
        return bot.send_message(message.chat.id, "⚠️ A deal is already in progress.")
    try:
        session["buyer"] = int(message.text.split()[1])
        bot.send_message(GROUP_ID, f"✅ Buyer set: {session['buyer']}")
    except:
        bot.send_message(message.chat.id, "⚠️ Usage: /setbuyer <user_id>")

@bot.message_handler(commands=['setseller'])
def set_seller(message: Message):
    if message.from_user.id != ADMIN_ID:
        return bot.send_message(message.chat.id, "❌ Only admin can set the seller.")
    if session["active"]:
        return bot.send_message(message.chat.id, "⚠️ A deal is already in progress.")
    if not session["buyer"]:
        return bot.send_message(message.chat.id, "⚠️ Set the buyer first.")
    try:
        session["seller"] = int(message.text.split()[1])
        session["active"] = True
        bot.send_message(session["buyer"], "👤 Seller connected. You may begin the deal.")
        bot.send_message(session["seller"], "🛒 You are now connected with the buyer.")
        bot.send_message(GROUP_ID, "🔗 Deal started.")
    except:
        bot.send_message(message.chat.id, "⚠️ Usage: /setseller <user_id>")

@bot.message_handler(commands=['end'])
def end_session(message: Message):
    if message.from_user.id != ADMIN_ID:
        return bot.send_message(message.chat.id, "❌ Only admin can end the session.")
    if session["active"]:
        try:
            if session["buyer"]:
                bot.send_message(session["buyer"], "❌ Deal ended by admin.")
            if session["seller"]:
                bot.send_message(session["seller"], "❌ Deal ended by admin.")
        except Exception as e:
            print(f"Error ending deal: {e}")
        bot.send_message(GROUP_ID, "✅ Session ended.")
        session.update({"buyer": None, "seller": None, "active": False})
    else:
        bot.send_message(message.chat.id, "⚠️ No active session to end.")

@bot.message_handler(func=lambda m: True)
def forward_all(message: Message):
    if message.chat.id != GROUP_ID:
        bot.send_message(GROUP_ID, f"📩 From @{message.from_user.username or 'Unknown'} (ID: {message.from_user.id}):\n{message.text}")

    if session["active"]:
        if message.from_user.id == session["buyer"]:
            bot.send_message(session["seller"], f"Buyer: {message.text}")
        elif message.from_user.id == session["seller"]:
            bot.send_message(session["buyer"], f"Seller: {message.text}")
        elif message.chat.id == GROUP_ID and message.from_user.id == ADMIN_ID:
            if session["buyer"]:
                bot.send_message(session["buyer"], f"Admin: {message.text}")
            if session["seller"]:
                bot.send_message(session["seller"], f"Admin: {message.text}")

# Start server on Render
if __name__ == "__main__":
    print("Bot is running...")
    keep_alive()
