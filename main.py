import argparse, json, logging, os, openai, requests
from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackContext, filters

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN') or exit("🚨Error: TELEGRAM_TOKEN is not set.")
openai.api_key = os.getenv('OPENAI_API_KEY') or None
SESSION_DATA = {}

# ========== BASIC CONFIG ==========
FAQ_KEYWORDS = {
    "dopq": "DOPQ tu sistem giliran untuk pemandu AirAsia Ride di KLIA. Kalau awak turunkan penumpang dan kekal dalam zon, awak dapat keutamaan job.",
    "insentif": "Insentif dibayar setiap Rabu, tapi pastikan awak cukup syarat trip dan tiada cancel atau incomplete job.",
    "akaun bank": "Untuk tukar akaun bank, boleh hantar info dan bukti akaun ke support dalam WhatsApp atau Telegram.",
    "tak dapat job": "Pastikan status app awak online, GPS on, dan line internet stabil. Cuba tunggu dalam zon aktif."
}

SALAM_KEYWORDS = ["salam", "assalamualaikum", "hi", "helo", "hello"]
NAME_KEYWORDS = ["aleeya", "admin"]

# ========== SESSION HELPERS ==========
def load_configuration():
    return {
        "default_session_values": {
            "model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 500,
            "system_prompt": ""
        }
    }

def get_session_id(func):
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        session_id = str(update.effective_chat.id if update.effective_chat.type in ['group', 'supergroup'] else update.effective_user.id)
        return await func(update, context, session_id, *args, **kwargs)
    return wrapper

def initialize_session_data(func):
    async def wrapper(update: Update, context: CallbackContext, session_id, *args, **kwargs):
        if session_id not in SESSION_DATA:
            SESSION_DATA[session_id] = load_configuration()['default_session_values']
            SESSION_DATA[session_id]['chat_history'] = []
        return await func(update, context, session_id, *args, **kwargs)
    return wrapper

# ========== BOT HANDLER ==========
@initialize_session_data
@get_session_id
async def handle_message(update: Update, context: CallbackContext, session_id):
    message_text = update.message.text.lower()

    # 🧠 Bot akan diam jika bukan panggilan nama atau bukan salam
    mentioned = any(name in message_text for name in NAME_KEYWORDS)
    is_salam = any(s in message_text for s in SALAM_KEYWORDS)

    if not mentioned and not is_salam:
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    # Salam reply
    if is_salam and not mentioned:
        await update.message.reply_text("Waalaikumsalam. Saya ada di sini kalau awak nak tanya apa-apa ya 😊")
        return

    # Jawapan FAQ auto detect
    for keyword in FAQ_KEYWORDS:
        if keyword in message_text:
            await update.message.reply_text(FAQ_KEYWORDS[keyword])
            return

    # Jika tak match FAQ, hantar ke OpenAI (dengan gaya ringkas)
    user_message = update.message.text
    chat_history = SESSION_DATA[session_id]['chat_history']
    chat_history.append({"role": "user", "content": user_message})

    response = await response_from_openai(
        SESSION_DATA[session_id]['model'],
        messages=[{"role": "system", "content": "Jawab pendek, sopan dan dalam Bahasa Melayu. Guna nada perbualan santai seperti 'saya' dan 'awak'."}] + chat_history[-5:],
        temperature=SESSION_DATA[session_id]['temperature'],
        max_tokens=SESSION_DATA[session_id]['max_tokens']
    )

    chat_history.append({"role": "assistant", "content": response})
    await update.message.reply_text(response)

async def response_from_openai(model, messages, temperature, max_tokens):
    try:
        result = openai.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return result.choices[0].message.content.strip()
    except Exception as e:
        return f"Maaf, ada masalah teknikal sebentar: {e}"

# ========== RAILWAY & MAIN ==========
def register_handlers(app):
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))

def railway_dns_workaround():
    from time import sleep
    for _ in range(3):
        try:
            if requests.get("https://api.telegram.org", timeout=3).status_code == 200:
                return
        except:
            sleep(1)

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
    print("Bot is running in long polling mode...")
    app.run_polling()

if __name__ == '__main__':
    main()
