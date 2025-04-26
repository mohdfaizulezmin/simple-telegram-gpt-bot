import argparse, json, logging, os, openai, requests, asyncio, random
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackContext, filters

# Token dan API Key
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN') or exit("🚨Error: TELEGRAM_TOKEN is not set.")
openai.api_key = os.getenv('OPENAI_API_KEY') or None
SESSION_DATA = {}

# Fungsi load config
def load_configuration():
    with open('configuration.json', 'r') as file:
        return json.load(file)

# Untuk dapat session ID ikut user/group
def get_session_id(func):
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        session_id = str(update.effective_chat.id if update.effective_chat.type in ['group', 'supergroup'] else update.effective_user.id)
        return await func(update, context, session_id, *args, **kwargs)
    return wrapper

# Untuk pastikan ada data sesi
def initialize_session_data(func):
    async def wrapper(update: Update, context: CallbackContext, session_id, *args, **kwargs):
        if session_id not in SESSION_DATA:
            SESSION_DATA[session_id] = load_configuration()['default_session_values']
        return await func(update, context, session_id, *args, **kwargs)
    return wrapper

# Untuk check api key openai
def check_api_key(func):
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        if not openai.api_key:
            await update.message.reply_text("⚠️ Sila tetapkan OpenAI API Key: /set openai_api_key YOUR_API_KEY")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# Untuk relay error ke user
def relay_errors(func):
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            await update.message.reply_text(f"⚠️ Maaf, berlaku ralat: {e}")
    return wrapper

CONFIGURATION = load_configuration()
VISION_MODELS = CONFIGURATION.get('vision_models', [])
VALID_MODELS = CONFIGURATION.get('VALID_MODELS', {})

# System prompt khas untuk Aleeya
ALEEYA_PROMPT = {
    "role": "system",
    "content": "Anda ialah Aleeya, AI sokongan untuk AirAsia Ride. Jawab dalam Bahasa Melayu sahaja. Gaya santai manusia, gunakan 'saya' dan 'awak', jangan gunakan simbol —. Jawab dalam ayat pendek, perenggan santai."
}

# Fungsi handle message
@relay_errors
@get_session_id
@initialize_session_data
@check_api_key
async def handle_message(update: Update, context: CallbackContext, session_id):
    user_message = update.message.text.lower()

    # Hanya balas jika sebut nama atau beri salam
    trigger = any(keyword in user_message for keyword in ["aleeya", "admin", "assalamualaikum", "salam", "hai", "hello"])
    if not trigger:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    session_data = SESSION_DATA[session_id]
    user_input = update.message.text.replace("—", "-")  # remove em dash

    # Simpan history
    session_data['chat_history'].append({
        "role": "user",
        "content": user_input
    })

    # Sediakan mesej untuk OpenAI
    messages_for_api = [ALEEYA_PROMPT] + [
        {"role": chat["role"], "content": chat["content"]}
        for chat in session_data['chat_history']
    ]

    # Delay untuk nampak natural
    await asyncio.sleep(random.randint(33, 60))

    response = await response_from_openai(
        session_data['model'], 
        messages_for_api, 
        session_data['temperature'], 
        session_data['max_tokens']
    )

    # Simpan jawapan
    session_data['chat_history'].append({
        'role': 'assistant',
        'content': response
    })

    await update.message.reply_text(response)

# Panggil OpenAI API
async def response_from_openai(model, messages, temperature, max_tokens):
    params = {'model': model, 'messages': messages, 'temperature': temperature}
    if model == "gpt-4-vision-preview":
        max_tokens = 4096
    if max_tokens is not None:
        params['max_tokens'] = max_tokens
    reply = openai.chat.completions.create(**params).choices[0].message.content
    return reply.replace("—", "-")  # tukar em dash kalau ada

# Command /start
async def command_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Hai! Saya Aleeya. Sedia bantu awak. 🌸")

# Command /help
async def command_help(update: Update, context: CallbackContext):
    await update.message.reply_text("Guna 'Aleeya' atau 'Admin' untuk mula berbual dengan saya ya. ✨")

# Untuk register command
def register_handlers(application):
    application.add_handler(CommandHandler('start', command_start))
    application.add_handler(CommandHandler('help', command_help))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

# Railway DNS workaround
def railway_dns_workaround():
    from time import sleep
    sleep(1.3)
    for _ in range(3):
        try:
            if requests.get("https://api.telegram.org", timeout=3).status_code == 200:
                return
        except:
            sleep(1)

# Main function
def main():
    parser = argparse.ArgumentParser(description="Run Aleeya Bot.")
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
        logging.error(f"An error occurred: {e}")

if __name__ == '__main__':
    main()
