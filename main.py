import os, openai, logging
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, ContextTypes, filters
from telegram.constants import ChatAction

# Tetapan asas
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or exit("TELEGRAM_TOKEN not set.")
openai.api_key = os.getenv("OPENAI_API_KEY") or exit("OPENAI_API_KEY not set.")

def get_prompt(user_input):
    return [
        {"role": "system", "content": (
            "Anda ialah ejen sokongan rasmi untuk pemandu AirAsia Ride. Jawapan anda mesti dalam Bahasa Melayu, padat, mesra, dan fokus kepada topik berkaitan pemandu e-hailing seperti DOPQ, insentif, aplikasi, sokongan teknikal, pembayaran, dan akaun pemandu."
            "Jawab soalan berdasarkan maklumat berikut:
            1. DOPQ ialah keutamaan giliran selepas drop-off di KLIA, aktif 30 minit.
            2. Jika keluar zon lebih 30 minit, DOPQ hilang dan masuk ACQ.
            3. Insentif dibayar hari Rabu (atau Khamis jika cuti).
            4. Tak dapat job? Pastikan Online, lokasi tepat, tiada gangguan app.
            5. Tukar akaun bank: hantar info ke support (Telegram/WhatsApp).
            6. Komisen 15% tak termasuk SST.
            7. Nak cuti? Off app. >14 hari tiada trip = tidak aktif.
            8. Akaun tidak aktif boleh diaktifkan semula oleh support.
            9. Masalah app: update app, tutup & buka, tekan "Lapor Isu" dalam app.
            10. eWallet: Semak Wallet, jika tak masuk, hantar bukti ke support.")},
        {"role": "user", "content": user_input}
    ]

# Fungsi utama untuk reply mesej
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    user_input = update.message.text

    try:
        messages = get_prompt(user_input)
        completion = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages
        )
        reply = completion.choices[0].message.content
        await update.message.reply_text(reply)
    except Exception as e:
        await update.message.reply_text("Maaf, berlaku masalah teknikal. Sila cuba lagi sebentar nanti.")
        logging.error(f"OpenAI error: {e}")

# Command asas
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hi! Saya ejen sokongan AirAsia Ride. Tanyakan apa-apa isu anda.")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()
