import os
import random
import asyncio
import logging
import openai
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Initialize API keys
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

# Trigger keywords
TRIGGER_KEYWORDS = ["aleeya", "admin", "salam", "assalamualaikum"]

def should_respond(message_text: str) -> bool:
    """Check if message contains any trigger keywords."""
    if not message_text:
        return False
    message_text = message_text.lower()
    return any(keyword in message_text for keyword in TRIGGER_KEYWORDS)

async def generate_openai_response(user_message: str) -> str:
    """Generate a reply from OpenAI."""
    for attempt in range(3):  # Retry up to 3 times if error
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
            return reply_text.replace("—", "-")
        
        except Exception as e:
            logging.error(f"OpenAI API error (Attempt {attempt + 1}): {e}")
            await asyncio.sleep(2)  # Wait 2 seconds before retry

    return "Maaf, saya mengalami masalah teknikal. Sila cuba sebentar lagi ya."

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main reply handler for incoming messages."""
    user_message = update.message.text

    if not should_respond(user_message):
        return

    delay_seconds = random.randint(33, 66)
    logging.info(f"Delaying reply by {delay_seconds} seconds for natural feel.")
    
    await asyncio.sleep(delay_seconds)

    reply_text = await generate_openai_response(user_message)

    await update.message.reply_text(reply_text)

def main():
    """Start the Telegram bot."""
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), reply))

    logging.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
