import os
import time
import random
import logging
import asyncio
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackContext, filters

# Ambil token dari environment
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN') or exit("🚨Error: TELEGRAM_TOKEN is not set.")

# Setting log untuk debugging
logging.basicConfig(level=logging.INFO)

# Senarai keyword yang bot akan balas
TRIGGER_KEYWORDS = ["salam", "aleeya", "admin"]

# Teks balasan untuk setiap keyword
RESPONSES = {
    "salam": "Waalaikumsalam awak. 🌸 Saya harap awak sihat. Ada apa-apa saya boleh bantu?",
    "aleeya": "Hai awak. Aleeya sentiasa ada untuk bantu awak. 😊 Ada apa-apa yang awak nak tanya?",
    "admin": "Hai admin. Saya di sini kalau ada apa-apa nak dibantu. 😊 Cerita je pada saya ya."
}

# Fungsi utama bila terima mesej
async def handle_message(update: Update, context: CallbackContext):
    # Dapatkan mesej user dan ubah ke huruf kecil
    text = (update.message.text or "").lower()

    # Cek kalau ada perkataan trigger
    if any(keyword in text for keyword in TRIGGER_KEYWORDS):
        await asyncio.sleep(random.randint(33, 60))  # Delay antara 33-60 saat
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

        # Cari keyword yang sesuai untuk jawab
        for keyword in TRIGGER_KEYWORDS:
            if keyword in text:
                await update.message.reply_text(RESPONSES[keyword])
                break

    # Jawab salam umum (kalau user cuma taip "salam")
    elif text.strip() == "salam":
        await asyncio.sleep(random.randint(33, 60))
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        await update.message.reply_text(RESPONSES["salam"])

    # Kalau mesej random atau huruf rawak, bot diam
    else:
        logging.info(f"Ignored random message: {text}")
        return

# Command /start
async def command_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Hai, saya Aleeya. Awak boleh taip 'salam', 'admin' atau panggil nama saya 'aleeya' untuk saya bantu.")

# Fungsi utama untuk run bot
def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Register command /start
    application.add_handler(CommandHandler('start', command_start))

    # Register mesej biasa
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

    # Run bot
    print("Bot sedang berjalan...")
    application.run_polling()

if __name__ == "__main__":
    main()
