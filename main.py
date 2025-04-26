# Import library
import argparse, json, logging, os, random, time, openai, asyncio, requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# Set API token
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN') or exit("Error: TELEGRAM_TOKEN not set.")
openai.api_key = os.getenv('OPENAI_API_KEY') or None
SESSION_DATA = {}

# Load configuration
def load_configuration():
    with open('configuration.json', 'r') as file:
        return json.load(file)

CONFIG = load_configuration()
SYSTEM_PROMPT = CONFIG.get('system_prompt', 'Saya ialah pembantu anda dalam Telegram.')
VALID_MODELS = CONFIG.get('valid_models', {})
VISION_MODELS = CONFIG.get('vision_models', [])

# Hantar pertanyaan ke OpenAI
async def ask_openai(session_data, user_message):
    try:
        response = await openai.ChatCompletion.acreate(
            model=session_data['model'],
            messages=[
                {"role": "system", "content": session_data['system_prompt']},
                {"role": "user", "content": user_message}
            ],
            temperature=session_data['temperature'],
            max_tokens=session_data['max_tokens'] if session_data['max_tokens'] else 500
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return "Maaf, ada masalah teknikal. 🌸"

# Filter sama ada perlu jawab atau diam
def should_respond(text):
    text = text.lower()
    keywords = ['aleeya', 'admin', 'salam', 'assalamualaikum', 'waalaikumsalam']
    return any(keyword in text for keyword in keywords)

# Delay sebelum reply untuk nampak natural
async def delayed_response(update: Update, text: str):
    delay_seconds = random.randint(33, 60)  # random delay 33-60 saat
    await asyncio.sleep(delay_seconds)
    await update.message.reply_text(text)

# Bila user hantar mesej
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    user_message = update.message.text.strip()

    # Check sama ada perlu respond
    if should_respond(user_message):
        session_id = str(update.effective_chat.id)
        if session_id not in SESSION_DATA:
            SESSION_DATA[session_id] = {
                "model": "gpt-4o",
                "temperature": 0.6,
                "max_tokens": 500,
                "system_prompt": "Jawab semua soalan dengan gaya santai dan sopan, guna perkataan saya dan awak. Jawapan pendek dalam 1-2 perenggan maksimum."
            }
        
        session_data = SESSION_DATA[session_id]

        # Hantar pertanyaan ke OpenAI
        reply_text = await ask_openai(session_data, user_message)
        
        # Buang simbol dash (–) dalam jawapan
        reply_text = reply_text.replace("—", "").replace("–", "")

        # Jawab selepas delay
        await delayed_response(update, reply_text)
    else:
        # Kalau tak sebut nama atau salam, diam
        return

# Command /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hai! 🌸 Saya di sini kalau awak perlukan bantuan.")

# Setup telegram bot
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # Connect telegram bot
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot is running...")
    app.run_polling()

if __name__ == '__main__':
    main()
