# Import semua library yang diperlukan
import argparse, json, logging, os, openai, requests, asyncio, random
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackContext, filters

# Ambil token dan API Key dari environment
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN') or exit("🚨 TELEGRAM_TOKEN tidak diset.")
openai.api_key = os.getenv('OPENAI_API_KEY') or None

SESSION_DATA = {}

# Load setting dari fail configuration.json
def load_configuration():
    with open('configuration.json', 'r') as file:
        return json.load(file)

# Dapatkan session ID untuk setiap user/group
def get_session_id(func):
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        session_id = str(update.effective_chat.id if update.effective_chat.type in ['group', 'supergroup'] else update.effective_user.id)
        return await func(update, context, session_id, *args, **kwargs)
    return wrapper

# Inisialisasi data session user
def initialize_session_data(func):
    async def wrapper(update: Update, context: CallbackContext, session_id, *args, **kwargs):
        if session_id not in SESSION_DATA:
            SESSION_DATA[session_id] = load_configuration()['default_session_values']
        return await func(update, context, session_id, *args, **kwargs)
    return wrapper

# Cek kalau tiada OpenAI API key
def check_api_key(func):
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        if not openai.api_key:
            await update.message.reply_text("⚠️ Sila set OpenAI API Key dahulu dengan /set openai_api_key YOUR_KEY.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# Relay error supaya bot tidak crash kalau ada error
def relay_errors(func):
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        try:
            return await func(update, context, *args, **kwargs)
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error berlaku: {e}")
    return wrapper

# Load semua konfigurasi
CONFIGURATION = load_configuration()
VISION_MODELS = CONFIGURATION.get('vision_models', [])
VALID_MODELS = CONFIGURATION.get('VALID_MODELS', {})

# Tetapkan identiti Aleeya
ALEEYA_PROMPT = """
Nama saya Aleeya. Saya bot sokongan AirAsia Ride.
Saya hanya berkomunikasi dalam Bahasa Melayu.
Gaya saya santai, guna "saya" dan "awak", dan balas pendek sahaja.
Saya hanya jawab kalau nama saya "Aleeya" atau "admin" disebut atau diberi salam.
"""

# Delay 33–60 saat untuk reply
async def natural_delay():
    await asyncio.sleep(random.randint(33, 60))

# Fungsi untuk proses mesej user
@relay_errors
@get_session_id
@initialize_session_data
@check_api_key
async def handle_message(update: Update, context: CallbackContext, session_id):
    text = (update.message.text or "").lower()

    # Kalau dalam group, cek nama dipanggil
    if update.message.chat.type in ['group', 'supergroup']:
        if not any(trigger in text for trigger in ["aleeya", "admin", "assalamualaikum", "salam", "hi", "hai"]):
            return  # Diam kalau tak panggil

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    await natural_delay()

    user_message = update.message.text

    # Auto detect FAQ AirAsia Ride
    faq_response = detect_faq(user_message)
    if faq_response:
        await update.message.reply_text(faq_response)
        return

    session_data = SESSION_DATA[session_id]
    session_data['chat_history'].append({
        "role": "user",
        "content": user_message
    })

    response = await response_from_openai(
        session_data['model'],
        session_data['chat_history'],
        session_data['temperature'],
        session_data['max_tokens']
    )

    # Padam simbol —
    response = response.replace("—", "")

    # Format ayat biar jadi ayat pendek
    if len(response) > 500:
        response = potong_perenggan(response)

    session_data['chat_history'].append({
        'role': 'assistant',
        'content': response
    })

    await update.message.reply_text(response)

# Fungsi potong panjang jawapan jadi pendek
def potong_perenggan(teks):
    potong = teks.split(". ")
    return ". ".join(potong[:2]) + "."

# Fungsi auto detect FAQ AirAsia Ride
def detect_faq(text):
    text = text.lower()
    if "dopq" in text:
        return "DOPQ maksudnya Drop-off Priority Queue. Ia beri keutamaan kepada pemandu di KLIA/KLIA2 jika kekal dalam zon selepas drop off."
    if "insentif" in text:
        return "Insentif AirAsia Ride dibayar setiap Rabu (atau Khamis jika ada cuti umum). Pastikan syarat trip dipenuhi ya."
    if "akaun bank" in text or "tukar bank" in text:
        return "Kalau nak tukar akaun bank, hantar info ke support WhatsApp/Telegram rasmi."
    if "cuti" in text:
        return "Untuk cuti, off-kan apps sahaja. Jika lebih 14 hari tiada trip, akan dikira tidak aktif."
    return None

# Fungsi panggil API OpenAI
async def response_from_openai(model, messages, temperature, max_tokens):
    params = {'model': model, 'messages': [{"role": "system", "content": ALEEYA_PROMPT}] + messages, 'temperature': temperature}
    if model == "gpt-4-vision-preview":
        max_tokens = 4096
    if max_tokens is not None:
        params['max_tokens'] = max_tokens
    return openai.chat.completions.create(**params).choices[0].message.content

# Fungsi /start untuk mula bot
async def command_start(update: Update, context: CallbackContext):
    await update.message.reply_text("Hai! 🌸 Saya Aleeya. Sedia membantu awak.")

# Fungsi reset session user
@get_session_id
async def command_reset(update: Update, context: CallbackContext, session_id):
    if session_id in SESSION_DATA:
        del SESSION_DATA[session_id]
    await update.message.reply_text("Reset berjaya. Awak boleh mula borak baru!")

# Fungsi clear chat history
@get_session_id
async def command_clear(update: Update, context: CallbackContext, session_id):
    if session_id in SESSION_DATA:
        SESSION_DATA[session_id]['chat_history'] = []
    await update.message.reply_text("Sejarah chat sudah dikosongkan!")

# Fungsi /help tunjuk arahan
async def command_help(update: Update, context: CallbackContext):
    help_text = (
        "<b>📚 Arahan yang boleh digunakan:</b>\n"
        "<code>/start</code> - Mulakan semula Aleeya\n"
        "<code>/reset</code> - Reset semua setting\n"
        "<code>/clear</code> - Kosongkan chat\n"
        "<code>/help</code> - Lihat arahan\n"
    )
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)

# Daftarkan semua command handler
def register_handlers(application):
    application.add_handlers(handlers={
        -1: [
            CommandHandler('start', command_start),
            CommandHandler('reset', command_reset),
            CommandHandler('clear', command_clear),
            CommandHandler('help', command_help)
        ],
        1: [MessageHandler(filters.ALL & (~filters.COMMAND), handle_message)]
    })

# Untuk pastikan telegram.org boleh dicapai
def railway_dns_workaround():
    from time import sleep
    sleep(1.3)
    for _ in range(3):
        if requests.get("https://api.telegram.org", timeout=3).status_code == 200:
            print("Telegram API reachable.")
            return
        print(f"Retry to reach Telegram API... ({_+1})")

# Main fungsi run bot
def main():
    parser = argparse.ArgumentParser(description="Run Aleeya Telegram Bot")
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    args = parser.parse_args()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.disable(logging.WARNING)

    railway_dns_workaround()
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    register_handlers(application)

    try:
        print("Bot Aleeya sedang berjalan...")
        application.run_polling()
    except Exception as e:
        logging.error(f"Bot error: {e}")

if __name__ == '__main__':
    main()
