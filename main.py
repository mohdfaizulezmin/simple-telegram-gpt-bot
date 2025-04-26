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
            SESSION_DATA[session_id]['chat_history'] = [
                {"role": "system", "content": system_prompt}
            ]
        else:
            logging.debug(f"Session data already exists for session_id={session_id}")
        logging.debug(f"SESSION_DATA[{session_id}]: {SESSION_DATA[session_id]}")
        return await func(update, context, session_id, *args, **kwargs)
    return wrapper

def check_api_key(func):
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        if not openai.api_key:
            await update.message.reply_text("⚠️Please configure your OpenAI API Key: /set openai_api_key THE_API_KEY")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def relay_errors(func):
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            await update.message.reply_text(f"An error occurred. e: {e}")
    return wrapper

system_prompt = """
Anda ialah ejen sokongan rasmi untuk pemandu AirAsia Ride. Jawapan anda mesti:
- Ringkas, padat, dan mudah difahami
- Dalam Bahasa Melayu formal tetapi mesra
- Fokus kepada topik berkaitan pemandu, aplikasi, insentif, dan isu sokongan

Berikut adalah soalan lazim dan jawapannya:
1. Apa itu DOPQ? DOPQ ialah Drop-off Priority Queue. Ia beri keutamaan kepada pemandu yang kekal di zon KLIA selepas turunkan penumpang.
2. Kenapa saya hilang DOPQ? Anda keluar dari zon lebih 30 minit.
3. Bila insentif dibayar? Setiap Rabu (atau Khamis jika cuti umum).
4. Masalah login atau app? Tutup & buka semula app, pastikan internet stabil.
5. Nak cuti? Off-kan app sahaja. Akaun aktif semula bila terima trip.
6. Tukar akaun bank? Hubungi support & sertakan bukti akaun.
"""

CONFIGURATION = load_configuration()
VISION_MODELS = CONFIGURATION.get('vision_models', [])
VALID_MODELS = CONFIGURATION.get('VALID_MODELS', {})

@relay_errors
@get_session_id
@initialize_session_data
@check_api_key
async def handle_message(update: Update, context: CallbackContext, session_id):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    session_data = SESSION_DATA[session_id]
    user_message = update.message.text
    session_data['chat_history'].append({"role": "user", "content": user_message})
    response = await response_from_openai(session_data['model'], session_data['chat_history'], session_data['temperature'], session_data['max_tokens'])
    session_data['chat_history'].append({"role": "assistant", "content": response})
    await update.message.reply_markdown(response)

async def response_from_openai(model, messages, temperature, max_tokens):
    params = {'model': model, 'messages': messages, 'temperature': temperature}
    if model == "gpt-4-vision-preview":
        max_tokens = 4096
    if max_tokens is not None:
        params['max_tokens'] = max_tokens
    return openai.chat.completions.create(**params).choices[0].message.content

async def command_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Selamat datang ke sokongan pemandu AirAsia Ride. Saya sedia bantu!")

@get_session_id
async def command_reset(update: Update, context: CallbackContext, session_id):
    if session_id in SESSION_DATA:
        del SESSION_DATA[session_id]
        await update.message.reply_text("ℹ️ Reset berjaya.")
    else:
        await update.message.reply_text("Tiada data untuk direset.")

def register_handlers(app):
    app.add_handlers(handlers={
        -1: [
            CommandHandler('start', command_start),
            CommandHandler('reset', command_reset),
        ],
        1: [MessageHandler(filters.ALL & (~filters.COMMAND), handle_message)]
    })

def railway_dns_workaround():
    from time import sleep
    sleep(1.3)
    for _ in range(3):
        try:
            if requests.get("https://api.telegram.org", timeout=3).status_code == 200:
                print("Telegram API reachable.")
                return
        except: pass
        print("Retrying...")

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
    try:
        print("Bot is running...")
        app.run_polling()
    except Exception as e:
        logging.error(f"Runtime error: {e}")

if __name__ == '__main__':
    main()
