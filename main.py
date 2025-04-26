import argparse, json, logging, os, openai, random, re, asyncio
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackContext, filters

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN') or exit("🚨Error: TELEGRAM_TOKEN is not set.")
openai.api_key = os.getenv('OPENAI_API_KEY') or None
SESSION_DATA = {}

def load_configuration():
    with open('configuration.json', 'r') as file:
        return json.load(file)

CONFIGURATION = load_configuration()
VISION_MODELS = CONFIGURATION.get('vision_models', [])
VALID_MODELS = CONFIGURATION.get('VALID_MODELS', {})

faq_aar = """
Anda ialah AI sokongan untuk pemandu AirAsia Ride. Jawab dengan ringkas, sopan dan gunakan "saya" dan "awak". Elakkan jawapan panjang. Berikut FAQ utama:

1. Apa itu DOPQ?
DOPQ bermaksud giliran keutamaan untuk pemandu selepas hantar penumpang di airport. Pastikan kekal dalam zon 30 minit.

2. Bila insentif dibayar?
Setiap Rabu, atau Khamis jika ada cuti umum.

3. Kenapa tak dapat insentif?
Mungkin tak cukup trip, cancel trip, incomplete job, atau laporan pelanggan.

4. Tukar akaun bank?
Hantar maklumat baru ke team support Telegram atau WhatsApp rasmi.

5. App problem?
Pastikan app dikemas kini, tutup buka semula, dan guna internet stabil.

6. Cuti macam mana?
Hanya off app, tak perlu permohonan. Tapi kalau lebih 14 hari tiada trip, dianggap tidak aktif.

7. Akaun suspended?
Hubungi support segera untuk semak status.

8. Job dapat tapi penumpang tak ada?
Jangan teruskan perjalanan. Lapor kepada support.

9. Komisen berapa?
15% komisen standard dari tambang.

10. Topup eWallet lambat?
Semak dalam wallet app. Jika tiada, hantar bukti kepada support.
"""

def get_session_id(func):
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        session_id = str(update.effective_chat.id if update.effective_chat.type in ['group', 'supergroup'] else update.effective_user.id)
        return await func(update, context, session_id, *args, **kwargs)
    return wrapper

def initialize_session_data(func):
    async def wrapper(update: Update, context: CallbackContext, session_id, *args, **kwargs):
        if session_id not in SESSION_DATA:
            SESSION_DATA[session_id] = CONFIGURATION['default_session_values']
        return await func(update, context, session_id, *args, **kwargs)
    return wrapper

def check_api_key(func):
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        if not openai.api_key:
            await update.message.reply_text("⚠️ Sila set API key dulu: /set openai_api_key YOUR_KEY")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def relay_errors(func):
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            await update.message.reply_text(f"Ada error: {e}")
    return wrapper

def is_salutation(text):
    return any(word in text.lower() for word in ['salam', 'assalamualaikum', 'hi', 'hai', 'hello'])

def is_bot_called(text):
    return 'aleeya' in text.lower() or 'admin' in text.lower()

def is_valid_message(text):
    return len(text.split()) > 2 or is_salutation(text) or is_bot_called(text)

def clean_response(text):
    return re.sub(r'[–—]', '', text).strip()

@relay_errors
@get_session_id
@initialize_session_data
@check_api_key
async def handle_message(update: Update, context: CallbackContext, session_id):
    if not update.message or not update.message.text:
        return

    text = update.message.text.lower()
    if update.effective_chat.type in ['group', 'supergroup']:
        if not is_salutation(text) and not is_bot_called(text):
            return

    if not is_valid_message(text):
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await asyncio.sleep(random.uniform(33, 60))  # ⏳ Delay typing 33-60s sebelum balas

    session_data = SESSION_DATA[session_id]
    session_data['chat_history'].append({"role": "user", "content": f"{faq_aar}\n\nSoalan: {update.message.text}"})

    response = await response_from_openai(
        session_data['model'],
        session_data['chat_history'],
        session_data['temperature'],
        session_data['max_tokens']
    )

    session_data['chat_history'].append({'role': 'assistant', 'content': response})
    final_response = clean_response(response)

    await update.message.reply_text(final_response, parse_mode=ParseMode.MARKDOWN)

async def response_from_openai(model, messages, temperature, max_tokens):
    params = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens or 512
    }
    return openai.chat.completions.create(**params).choices[0].message.content

async def command_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Hai! Saya Aleeya. Awak boleh tanya saya soalan berkaitan AirAsia Ride. 😊")

def register_handlers(app):
    app.add_handler(CommandHandler('start', command_start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING)
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    register_handlers(app)
    app.run_polling()

if __name__ == '__main__':
    main()
