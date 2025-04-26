# Import semua library yang diperlukan
import os
import random
import asyncio  # Untuk buat delay masa jawab
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
import openai

# Dapatkan API Key dan Token dari environment variable
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Senarai trigger perkataan yang akan buat bot balas
TRIGGER_KEYWORDS = ["aleeya", "admin", "salam", "assalamualaikum"]

# Function untuk detect sama ada mesej nak dibalas atau tidak
def should_respond(message_text: str) -> bool:
    if not message_text:
        return False
    message_text = message_text.lower()
    return any(keyword in message_text for keyword in TRIGGER_KEYWORDS)

# Function utama untuk balas mesej
async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    if not should_respond(user_message):
        # Jika tiada keyword, bot akan diam
        return

    # Delay antara 33 hingga 66 saat sebelum balas
    delay_seconds = random.randint(33, 66)
    await asyncio.sleep(delay_seconds)

    try:
        # Guna OpenAI API untuk generate jawapan ringkas
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Model paling murah
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Jawab dalam Bahasa Melayu santai menggunakan 'saya' dan 'awak'. "
                        "Jawapan mesti pendek, sopan, dan mesra seperti berbual. "
                        "Hanya jawab soalan berkaitan jika disebut 'aleeya', 'admin', atau salam."
                    ),
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
            temperature=0.5,
            max_tokens=150,
        )
        reply_text = response.choices[0].message.content.strip()
        # Hantar balasan ke Telegram
        await update.message.reply_text(reply_text)

    except Exception as e:
        logging.error(f"Error when generating reply: {e}")

# Function utama untuk jalankan bot
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Set handler bila ada mesej masuk
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), reply))

    print("Bot is running...")
    app.run_polling()

# Kalau file ini yang dijalankan, terus start main()
if __name__ == "__main__":
    main()
