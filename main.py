import argparse, json, logging, os, openai, random, asyncio
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackContext, filters

# Ambil token dan API key dari environment
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN') or exit("🚨Error: TELEGRAM_TOKEN is not set.")
openai.api_key = os.getenv('OPENAI_API_KEY') or None
SESSION_DATA = {}

# Load setting default
def load_configuration():
    with open('configuration.json', 'r') as file:
        return json.load(file)

# Dapatkan session ID berdasarkan chat
def get_session_id(func):
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        session_id = str(update.effective_chat.id if update.effective_chat.type in ['group', 'supergroup'] else update.effective_user.id)
        return await func(update, context, session_id, *args, **kwargs)
    return wrapper

# Pastikan session data wujud
def initialize_session_data(func):
    async def wrapper(update: Update, context: CallbackContext, session_id, *args, **kwargs):
        if session_id not in SESSION_DATA:
            SESSION_DATA[session_id] = load_configuration()['default_session_values']
        return await func(update, context, session_id, *args, **kwargs)
    return wrapper

# Semak kalau OpenAI API Key dah set
def check_api_key(func):
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        if not openai.api_key:
            await update.message.reply_text("⚠️ Sila set OpenAI API Key: /set openai_api_key THE_API_KEY")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# Relay error supaya tak crash
def relay_errors(func):
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            await update.message.reply_text(f"Error berlaku: {e}")
    return wrapper

CONFIGURATION = load_configuration()
VISION_MODELS = CONFIGURATION.get('vision_models', [])
VALID_MODELS = CONFIGURATION.get('VALID_MODELS', {})
FAQ = CONFIGURATION.get('faq', {})  # auto detect FAQ

@relay_errors
@get_session_id
@initialize_session_data
@check_api_key
async def handle_message(update: Update, context: CallbackContext, session_id):
    message_text = update.message.text.lower()

    # Jawab hanya jika ada "aleeya" atau "admin" atau salam
    allowed_keywords = ['aleeya', 'admin', 'assalamualaikum', 'salam', 'hai', 'hi', 'hello']
    if not any(word in message_text for word in allowed_keywords):
        return  # Abaikan mesej lain

    # Delay antara 33 ke 60 saat sebelum jawab
    await asyncio.sleep(random.randint(33, 60))

    # Bersihkan karakter pelik
    clean_text = message_text.replace("—", "-").replace("–", "-").strip()

    # Kalau mesej salam
    if any(salam in clean_text for salam in ['assalamualaikum', 'salam', 'hi', 'hai', 'hello']):
        reply = "Waalaikumsalam awak. 🌸 Apa yang boleh saya bantu hari ini? Cerita sikit ya."
        await update.message.reply_text(reply)
        return

    # Auto detect FAQ
    for keyword, answer in FAQ.items():
        if keyword.lower() in clean_text:
            await update.message.reply_text(answer)
            return

    # Jawapan default kalau keyword dipanggil
    reply = f"Hai, saya Aleeya. Awak panggil saya ke? 🌸 Ada apa-apa soalan atau nak bersembang?"
    await update.message.reply_text(reply)

async def response_from_openai(model, messages, temperature, max_tokens):
    params = {'model': model, 'messages': messages, 'temperature': temperature}
    if model == "gpt-4-vision-preview":
        max_tokens = 4096
    if max_tokens is not None: 
        params['max_tokens'] = max_tokens
    return openai.chat.completions.create(**params).choices[0].message.content

async def command_start(update: Update, context: CallbackContext):
    await update.message.reply_text("ℹ️ Bot Aleeya sudah aktif! Taip apa-apa untuk mula bersembang ya.")

@get_session_id
async def command_reset(update: Update, context: CallbackContext, session_id):
    if session_id in SESSION_DATA:
        del SESSION_DATA[session_id]
        await update.message.reply_text("ℹ️ Semua setting sudah reset.")

@get_session_id
async def command_clear(update: Update, context: CallbackContext, session_id):
    if session_id in SESSION_DATA:
        SESSION_DATA[session_id]['chat_history'] = []
        await update.message.reply_text("ℹ️ Sejarah perbualan kosong sekarang!")

def update_session_preference(session_id, preference, value):
    if session_id in SESSION_DATA:
        SESSION_DATA[session_id][preference] = value

@get_session_id
@initialize_session_data
async def command_set(update: Update, context: CallbackContext, session_id):
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ Sila nyatakan setting nak ubah: model, temperature, system_prompt, max_tokens, openai_api_key.")
        return
    preference, *rest = args
    value = ' '.join(rest)
    if preference.lower() == 'openai_api_key':
        openai.api_key = value
        await update.message.reply_text("✅ OpenAI API Key berjaya diset.")

def register_handlers(application):
    application.add_handlers(handlers={ 
        -1: [
            CommandHandler('start', command_start),
            CommandHandler('reset', command_reset),
            CommandHandler('clear', command_clear),
            CommandHandler('set', command_set),
        ],
        1: [MessageHandler(filters.ALL & (~filters.COMMAND), handle_message)]
    })

def railway_dns_workaround():
    from time import sleep
    sleep(1.3)
    for _ in range(3):
        if requests.get("https://api.telegram.org", timeout=3).status_code == 200:
            return
    print("Telegram API tak reachable lepas 3 kali cuba.")

def main():
    parser = argparse.ArgumentParser(description="Run the Telegram bot.")
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.disable(logging.WARNING)
    railway_dns_workaround()
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    register_handlers(application)
    try:
        application.run_polling()
    except Exception as e:
        logging.error(f"Error berlaku: {e}")

if __name__ == '__main__':
    main()
