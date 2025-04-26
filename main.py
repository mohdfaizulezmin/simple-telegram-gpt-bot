import os
import random
import asyncio
import logging
import openai
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

TRIGGER_KEYWORDS = ["aleeya", "admin", "salam", "assalamualaikum"]

def should_respond(message_text: str) -> bool:
    if not message_text:
        return False
    message_text = message_text.lower()
    return any(keyword in message_text for keyword in TRIGGER_KEYWORDS)

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_message = update.message.text

    if not should_respond(user_message):
        return

    delay_seconds = random.randint(33, 66)
    await asyncio.sleep(delay_seconds)

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Anda ialah Aleeya, pembantu rasmi AirAsia Ride. Balas dalam Bahasa Melayu santai, gunakan 'saya' dan 'awak'. "
                        "Jawapan mesti pendek, mesra, sopan. Jawab hanya soalan berkaitan AirAsia Ride (apps, insentif, airport, topup, pemandu). "
                        "Kalau soalan luar topik, balas: 'Maaf, saya hanya bantu berkaitan AirAsia Ride sahaja.'"
                    )
                },
                {
                    "role": "user",
                    "content": user_message,
                },
            ],
            temperature=0.7,
            max_tokens=200,
        )
        reply_text = response.choices[0].message.content.strip()
        reply_text = reply_text.replace("—", "-")
        await update.message.reply_text(reply_text)

    except Exception as e:
        logging.error(f"Error when generating reply: {e}")

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), reply))
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
