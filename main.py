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

CONFIGURATION = load_configuration()
VISION_MODELS = CONFIGURATION.get('vision_models', [])
VALID_MODELS = CONFIGURATION.get('VALID_MODELS', {})

system_prompt = """
Anda ialah ejen sokongan rasmi untuk pemandu AirAsia Ride. Jawapan anda mesti:
- Ringkas, padat, dan mudah difahami
- Dalam Bahasa Melayu formal tetapi mesra
- Fokus kepada topik berkaitan pemandu, aplikasi, insentif, dan isu sokongan

Berikut adalah soalan lazim dan jawapannya:
1. Apa itu DOPQ?
DOPQ bermaksud Drop-off Priority Queue. Ia membolehkan pemandu dapat keutamaan giliran selepas turunkan penumpang di KLIA/KLIA2 jika mereka kekal dalam zon selama 30 minit.

2. Kenapa saya hilang DOPQ?
Jika anda keluar dari zon airport lebih 30 minit, sistem akan keluarkan anda dari DOPQ dan masuk ke giliran biasa (ACQ).

3. Kenapa saya tak dapat job walaupun ada dalam giliran?
Pastikan anda aktif dalam app (status Online), lokasi GPS tepat, dan tiada gangguan rangkaian.

4. Kenapa tak dapat insentif minggu ini?
Pastikan anda capai syarat trip, tiada incomplete job, cancel trip, atau laporan pelanggan.

5. Bila insentif dibayar?
Insentif dibayar setiap Rabu (atau selewatnya Khamis jika cuti umum).

6. Bagaimana nak tukar akaun bank?
Hantar maklumat akaun baru ke support melalui WhatsApp atau Telegram rasmi bersama bukti akaun.

7. Apps problem — tak dapat login atau loading slow
Sila tutup app, update ke versi terbaru, dan guna internet stabil. Kalau masih bermasalah, guna butang "Lapor Isu" dalam app.

8. Ada komisen ke?
Ya. Komisen standard 15% untuk setiap trip, tidak termasuk SST.

9. Nak cuti, kena buat apa?
Hanya perlu off-kan app. Tiada permohonan rasmi. Tapi lebih 14 hari tiada trip, sistem akan klasifikasikan tidak aktif.

10. Bagaimana nak aktifkan semula akaun?
Hubungi team sokongan melalui Telegram atau WhatsApp.

11. Masalah topup eWallet?
Semak transaksi dalam apps > Wallet. Jika tiada, hantar bukti transfer kepada support.
"""

@relay_errors
@get_session_id
@initialize_session_data
@check_api_key
async def handle_message(update: Update, context: CallbackContext, session_id):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    session_data = SESSION_DATA[session_id]
    user_message = update.message.text
    session_data['chat_history'].append({"role": "user", "content": user_message})

    messages_for_api = [
        {"role": "system", "content": session_data.get("system_prompt", system_prompt)}
    ] + session_data['chat_history']

    response = await response_from_openai(
        session_data['model'], messages_for_api,
        session_data['temperature'], session_data['max_tokens']
    )
    session_data['chat_history'].append({'role': 'assistant', 'content': response})
    await update.message.reply_markdown(response)

async def response_from_openai(model, messages, temperature, max_tokens):
    params = {'model': 'gpt-3.5-turbo', 'messages': messages, 'temperature': temperature}  # model paling murah
    if max_tokens is not None:
        params['max_tokens'] = max_tokens
    return openai.chat.completions.create(**params).choices[0].message.content

async def command_start(update: Update, context: CallbackContext):
    await update.message.reply_text("ℹ️ Selamat datang! Tanyakan saja apa-apa soalan berkaitan pemandu AirAsia Ride.")

def register_handlers(application):
    application.add_handlers(handlers={
        -1: [CommandHandler('start', command_start)],
        1: [MessageHandler(filters.ALL & (~filters.COMMAND), handle_message)]
    })

def railway_dns_workaround():
    from time import sleep
    sleep(1.3)
    for _ in range(3):
        try:
            if requests.get("https://api.telegram.org", timeout=3).status_code == 200:
                print("The api.telegram.org is reachable.")
                return
        except:
            pass
        print(f'Retrying...({_})')
    print("Failed to reach api.telegram.org after 3 attempts.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING)
    railway_dns_workaround()
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    register_handlers(application)
    application.run_polling()

if __name__ == '__main__':
    main()
