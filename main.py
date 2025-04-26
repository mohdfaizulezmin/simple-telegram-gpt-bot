import argparse, json, logging, os, openai, re, requests
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
Anda ialah AI sokongan untuk pemandu AirAsia Ride. Jawab dengan ringkas dan mesra. Guna gaya bahasa "saya" dan "awak". Berikut ialah soalan lazim:

1. Apa itu DOPQ?
Drop-off Priority Queue (DOPQ) ialah giliran keutamaan untuk pemandu selepas turunkan penumpang di airport. Jika pemandu kekal dalam zon, mereka dapat DOPQ.

2. Bila insentif dibayar?
Setiap Rabu, atau selewatnya Khamis jika ada cuti umum.

3. Kenapa tak dapat insentif minggu ini?
Sebab biasa: tidak cukup trip, ada cancel job, atau laporan pelanggan.

4. Bagaimana nak tukar akaun bank?
Hantar maklumat akaun baru ke team support melalui Telegram/WhatsApp.

5. Masalah app atau tak boleh login?
Pastikan app dikemas kini, guna internet stabil, atau guna fungsi "Lapor Isu" dalam app.

6. Nak cuti macam mana?
Hanya off app. Tapi kalau 14 hari tiada trip, akan dikira tidak aktif.

7. Akaun kena block, macam mana?
Hubungi support melalui Telegram/WhatsApp rasmi.

8. Dapat job tapi tiada penumpang?
Hubungi support. Jangan teruskan perjalanan.

9. Ada komisen ke?
Ya. Standard 15% dari tambang.

10. Topup eWallet lambat masuk?
Semak transaksi wallet. Jika tiada, hantar bukti transfer kepada support.
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
    return any(greet in text.lower() for greet in ['salam', 'assalamualaikum', 'as salam'])

def is_bot_called(text):
    return 'aleeya' in text.lower() or 'admin' in text.lower()

def is_valid_message(text):
    return len(text.split()) > 2 or is_salutation(text) or is_bot_called(text)

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
    session_data = SESSION_DATA[session_id]
    session_data['chat_history'].append({"role": "user", "content": f"{faq_aar}\n\nSoalan: {update.message.text}"})
    response = await response_from_openai(session_data['model'], session_data['chat_history'], session_data['temperature'], session_data['max_tokens'])
    session_data['chat_history'].append({'role': 'assistant', 'content': response})
    await update.message.reply_text(response.strip(), parse_mode=ParseMode.MARKDOWN)

async def response_from_openai(model, messages, temperature, max_tokens):
    params = {
        'model': model,
        'messages': messages,
        'temperature': temperature,
        'max_tokens': max_tokens or 512
    }
    return openai.chat.completions.create(**params).choices[0].message.content

async def command_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Hai! 😊 Saya Aleeya. Boleh bantu jawab soalan berkaitan AirAsia Ride.")

@get_session_id
async def command_reset(update: Update, context: CallbackContext, session_id):
    SESSION_DATA.pop(session_id, None)
    await update.message.reply_text("✅ Semua tetapan dan sejarah chat dah dipadam.")

@get_session_id
async def command_clear(update: Update, context: CallbackContext, session_id):
    SESSION_DATA[session_id]['chat_history'] = []
    await update.message.reply_text("✅ Sejarah chat dah kosong!")

@initialize_session_data
@get_session_id
async def command_set(update: Update, context: CallbackContext, session_id):
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Guna format: /set [setting] [value]")
        return
    key, value = args[0].lower(), ' '.join(args[1:])
    if key == 'openai_api_key':
        openai.api_key = value
        await update.message.reply_text("✅ API key dikemas kini.")
    elif key in ['model', 'temperature', 'max_tokens', 'system_prompt']:
        SESSION_DATA[session_id][key] = float(value) if key == 'temperature' else int(value) if key == 'max_tokens' else value
        await update.message.reply_text(f"✅ {key} disimpan.")
    else:
        await update.message.reply_text("Setting tak dikenali.")

@get_session_id
async def command_show(update: Update, context: CallbackContext, session_id):
    data = SESSION_DATA.get(session_id, {})
    msg = '\n'.join([f"{k}: {v}" for k, v in data.items() if k != 'chat_history'])
    await update.message.reply_text(f"📌 Tetapan semasa:\n{msg}")

async def command_help(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "🛠 Perintah yang ada:\n"
        "/start - Mula perbualan\n"
        "/reset - Padam semua tetapan\n"
        "/clear - Kosongkan chat\n"
        "/set - Ubah setting (contoh: model)\n"
        "/show - Lihat setting semasa\n"
        "/help - Senarai perintah"
    )

def register_handlers(app):
    app.add_handlers(handlers={
        -1: [
            CommandHandler('start', command_start),
            CommandHandler('reset', command_reset),
            CommandHandler('clear', command_clear),
            CommandHandler('set', command_set),
            CommandHandler('show', command_show),
            CommandHandler('help', command_help)
        ],
        1: [MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)]
    })

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
