import argparse, os, logging
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackContext, filters

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN') or exit("🚨 TELEGRAM_TOKEN belum diset.")
SESSION_DATA = {}

FAQ = {
    "dopq": "DOPQ tu sistem giliran khas untuk pemandu AirAsia Ride yang baru turunkan penumpang di airport.",
    "insentif": "Insentif dibayar setiap hari Rabu. Kalau ada cuti, mungkin akan lewat ke Khamis.",
    "akaun bank": "Nak tukar akaun bank? Hantar butiran akaun ke Telegram rasmi support.",
    "login": "Kalau app tak boleh login, tutup & buka semula. Pastikan update dan internet stabil.",
    "cuti": "Awak boleh off app bila-bila masa. Tapi kalau lebih 14 hari tiada trip, sistem anggap tak aktif.",
    "komisen": "Komisen biasa ialah 15%, belum termasuk SST."
}

TRIGGER = ["aleeya", "admin"]
SALAM = ["salam", "assalamualaikum", "hi", "hello", "hai"]

def is_triggered(text):
    return any(x in text for x in TRIGGER)

def is_salam(text):
    return any(x in text for x in SALAM)

def detect_faq(text):
    for keyword, response in FAQ.items():
        if keyword in text:
            return response
    return None

def is_random(text):
    return len(text.strip()) < 6 or sum(c.isalpha() for c in text) < 4

async def handle(update: Update, context: CallbackContext):
    text = update.message.text.lower()

    if update.effective_chat.type in ['group', 'supergroup']:
        if not (is_triggered(text) or is_salam(text)):
            return

    if is_salam(text):
        await update.message.reply_text("Waalaikumsalam 😊 Ada apa-apa saya boleh bantu?")
        return

    if is_random(text):
        return  # Senyap jika random / typo / tak jelas

    faq_response = detect_faq(text)
    if faq_response:
        await update.message.reply_text(faq_response)
        return

    if is_triggered(text):
        await update.message.reply_text("Ya awak panggil saya? 😊 Tulis je apa awak nak tahu.")
        return

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Hai! Saya Aleeya. Awak boleh tanya soalan bila-bila ya 😊")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    if args.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.disable(logging.WARNING)

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle))
    app.run_polling()

if __name__ == '__main__':
    main()
