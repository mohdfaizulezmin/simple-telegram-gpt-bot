import argparse, json, logging, os, openai, requests
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackContext, filters

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN') or exit("🚨Error: TELEGRAM_TOKEN is not set.")
openai.api_key = os.getenv('OPENAI_API_KEY') or None
SESSION_DATA = {}

def load_configuration():
    with open('configuration.json', 'r') as file:
        return json.load(file)

def get_session_id(func):
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        session_id = str(update.effective_chat.id if update.effective_chat.type in ['group', 'supergroup'] else update.effective_user.id)
        return await func(update, context, session_id, *args, **kwargs)
    return wrapper

def initialize_session_data(func):
    async def wrapper(update: Update, context: CallbackContext, session_id, *args, **kwargs):
        if session_id not in SESSION_DATA:
            logging.debug(f"Initializing session data for session_id={session_id}")
            SESSION_DATA[session_id] = load_configuration()['default_session_values']
        return await func(update, context, session_id, *args, **kwargs)
    return wrapper

def check_api_key(func):
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        if not openai.api_key:
            await update.message.reply_text("⚠️ Sila set API key: /set openai_api_key YOUR_KEY")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def relay_errors(func):
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            await update.message.reply_text(f"Maaf ya, ada ralat teknikal. ({e})")
    return wrapper

def get_system_prompt():
    return (
        "Awak ialah Aleeya, pembantu AI kepada pemandu AirAsia Ride."
        " Awak akan jawab dalam Bahasa Melayu, sopan dan santai."
        " Gaya awak mesra, pendek, dalam perenggan."
        " Awak hanya jawab kalau nama awak dipanggil, contohnya 'aleeya' atau 'admin'."
        " Kalau tak dipanggil, diam sahaja."
        " Fokus kepada topik e-hailing, pemandu, aplikasi, DOPQ, insentif, dan isu biasa."
    )

CONFIGURATION = load_configuration()
VISION_MODELS = CONFIGURATION.get('vision_models', [])
VALID_MODELS = CONFIGURATION.get('VALID_MODELS', {})

@relay_errors
@get_session_id
@initialize_session_data
@check_api_key
async def handle_message(update: Update, context: CallbackContext, session_id):
    message_text = update.message.text.lower()
    if update.effective_chat.type in ['group', 'supergroup']:
        if not any(name in message_text for name in ["aleeya", "admin"]):
            return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    session_data = SESSION_DATA[session_id]
    user_message = update.message.text

    session_data['chat_history'].append({
        "role": "system", "content": get_system_prompt()
    })
    session_data['chat_history'].append({
        "role": "user", "content": user_message
    })

    messages_for_api = session_data['chat_history'][-10:]

    response = await response_from_openai(
        session_data['model'], 
        messages_for_api, 
        session_data['temperature'], 
        session_data['max_tokens']
    )

    session_data['chat_history'].append({
        'role': 'assistant',
        'content': response
    })
    await update.message.reply_text(response)

async def response_from_openai(model, messages, temperature, max_tokens):
    params = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens or 300,
    }
    return openai.chat.completions.create(**params).choices[0].message.content.strip()

async def command_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Hi! Saya Aleeya, pembantu AI untuk pemandu AirAsia Ride. Tulis 'aleeya' atau 'admin' kalau perlukan bantuan ya 😊")

@get_session_id
async def command_reset(update: Update, context: CallbackContext, session_id):
    if session_id in SESSION_DATA:
        del SESSION_DATA[session_id]
    await update.message.reply_text("✅ Semua data sesi dah dipadam. Awak boleh mula semula sekarang.")

@get_session_id
async def command_clear(update: Update, context: CallbackContext, session_id):
    if session_id in SESSION_DATA:
        SESSION_DATA[session_id]['chat_history'] = []
    await update.message.reply_text("✅ Chat history dah kosong.")

@get_session_id
@initialize_session_data
async def command_set(update: Update, context: CallbackContext, session_id):
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ Sila nyatakan apa yang nak diubah.")
        return
    preference, *rest = args
    value = ' '.join(rest)
    SESSION_DATA[session_id][preference] = value
    await update.message.reply_text(f"✅ {preference} telah ditetapkan ke: {value}")

@get_session_id
async def command_show(update: Update, context: CallbackContext, session_id):
    session_data = SESSION_DATA.get(session_id, {})
    if not session_data:
        await update.message.reply_text("Tiada data sesi buat masa ini.")
        return
    reply = "\n".join([f"{k}: {v}" for k, v in session_data.items() if k != 'chat_history'])
    await update.message.reply_text(f"**Maklumat sesi:**\n{reply}")

def register_handlers(application):
    application.add_handlers(handlers={
        -1: [
            CommandHandler('start', command_start),
            CommandHandler('reset', command_reset),
            CommandHandler('clear', command_clear),
            CommandHandler('set', command_set),
            CommandHandler('show', command_show),
        ],
        1: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)]
    })

def railway_dns_workaround():
    from time import sleep
    sleep(1.3)
    for _ in range(3):
        try:
            if requests.get("https://api.telegram.org", timeout=3).status_code == 200:
                return
        except:
            pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.disable(logging.WARNING)

    railway_dns_workaround()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    register_handlers(app)
    app.run_polling()

if __name__ == '__main__':
    main()
